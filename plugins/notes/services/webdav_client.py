"""
WebDAV 客户端模块（坚果云）
基于 requests 的极薄封装：GET / PUT / DELETE / 连接测试。
仅负责 HTTP 传输，不含任何同步或合并逻辑。

坚果云注意事项：
- 认证必须用「应用密码」（网页端 账户信息→安全选项 生成），登录密码会 401
- PUT 的父目录不存在时返回 409，因此写入前需 ensure_dir（MKCOL）
- MKCOL 对已存在目录返回 405，视为成功
- GET 不存在的父目录返回 409（非标准），与 404 同样按"不存在"处理

协议 v3 说明（2026-08-24）：坚果云 WAF 按 TLS 指纹拦截 Android HttpURLConnection
（conscrypt）的非标准 HTTP 方法（PROPFIND/MKCOL 一律 403，GET/PUT 放行），为让
Android/PC 走同一套同步协议，v3 全程只用 GET/PUT（设备发现改 devices.json 注册
表、文件布局改扁平，见 sync_service.py）。PC 端 requests 不受 WAF 影响，保留
MKCOL 仅为确保远端根目录存在（Android 无法建目录，全新云盘首次部署需 PC 先建），
DELETE 仅为一次性清理 v2 遗留的设备子目录；二者均不出现在稳态同步流量中。
"""
from typing import Optional
from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_SERVER = 'https://dav.jianguoyun.com/dav/'


class WebDavError(Exception):
    """WebDAV 传输错误（网络/认证/服务器异常）"""


class WebDavClient:
    """坚果云 WebDAV 客户端（每次同步独立实例，Session 不跨线程共享）"""

    def __init__(self, server: str, account: str, password: str):
        self.server = (server or DEFAULT_SERVER).strip()
        if not self.server.endswith('/'):
            self.server += '/'
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(account, password)

    # ── 内部 ──

    def _url(self, remote_dir: str, filename: str = '') -> str:
        """拼接远端完整 URL（目录/文件名做 URL 编码，中文文件名安全）"""
        dir_path = (remote_dir or '').strip('/')
        path = f'{dir_path}/{filename}' if filename else dir_path
        return f'{self.server}{quote(path)}'

    # ── 公开操作 ──

    def get_bytes(self, remote_dir: str, filename: str,
                  read_timeout: int = 300) -> Optional[bytes]:
        """下载远端文件，返回内容；文件不存在返回 None；其他错误抛 WebDavError"""
        try:
            resp = self.session.get(self._url(remote_dir, filename),
                                    timeout=(10, read_timeout))
            # 404=文件不存在；409=坚果云对"父目录不存在"的返回（非标准），均视为不存在
            if resp.status_code in (404, 409):
                return None
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            raise WebDavError(f'下载 {filename} 失败：{e}') from e

    def put_bytes(self, remote_dir: str, filename: str, data: bytes,
                  read_timeout: int = 300) -> None:
        """上传文件；父目录不存在时自动先建目录"""
        try:
            self.ensure_dir(remote_dir)
            # 注意：timeout 元组第一项也会作用于大 body 的写超时（urllib3 语义），
            # 若用 (10, 300)，约 200KB/s 的上行速度下传到 ~2MB 即抛 write timeout，
            # 故 connect 也必须给大值
            resp = self.session.put(self._url(remote_dir, filename), data=data,
                                    timeout=(read_timeout, read_timeout))
            resp.raise_for_status()
        except requests.RequestException as e:
            raise WebDavError(f'上传 {filename} 失败：{e}') from e

    def ensure_dir(self, remote_dir: str) -> None:
        """确保远端目录存在（不存在则 MKCOL 创建；已存在/创建成功均静默通过）"""
        if not remote_dir or not remote_dir.strip('/'):
            return
        try:
            resp = self.session.request(
                'MKCOL', self._url(remote_dir), timeout=(10, 30)
            )
            # 201=创建成功；405=已存在；其余视为失败
            if resp.status_code not in (201, 405):
                raise WebDavError(f'创建远端目录 {remote_dir} 失败：HTTP {resp.status_code}')
        except requests.RequestException as e:
            raise WebDavError(f'创建远端目录 {remote_dir} 失败：{e}') from e

    def delete_path(self, remote_dir: str, filename: str = '') -> bool:
        """删除远端文件或目录（DELETE，目录递归删除）。

        目标不存在（404/坚果云 409）返回 False，删除成功返回 True，其余抛 WebDavError。
        仅用于一次性清理 v2 遗留目录，稳态同步不调用。
        """
        try:
            resp = self.session.delete(self._url(remote_dir, filename),
                                       timeout=(10, 60))
            if resp.status_code in (404, 409):
                return False
            if resp.status_code == 401:
                raise WebDavError('认证失败：请核对账号与应用密码（必须是应用密码，非登录密码）')
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            raise WebDavError(f'删除 {filename or remote_dir} 失败：{e}') from e

    def test_connection(self) -> tuple:
        """测试连接与凭据，返回 (success, message)。

        用「GET 一个必然不存在的探测文件」实现（与 Android 端一致，全程不依赖
        非标准 HTTP 方法）：404/409 = 连通且认证通过（服务器对鉴权失败一律先回
        401）；不能 GET 目录（坚果云对目录 GET 返回 403）。
        """
        try:
            resp = self.session.get(self._url('', '__jotme_probe__'),
                                    timeout=(10, 15))
            if resp.status_code == 401:
                return False, '认证失败：请核对账号与应用密码（必须是应用密码，非登录密码）'
            if resp.status_code in (404, 409):
                return True, '连接成功'
            return False, f'服务器响应异常：HTTP {resp.status_code}'
        except requests.RequestException as e:
            return False, f'无法连接服务器：{e}'
