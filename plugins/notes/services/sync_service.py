"""
坚果云 WebDAV 同步服务 v3（纯 GET/PUT + devices.json 注册表 + 扁平文件布局，
协议与 Android 端 CloudSyncService.kt 完全一致）

v3 起因：坚果云 WAF 按 TLS 指纹拦截 Android HttpURLConnection 的非标准 HTTP 方法
（PROPFIND/MKCOL 一律 403 OperationNotAllowed，GET/PUT 放行——2026-08-24 实机
全链路验证），因此设备发现改用注册表、目录结构改扁平，彻底消灭 PROPFIND/MKCOL。

远端布局（全部平铺在 `/<remote_dir>/` 根目录，不建子目录）：
 - `devices.json`：设备注册表 {"devices":["ANDROID-x","PC-y"],"updated_at":...}
 - `<device_id>.manifest.json` + `<device_id>.backup.zip`：每设备独立快照
 - `manifest.json` + `backup.zip`：v1 时代共享布局，作为"伪设备"长期兼容检查

单轮同步（后台线程执行，互斥防重入）：
  1. GET 根目录 v1 manifest（伪设备，指纹不变则跳过）
  2. GET devices.json → 逐个 GET peer 的 manifest，指纹 ≠ 本机为该设备记录的
     游标（sync_peer_fp_<id>）才 GET backup.zip → DataService.import_data
     内容指纹合并（幂等，绝不覆盖删除）
  3. 重算本地同步指纹，≠ 本机上次推送指纹 → PUT 本机 zip 后【最后】PUT
     manifest——manifest 是提交点：zip 上传中断时远端仍指向旧版，保持一致
     v3 首轮（sync_v3_migrated 未置位）强制推送一次：DB 自 v2 末期无变化时
     指纹相等到不了推送分支，云端会没有 v3 格式的最新快照
  4. 本机不在注册表（首次出现/被并发覆盖）→ GET 最新注册表补登自己后 PUT
     （两台新设备同时登记的竞态由下轮自动补登修复，最终一致）
  5. 一次性清理 v2 遗留的本机子目录（v3 改扁平布局后不再需要；仅在 v3 快照
     已确认落云后执行，成功后落盘 sync_v2_cleaned 标志，稳态零额外请求）

收敛性：合并满足交换律（集并向 + 标志 OR + 分类排序传播），各端各跑一轮后指纹
相等；稳态每轮 = 2 次 GET（v1 探测 + 注册表）+ N 次 peer manifest GET（几十字节
流量），远低于坚果云限额。

同步指纹与合并指纹的区别：
  - 合并指纹（DataService._fingerprint）：内容 only，用于判断"同一条笔记"
  - 同步指纹（本模块）：内容 + 收藏/归档标志 + 分类，用于判断"整个库是否变化"，
    因此收藏状态的修改也能触发推送、经合并 OR 传播
"""
import hashlib
import json
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from ..dao.database import Database
from .config_service import ConfigService
from .data_service import DataService
from .webdav_client import WebDavClient, WebDavError

MANIFEST_FILE = 'manifest.json'
BACKUP_FILE = 'backup.zip'
DEVICES_FILE = 'devices.json'
FIRST_SYNC_DELAY_MS = 30_000  # 启动后 30 秒做首次同步（避开启动高峰）
IMPORT_RETRY_DELAY_S = 3  # 拉取合并瞬时失败（如杀软锁定临时文件）的重试退避


