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
    """后台执行恢复文件操作，避免阻塞 UI。"""

    file_ops_done = pyqtSignal(bool, str, str)  # success, message, backup_path

    def __init__(self, backup_file: str, parent=None):
        super().__init__(parent)
        self._backup_file = backup_file
        self._temp_dir_obj: Optional[tempfile.TemporaryDirectory] = None

    def run(self) -> None:
        backup_path = Path(self._backup_file)
        if not backup_path.exists():
            self.file_ops_done.emit(False, "备份文件不存在", self._backup_file)
            return

        self._temp_dir_obj = tempfile.TemporaryDirectory(prefix="flutool_restore_")
        temp_dir = Path(self._temp_dir_obj.name)
        extracted_data_dir = temp_dir / "data"
        data_dir = get_app_data_path("data")
        backup_target = data_dir.parent / "data.pre_restore_backup"

        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            valid, message = BackupManager._validate_restored_data_static(extracted_data_dir)
            if not valid:
                self.file_ops_done.emit(False, message, self._backup_file)
                return

            # 强制 GC 回收 SQLite 连接，释放文件锁
            gc.collect()
            time.sleep(0.2)

            if backup_target.exists():
                BackupManager._force_rmtree(backup_target)

            if data_dir.exists():
                BackupManager._retry_file_op(lambda: BackupManager._safe_move_dir(data_dir, backup_target))

            if data_dir.exists():
                BackupManager._force_rmtree(data_dir)

            if data_dir.exists():
                shutil.copytree(str(extracted_data_dir), str(data_dir), dirs_exist_ok=True)
                BackupManager._force_rmtree(extracted_data_dir)
            else:
                shutil.move(str(extracted_data_dir), str(data_dir))

            if backup_target.exists():
                BackupManager._force_rmtree(backup_target)

            self.file_ops_done.emit(True, "ok", self._backup_file)
        except Exception as e:
            # 回滚
            if not data_dir.exists() and backup_target.exists():
                try:
                    BackupManager._retry_file_op(
                        lambda: shutil.move(str(backup_target), str(data_dir))
                    )
                except OSError as rollback_err:
                    hint = f"；原数据已保留在 {backup_target.name}，可手动移回 {data_dir.name}"
                    self.file_ops_done.emit(False, f"恢复失败，数据目录回滚失败: {rollback_err}{hint}", self._backup_file)
                    return
            hint = "，请关闭资源管理器/杀毒软件等其他可能占用文件的程序后重试" if isinstance(e, OSError) else ""
            self.file_ops_done.emit(False, f"恢复失败: {e}{hint}", self._backup_file)

    def cleanup(self) -> None:
        if self._temp_dir_obj:
            self._temp_dir_obj.cleanup()


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
    def _safe_move_dir(src: Path, dst: Path) -> None:
        """安全移动目录：先尝试 move，失败则复制+强制删除。"""
        try:
            shutil.move(str(src), str(dst))
        except (OSError, PermissionError):
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            BackupManager._force_rmtree(src)

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

    def restore_backup(self, backup_file: str) -> Tuple[bool, str]:
        """从 zip 备份恢复 data 目录（后台线程执行文件操作，主线程刷新 UI）。"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            message = "备份文件不存在"
            self.restore_failed.emit(message)
            return False, message

        main_window = getattr(self._core, "main_window", None)
        if main_window and hasattr(main_window, "suspend_plugin_io"):
            main_window.suspend_plugin_io()

        # 后台线程执行文件操作
        self._restore_worker = _RestoreWorker(backup_file, self)
        self._restore_worker.file_ops_done.connect(
            lambda ok, msg, path: self._on_restore_done(ok, msg, path, main_window)
        )
        self._restore_worker.start()
        return True, "正在恢复..."

    def _on_restore_done(self, ok: bool, msg: str, backup_path: str, main_window) -> None:
        """后台文件操作完成后的主线程回调。"""
        backup_name = Path(backup_path).name
        if ok:
            try:
                db_path = get_app_data_path("data/data.db")
                DatabaseManager().reinitialize(str(db_path))
                if main_window and hasattr(main_window, "reload_loaded_plugins"):
                    main_window.reload_loaded_plugins()
                self._core.event_bus.emit("data_restored")
                self._core.logger.log_operation("RESTORE", f"从备份文件恢复数据: {backup_name}")
                self.restore_completed.emit(backup_path)
            except Exception as e:
                self._core.logger.error(f"Restore post-processing failed: {e}")
                self.restore_failed.emit(f"恢复后初始化失败: {e}")
        else:
            self._core.logger.error(f"Restore failed: {msg}")
            self.restore_failed.emit(msg)

        if main_window and hasattr(main_window, "resume_plugin_io"):
            main_window.resume_plugin_io()
        if self._restore_worker:
            self._restore_worker.cleanup()
            self._restore_worker = None

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
