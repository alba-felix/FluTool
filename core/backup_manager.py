import os
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal
from .utils import get_app_data_path


class BackupManager(QObject):
    """
    备份管理器
    
    在应用启动时检查并执行备份（每天一次）。
    """
    
    backup_completed = pyqtSignal(str)
    backup_failed = pyqtSignal(str)
    
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
        
        backup_filename = "flutool_backup.zip"
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
        """手动备份到指定路径"""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        return self._execute_backup(backup_path, date_str)
    
    def is_enabled(self) -> bool:
        """检查自动备份是否启用"""
        return self._core.config.auto_backup_enabled.value
    
    def get_backup_path(self) -> str:
        """获取备份路径"""
        return self._core.config.auto_backup_path.value or ""