class SyncService(QObject):
    """云同步调度服务（单例；自动同步由主线程 QTimer 驱动，网络 IO 全在后台线程）"""

    syncFinished = pyqtSignal(bool, str)  # 同步结束（成功标志 + 用户可读消息）

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self._worker: threading.Thread = None
        self._timer: QTimer = None
        # 最近一次同步结果（结构化，供 UI/插件判断是否需要刷新窗口）
        self.last_result: dict = {}

    @classmethod
    def get_instance(cls) -> 'SyncService':
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = SyncService()
        return cls._instance

    # ── 配置读写（每次同步重新读盘，设置页改动无需重启） ──

    @staticmethod
    def _load_config() -> dict:
        cs = ConfigService()
        return {
            'enabled': bool(cs.get('webdav_enabled', False)),
            'server': cs.get('webdav_server', 'https://dav.jianguoyun.com/dav/'),
            'account': cs.get('webdav_account', ''),
            'password': cs.get('webdav_password', ''),
            'remote_dir': (cs.get('webdav_dir', 'JotMe') or 'JotMe').strip('/'),
            'interval_min': int(cs.get('sync_interval', 30) or 30),
            'device_id': cs.get('device_id', ''),
            'last_pushed_fp': cs.get('sync_last_pushed_fp', ''),
        }

    @staticmethod
    def _save_state(**kv) -> None:
        cs = ConfigService()
        for key, value in kv.items():
            cs.set(key, value)
        cs.save()

    @staticmethod
    def _ensure_device_id() -> str:
        cs = ConfigService()
        device_id = cs.get('device_id', '')
        if not device_id:
            device_id = f'PC-{hashlib.sha256(str(Path.home()).encode()).hexdigest()[:8]}'
            cs.set('device_id', device_id)
            cs.save()
        return device_id

    # ── 自动同步调度（主线程） ──

    def start_auto_sync(self) -> None:
        """按当前配置启动自动同步定时器（插件加载/设置变更时调用）。

        间隔语义 = "距上次成功同步至少 interval"（跨启动有效）：
        - 已到期/从未成功过 → 启动 30 秒后补一次（避开启动高峰）；
          同步失败不推进成功时间，重开软件即自动重试，故障自愈
        - 未到期 → 不做启动同步（重开软件不再重复触发），到剩余时间点补一次；
          周期定时器从"整周期+剩余"起算，重启不清零 12 小时这类长间隔的倒计时
        """
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        cfg = self._load_config()
        if not cfg['enabled'] or not cfg['account'] or not cfg['password']:
            return
        interval_ms = max(cfg['interval_min'], 5) * 60_000
        elapsed_ms = self._ms_since_last_success()
        if elapsed_ms is None or elapsed_ms >= interval_ms:
            QTimer.singleShot(FIRST_SYNC_DELAY_MS, self._deferred_first_sync)
            self._start_timer(interval_ms)
        else:
            remaining_ms = max(interval_ms - elapsed_ms, 60_000)
            QTimer.singleShot(remaining_ms, self.sync_now)
            # 首拍延后一个整周期，避免与"剩余时间补同步"挨得太近
            self._start_timer(interval_ms + remaining_ms)

    def _start_timer(self, interval_ms: int) -> None:
        self._timer = QTimer()
        self._timer.timeout.connect(self.sync_now)
        self._timer.start(interval_ms)

    def _deferred_first_sync(self) -> None:
        """启动补同步（30 秒延迟后）：延迟期间刚成功同步过（如启用开关时的
        立即同步）则跳过，避免一轮内连续两次同步、弹两次提示"""
        elapsed_ms = self._ms_since_last_success()
        if elapsed_ms is not None and elapsed_ms < FIRST_SYNC_DELAY_MS * 2:
            return
        self.sync_now()

    @staticmethod
    def _ms_since_last_success():
        """距上次成功同步的毫秒数；从未成功过返回 None（失败不推进此时间）"""
        cs = ConfigService()
        raw = cs.get('sync_last_success_time', '')
        if not raw:
            return None
        try:
            last = datetime.strptime(raw, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
        return max(0, int((datetime.now() - last).total_seconds() * 1000))

    # ── 手动/定时触发（主线程） ──

    def sync_now(self) -> None:
        """触发一次同步（已在同步中则忽略）"""
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._do_sync, daemon=True)
        self._worker.start()

    # ── 同步主体（后台线程） ──

    def _do_sync(self) -> None:
        cfg = self._load_config()
        if not cfg['enabled'] or not cfg['account'] or not cfg['password']:
            self._finish(False, '云同步未启用或账号/应用密码未配置', added=0)
            return
        self._ensure_device_id()
        cfg = self._load_config()

        client = WebDavClient(cfg['server'], cfg['account'], cfg['password'])
        notes_before = self._note_count()
        pulled: list = []
        warnings: list = []
        try:
            # 1. v1 兼容：根目录旧共享布局（伪设备，旧客户端仍在写这里）
            self._pull_snapshot(client, cfg, '', '旧版共享备份', pulled, warnings)

            # 2. devices.json 注册表发现其他设备，逐个拉取有变化的快照合并（幂等）
            registry = self._read_registry(client, cfg, warnings)
            for peer in sorted(p for p in registry if p != cfg['device_id']):
                self._pull_snapshot(client, cfg, peer, peer, pulled, warnings)

            # 3. 本库有未推送的变化 → 推送扁平快照（zip 先、manifest 最后——提交点）。
            #    v3 首轮强制推送：DB 自 v2 末期无变化时指纹相等，不强制则云端没有
            #    v3 格式的最新快照，后续的 v2 目录清理就失去了"新快照已落云"前提
            cs = ConfigService()
            force_push = not cs.get('sync_v3_migrated', False)
            local_fp = self.compute_sync_fingerprint()
            pushed = force_push or local_fp != cfg['last_pushed_fp']
            if pushed:
                self._push_snapshot(client, cfg, local_fp)
                if force_push:
                    cs.set('sync_v3_migrated', True)
                    cs.save()

            # 4. 本机不在注册表（首次出现/被并发覆盖）→ 补登自己
            if cfg['device_id'] not in registry:
                self._register_self(client, cfg, warnings)

            # 5. 一次性清理 v2 遗留的本机子目录（v3 快照已确认落云才执行）
            self._cleanup_v2_dir(client, cfg, warnings)

            added = self._note_count() - notes_before
            message = self._build_message(pulled, warnings, added, pushed)
            self._save_state(sync_last_pushed_fp=local_fp if pushed else cfg['last_pushed_fp'])
            self._finish(True, message, added=added)
        except WebDavError as e:
            self._finish(False, str(e), added=self._note_count() - notes_before)
        except Exception as e:  # 网络/磁盘等未预期异常也回报给 UI，绝不清本地数据
            self._finish(False, f'同步异常：{e}', added=self._note_count() - notes_before)

    def _pull_snapshot(self, client: WebDavClient, cfg: dict, device_id: str,
                       label: str, pulled: list, warnings: list) -> None:
        """拉取单个设备（device_id 为空 = v1 根目录伪设备，用原始文件名）的扁平
        快照并按内容指纹合并。

        每设备一个"已合并游标"：指纹没变就不下载 zip（零流量）。
        单个设备失败只记警告、不中断本轮（本机推送不受影响，下轮自动重试）。
        """
        manifest_name = MANIFEST_FILE if not device_id else f'{device_id}.{MANIFEST_FILE}'
        zip_name = BACKUP_FILE if not device_id else f'{device_id}.{BACKUP_FILE}'
        cursor_key = f"sync_peer_fp_{device_id or 'v1'}"
        remote_dir = cfg['remote_dir']
        try:
            raw = client.get_bytes(remote_dir, manifest_name, read_timeout=30)
            if raw is None:
                return
            try:
                remote_fp = json.loads(raw.decode('utf-8')).get('fingerprint') or ''
            except (ValueError, UnicodeDecodeError):
                warnings.append(f'{label} 的 manifest 解析失败，已跳过')
                return
            if not remote_fp:
                return
            cs = ConfigService()
            if remote_fp == cs.get(cursor_key, ''):
                return

            zip_bytes = client.get_bytes(remote_dir, zip_name)
            if zip_bytes is None:
                warnings.append(f'{label} 的 manifest 存在但 backup.zip 缺失')
                return
            with tempfile.TemporaryDirectory(prefix='notes_sync_') as tmp:
                zip_path = Path(tmp) / 'remote.zip'
                zip_path.write_bytes(zip_bytes)
                ok, pull_msg = DataService.import_data(str(zip_path))
                if not ok:
                    # 瞬时故障退避重试一次（实测中杀软会锁定刚解压的临时文件，
                    # 导致 SQLite 报 disk I/O error；游标不更新，仍失败则下轮再试）
                    time.sleep(IMPORT_RETRY_DELAY_S)
                    ok, pull_msg = DataService.import_data(str(zip_path))
            if ok:
                cs.set(cursor_key, remote_fp)
                cs.save()  # 游标立即落盘：本轮后续步骤失败也不会重复下载该快照
                pulled.append(label)
            else:
                warnings.append(f'{label} 合并失败：{pull_msg}')
        except WebDavError as e:
            warnings.append(f'{label} 拉取失败：{e}')

    def _push_snapshot(self, client: WebDavClient, cfg: dict, fingerprint: str) -> None:
        """推送本机全量快照（扁平文件，zip 先、manifest 最后——提交点）"""
        remote_dir = cfg['remote_dir']
        with tempfile.TemporaryDirectory(prefix='notes_sync_') as tmp:
            zip_path = Path(tmp) / 'local.zip'
            ok, msg = DataService.backup_data(str(zip_path))
            if not ok:
                raise WebDavError(f'生成备份失败：{msg}')
            client.put_bytes(remote_dir, f"{cfg['device_id']}.{BACKUP_FILE}",
                             zip_path.read_bytes())
        manifest = {
            'device_id': cfg['device_id'],
            'fingerprint': fingerprint,
            'note_count': self._note_count(),
            'updated_at': datetime.now().isoformat(timespec='seconds'),
        }
        client.put_bytes(remote_dir, f"{cfg['device_id']}.{MANIFEST_FILE}",
                         json.dumps(manifest, ensure_ascii=False).encode('utf-8'))

    def _read_registry(self, client: WebDavClient, cfg: dict,
                       warnings: list) -> list:
        """读设备注册表 devices.json；缺失返回空表，损坏记警告并按空表处理
        （自愈：本机不在表中会随后触发补登重建）"""
        try:
            raw = client.get_bytes(cfg['remote_dir'], DEVICES_FILE, read_timeout=30)
        except WebDavError as e:
            warnings.append(f'设备注册表读取失败：{e}')
            return []
        if raw is None:
            return []
        try:
            devices = json.loads(raw.decode('utf-8')).get('devices')
            if not isinstance(devices, list):
                warnings.append('设备注册表格式异常，已按空表处理')
                return []
            return [d for d in devices if isinstance(d, str) and d]
        except (ValueError, UnicodeDecodeError):
            warnings.append('设备注册表解析失败，已按空表处理')
            return []

    def _register_self(self, client: WebDavClient, cfg: dict,
                       warnings: list) -> None:
        """把本机补登进 devices.json（GET 最新 → 补自己 → PUT；
        登记失败仅警告，下轮重试）"""
        try:
            devices: list = []
            try:
                raw = client.get_bytes(cfg['remote_dir'], DEVICES_FILE, read_timeout=30)
                if raw is not None:
                    parsed = json.loads(raw.decode('utf-8')).get('devices')
                    if isinstance(parsed, list):
                        devices = [d for d in parsed if isinstance(d, str) and d]
            except (WebDavError, ValueError, UnicodeDecodeError):
                pass  # 读不到就按空表重建
            if cfg['device_id'] not in devices:
                devices.append(cfg['device_id'])
                registry = {
                    'devices': devices,
                    'updated_at': datetime.now().isoformat(timespec='seconds'),
                }
                client.put_bytes(
                    cfg['remote_dir'], DEVICES_FILE,
                    json.dumps(registry, ensure_ascii=False).encode('utf-8'))
        except WebDavError as e:
            warnings.append(f'本机登记到设备注册表失败：{e}')

    def _cleanup_v2_dir(self, client: WebDavClient, cfg: dict,
                        warnings: list) -> None:
        """一次性清理 v2 遗留的本机子目录 `/<remote_dir>/<device_id>/`。

        v2 时代 PC 把快照写进自己的子目录；v3 改扁平布局后该目录不再被任何端
        读取，留着既占云盘空间又会误导排查。前置条件 sync_v3_migrated（本轮
        推送成功后已置位）保证删它之前 v3 格式的同数据快照确认已落云。
        仅删本机目录（Android v2 因 WAF 拦截从未建成过目录，无遗留）。
        成功或确认不存在后落盘 sync_v2_cleaned 标志，之后稳态零额外请求；
        失败仅警告，下轮再试。
        """
        cs = ConfigService()
        if cs.get('sync_v2_cleaned', False):
            return
        if not cs.get('sync_v3_migrated', False):
            return  # v3 快照尚未落云，保留 v2 目录作为云端唯一最新备份
        try:
            deleted = client.delete_path(f"{cfg['remote_dir']}/{cfg['device_id']}")
            cs.set('sync_v2_cleaned', True)
            cs.save()
            if deleted:
                warnings.append('已清理 v2 遗留的本机设备目录')
        except WebDavError as e:
            warnings.append(f'清理 v2 遗留目录失败：{e}')

    @staticmethod
    def _build_message(pulled: list, warnings: list, added: int, pushed: bool) -> str:
        parts = []
        if pulled:
            text = '已合并 ' + '、'.join(pulled)
            if added > 0:
                text += f'（新增 {added} 条笔记）'
            parts.append(text)
        parts.extend(warnings)
        if pushed:
            parts.append('已推送本机快照')
        elif not pulled and not warnings:
            parts.append('已是最新，无需同步')
        else:
            parts.append('本机无变更')
        return '；'.join(parts)

    def _finish(self, success: bool, message: str, added: int) -> None:
        self.last_result = {'success': success, 'added_notes': added,
                            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        state = {'sync_last_time': self.last_result['time'],
                 'sync_last_result': '成功' if success else message}
        if success:
            # 成功时间单独记录：自动同步的启动节流以其为基准（失败不推进，重开即重试）
            state['sync_last_success_time'] = self.last_result['time']
        self._save_state(**state)
        self.syncFinished.emit(success, message)

    # ── 同步指纹（整个库的状态哈希） ──

    @staticmethod
    def compute_sync_fingerprint() -> str:
        """库级同步指纹：全部笔记(内容+收藏/归档) + 全部分类，排序后整体哈希。

        与 DataService._fingerprint（单条内容指纹，用于合并去重）分工不同：
        本指纹用于判断"库是否变化/两端是否一致"，故包含收藏/归档标志。
        排序消除两端自增 id 顺序差异，保证合并收敛后两端指纹相等。
        """
        db = Database.get_instance()
        h = hashlib.sha256()
        cats = sorted(
            (f"{r['name']}\x00{r['sort_order']}" for r in
             db.execute('SELECT name, sort_order FROM categories').fetchall())
        )
        h.update(('\x01'.join(cats) + '\x02').encode('utf-8'))
        notes = sorted(
            (f"{DataService._fingerprint(r)}"
             f"\x00{DataService._get(r, 'is_favorite', 0) or 0}"
             f"\x00{DataService._get(r, 'is_archived', 0) or 0}"
             for r in db.execute('SELECT * FROM notes').fetchall())
        )
        h.update('\x01'.join(notes).encode('utf-8'))
        return h.hexdigest()

    @staticmethod
    def _note_count() -> int:
        return Database.get_instance().execute('SELECT COUNT(*) FROM notes').fetchone()[0]

    # ── 连接测试（供设置页调用，后台线程执行） ──

    def test_connection_async(self, server: str, account: str, password: str,
                              callback) -> None:
        """后台测试连接，结果通过回调返回（回调在主线程执行需调用方自行保证）"""

        def run():
            client = WebDavClient(server, account, password)
            ok, msg = client.test_connection()
            try:
                callback(ok, msg)
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()
