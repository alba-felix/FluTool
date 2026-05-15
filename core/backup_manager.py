import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal
from .utils import get_app_data_path
from storage import DatabaseManager


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
        
        backup_filename = f"flutool_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
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

    def restore_backup(self, backup_file: str) -> Tuple[bool, str]:
        """从 zip 备份恢复 data 目录，并统一刷新已加载插件。"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            message = "备份文件不存在"
            self.restore_failed.emit(message)
            return False, message

        temp_dir_obj = tempfile.TemporaryDirectory(prefix="flutool_restore_")
        temp_dir = Path(temp_dir_obj.name)
        extracted_data_dir = temp_dir / "data"
        data_dir = get_app_data_path("data")
        backup_target = data_dir.parent / "data.pre_restore_backup"

        main_window = getattr(self._core, "main_window", None)

        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            valid, message = self._validate_restored_data(extracted_data_dir)
            if not valid:
                self.restore_failed.emit(message)
                return False, message

            if main_window and hasattr(main_window, "suspend_plugin_io"):
                main_window.suspend_plugin_io()

            if backup_target.exists():
                shutil.rmtree(backup_target)

            if data_dir.exists():
                data_dir.replace(backup_target)

            shutil.move(str(extracted_data_dir), str(data_dir))

            db_path = get_app_data_path("data/data.db")
            DatabaseManager().reinitialize(str(db_path))

            if backup_target.exists():
                shutil.rmtree(backup_target)

            if main_window and hasattr(main_window, "reload_loaded_plugins"):
                main_window.reload_loaded_plugins()
            self._core.event_bus.emit("data_restored")
            self._core.logger.log_operation("RESTORE", f"从备份文件恢复数据: {backup_path.name}")
            self.restore_completed.emit(str(backup_path))
            return True, "数据已恢复"
        except Exception as e:
            self._core.logger.error(f"Restore backup failed: {e}")
            if not data_dir.exists() and backup_target.exists():
                shutil.move(str(backup_target), str(data_dir))
            message = f"恢复失败: {e}"
            self.restore_failed.emit(message)
            return False, message
        finally:
            if main_window and hasattr(main_window, "resume_plugin_io"):
                main_window.resume_plugin_io()
            temp_dir_obj.cleanup()

    def _validate_restored_data(self, extracted_data_dir: Path) -> Tuple[bool, str]:
        """校验恢复包结构，至少要求 data 目录和 data.db 存在。"""
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
