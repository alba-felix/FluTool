import gc
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Any, Callable, Optional, Tuple
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from .utils import get_app_data_path
from storage import DatabaseManager


class _RestoreWorker(QThread):
    """后台执行恢复文件操作，避免阻塞 UI 主线程。"""

    files_done = pyqtSignal(bool, str, str)  # ok, message, backup_file

    def __init__(self, backup_path: Path, logger, parent=None):
        super().__init__(parent)
        self._backup_path = backup_path
        self._logger = logger

    def run(self) -> None:
        ok, message = BackupManager._restore_files_sync(self._backup_path, self._logger)
        self.files_done.emit(ok, message, str(self._backup_path))


class BackupManager(QObject):
    """
    备份管理器

    在应用启动时检查并执行备份（每天一次）。
    """

    backup_completed = pyqtSignal(str)
    backup_failed = pyqtSignal(str)
    restore_completed = pyqtSignal(str)
    restore_failed = pyqtSignal(str)

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self._core = core
        self._last_backup_date: Optional[str] = None
        self._restore_worker: Optional[_RestoreWorker] = None

    def _on_restore_files_done(self, ok: bool, message: str, backup_file: str) -> None:
        """后台文件操作完成后回到主线程执行后处理（worker 信号自动排队到主线程）。"""
        # 线程已结束，清理 worker 防止在对象树上累积泄漏
        if self._restore_worker is not None:
            self._restore_worker.deleteLater()
            self._restore_worker = None

        if not ok:
            self.restore_failed.emit(message)
            return
        self._post_restore(Path(backup_file))
        self.restore_completed.emit(backup_file)
    
    def check_and_backup(self) -> None:
        """检查并执行备份（每天一次）"""
        if not self._core.config.auto_backup_enabled.value:
            return
        
        backup_path = self._core.config.auto_backup_path.value
        if not backup_path:
            return
        
        self._last_backup_date = self._load_last_backup_date()
        
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        if self._last_backup_date == today_str:
            return
        
        self._execute_backup(backup_path, today_str)
    
    def _load_last_backup_date(self) -> Optional[str]:
        """加载上次备份日期"""
        backup_info_path = get_app_data_path("data/.backup_info")
        if backup_info_path.exists():
            try:
                return backup_info_path.read_text(encoding='utf-8').strip()
            except Exception:
                pass
        return None
    
    def _save_last_backup_date(self, date_str: str) -> None:
        """保存备份日期"""
        backup_info_path = get_app_data_path("data/.backup_info")
        backup_info_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            backup_info_path.write_text(date_str, encoding='utf-8')
        except Exception as e:
            self._core.logger.error(f"Failed to save backup date: {e}")
    
    def _execute_backup(self, backup_dir: str, date_str: str) -> bool:
        """执行备份操作"""
        backup_dir_path = Path(backup_dir)
        if not backup_dir_path.exists():
            try:
                backup_dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self._core.logger.error(f"Failed to create backup directory: {e}")
                self.backup_failed.emit(f"无法创建备份目录: {e}")
                return False
        
        data_dir = get_app_data_path("data")
        if not data_dir.exists():
            self._core.logger.warning("Data directory not found, skip backup")
            return False
        
        backup_filename = f"flutool_backup_{datetime.now().strftime('%Y%m')}.zip"
        backup_file_path = backup_dir_path / backup_filename
        
        try:
            with zipfile.ZipFile(backup_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(data_dir):
                    for file in files:
                        if file == '.backup_info':
                            continue
                        file_path_full = Path(root) / file
                        arcname = file_path_full.relative_to(data_dir.parent)
                        zipf.write(file_path_full, arcname)
            
            self._last_backup_date = date_str
            self._save_last_backup_date(date_str)
            self._core.logger.info(f"Auto backup completed: {backup_file_path}")
            self.backup_completed.emit(str(backup_file_path))
            return True
        
        except Exception as e:
            self._core.logger.error(f"Auto backup failed: {e}")
            self.backup_failed.emit(f"备份失败: {e}")
            return False
    
    def manual_backup(self, backup_path: str) -> bool:
        """手动备份到指定 zip 文件路径。"""
        target_path = Path(backup_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        data_dir = get_app_data_path("data")
        if not data_dir.exists():
            self._core.logger.warning("Data directory not found, skip backup")
            return False

        try:
            with zipfile.ZipFile(target_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(data_dir):
                    for file in files:
                        if file == '.backup_info':
                            continue
                        file_path_full = Path(root) / file
                        arcname = file_path_full.relative_to(data_dir.parent)
                        zipf.write(file_path_full, arcname)
            self._core.logger.info(f"Manual backup completed: {target_path}")
            self.backup_completed.emit(str(target_path))
            return True
        except Exception as e:
            self._core.logger.error(f"Manual backup failed: {e}")
            self.backup_failed.emit(f"备份失败: {e}")
            return False

    @staticmethod
    def _retry_file_op(op: Callable[[], Any], retries: int = 3) -> Any:
        """重试文件操作，缓解杀毒/索引器/资源管理器瞬时占用导致的 WinError 5/32"""
        last_err: Optional[OSError] = None
        for attempt in range(retries):
            try:
                return op()
            except (OSError, PermissionError) as e:
                last_err = e
                if attempt < retries - 1:
                    time.sleep(0.5 * (attempt + 1))
        raise last_err

    @staticmethod
    def _force_rmtree(path: Path, retries: int = 5) -> None:
        """强制删除目录，重试多次应对文件占用。"""
        for attempt in range(retries):
            if not path.exists():
                return
            try:
                shutil.rmtree(str(path))
                return
            except (OSError, PermissionError):
                if attempt < retries - 1:
                    gc.collect()
                    time.sleep(0.5 * (attempt + 1))
        # 最后一次仍失败，忽略错误继续（文件可能已被释放）
        shutil.rmtree(str(path), ignore_errors=True)

    @staticmethod
    def _restore_files_sync(backup_path: Path, logger=None) -> Tuple[bool, str]:
        """恢复流程的纯文件操作部分（解压/替换/清理），可在线程中执行。

        返回 (ok, message)。logger 可为 None（测试场景）。
        """
        def _log(level: str, msg: str) -> None:
            if logger is not None:
                getattr(logger, level)(msg)

        data_dir = get_app_data_path("data")
        backup_target = data_dir.parent / "data.pre_restore_backup"

        temp_dir_obj = tempfile.TemporaryDirectory(prefix="flutool_restore_")
        temp_dir = Path(temp_dir_obj.name)
        extracted_data_dir = temp_dir / "data"

        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            valid, message = BackupManager._validate_restored_data_static(extracted_data_dir)
            if not valid:
                return False, message

            # 强制 GC 回收 SQLite 连接，释放文件锁
            gc.collect()
            time.sleep(0.2)

            if backup_target.exists():
                BackupManager._force_rmtree(backup_target)

            # 旧目录原子改名移开；rename 失败（目录被资源管理器/杀毒占用）降级为复制备份
            if data_dir.exists():
                try:
                    BackupManager._retry_file_op(lambda: data_dir.replace(backup_target))
                except OSError as move_err:
                    _log("warning", f"Rename failed, fallback to copy backup: {move_err}")
                    try:
                        shutil.copytree(str(data_dir), str(backup_target), dirs_exist_ok=True)
                    except OSError as copy_err:
                        _log("error", f"Restore backup copy failed: {copy_err}")
                        message = (
                            f"无法备份旧数据目录（文件被占用）: {copy_err}，"
                            "请关闭资源管理器/杀毒软件等可能占用文件的程序后重试"
                        )
                        return False, message
                    # 旧数据已复制备份，删除原目录（残留锁定文件不影响后续覆盖合并）
                    BackupManager._force_rmtree(data_dir)

            # 放入新数据：目录已删则 move；仍有残留（锁定文件）则覆盖合并
            if data_dir.exists():
                shutil.copytree(str(extracted_data_dir), str(data_dir), dirs_exist_ok=True)
                BackupManager._force_rmtree(extracted_data_dir)
            else:
                shutil.move(str(extracted_data_dir), str(data_dir))
            if backup_target.exists():
                BackupManager._force_rmtree(backup_target)

            return True, "数据恢复成功"
        except Exception as e:
            # 回滚：新数据未就位时把旧目录移回
            if not data_dir.exists() and backup_target.exists():
                try:
                    BackupManager._retry_file_op(lambda: backup_target.replace(data_dir))
                except OSError as rollback_err:
                    message = (
                        f"恢复失败，数据目录回滚失败: {rollback_err}；"
                        f"原数据已保留在 {backup_target.name}，可手动移回 {data_dir.name}"
                    )
                    return False, message
            hint = "，请关闭资源管理器/杀毒软件等其他可能占用文件的程序后重试" if isinstance(e, OSError) else ""
            _log("error", f"Restore failed: {e}")
            return False, f"恢复失败: {e}{hint}"
        finally:
            temp_dir_obj.cleanup()

    def _post_restore(self, backup_path: Path) -> None:
        """恢复成功后的主线程后处理：重建数据库连接并广播事件。"""
        try:
            db_path = get_app_data_path("data/data.db")
            DatabaseManager().reinitialize(str(db_path))
            self._core.event_bus.emit("data_restored")
            self._core.logger.log_operation("RESTORE", f"从备份文件恢复数据: {backup_path.name}")
        except Exception as e:
            self._core.logger.error(f"Restore post-processing failed: {e}")

    def restore_backup(self, backup_file: str) -> Tuple[bool, str]:
        """从 zip 备份恢复（同步版本，主要用于测试；UI 请用 restore_backup_async）。"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            message = "备份文件不存在"
            self.restore_failed.emit(message)
            return False, message

        ok, message = self._restore_files_sync(backup_path, self._core.logger)
        if not ok:
            self.restore_failed.emit(message)
            return False, message

        self._post_restore(backup_path)
        self.restore_completed.emit(str(backup_path))
        return True, message

    def restore_backup_async(self, backup_file: str) -> Tuple[bool, str]:
        """从 zip 备份恢复（后台线程执行文件操作，不阻塞 UI）。

        结果通过 restore_completed / restore_failed 信号通知。
        """
        backup_path = Path(backup_file)
        if not backup_path.exists():
            message = "备份文件不存在"
            self.restore_failed.emit(message)
            return False, message

        if self._restore_worker is not None and self._restore_worker.isRunning():
            message = "恢复正在进行中，请稍候"
            self.restore_failed.emit(message)
            return False, message

        self._restore_worker = _RestoreWorker(backup_path, self._core.logger, self)
        self._restore_worker.files_done.connect(self._on_restore_files_done)
        self._restore_worker.start()
        return True, "正在恢复数据..."

    def _validate_restored_data(self, extracted_data_dir: Path) -> Tuple[bool, str]:
        """校验恢复包结构，至少要求 data 目录和 data.db 存在。"""
        return self._validate_restored_data_static(extracted_data_dir)

    @staticmethod
    def _validate_restored_data_static(extracted_data_dir: Path) -> Tuple[bool, str]:
        """校验恢复包结构（静态方法，供 worker 调用）。"""
        if not extracted_data_dir.exists() or not extracted_data_dir.is_dir():
            return False, "备份包缺少 data 目录"

        db_path = extracted_data_dir / "data.db"
        if not db_path.exists():
            return False, "备份包缺少 data/data.db"

        return True, "ok"
    
    def is_enabled(self) -> bool:
        """检查自动备份是否启用"""
        return self._core.config.auto_backup_enabled.value
    
    def get_backup_path(self) -> str:
        """获取备份路径"""
        return self._core.config.auto_backup_path.value or ""
