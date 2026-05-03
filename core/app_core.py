from typing import Optional
from pathlib import Path
import sys
import shutil
import traceback
from .plugin_manager import PluginManager
from .event_bus import EventBus
from .log import LogManager
from .config import AppConfig
from .utils import get_app_data_path, get_resource_path
from .backup_manager import BackupManager
from .efficiency_mode import set_process_efficiency_mode, is_efficiency_mode_supported
from .search import GlobalSearchManager
from .settings import AISettingsManager
from .ai import AIChatService, AISettingsBridge, AISearchBridge
from qfluentwidgets import qconfig
from storage import DatabaseManager


def init_app_data() -> None:
    """
    初始化应用数据目录
    
    打包后首次运行时，将 data 和 config 从 MEIPASS 复制到 %LOCALAPPDATA%\\FluTool 目录
    """
    if not getattr(sys, 'frozen', False):
        return
    
    try:
        data_dir = get_app_data_path("data")
        config_dir = get_app_data_path("config")
        
        src_data = get_resource_path("data")
        src_config = get_resource_path("config")
        
        print(f"[init_app_data] data_dir: {data_dir}")
        print(f"[init_app_data] src_data: {src_data}")
        print(f"[init_app_data] src_data exists: {src_data.exists()}")
        
        if not data_dir.exists():
            if src_data.exists():
                print(f"[init_app_data] Copying data directory...")
                shutil.copytree(src_data, data_dir)
                print(f"[init_app_data] Data directory copied to: {data_dir}")
            else:
                print(f"[init_app_data] Source data directory not found!")
                data_dir.mkdir(parents=True, exist_ok=True)
        else:
            if src_data.exists():
                for item in src_data.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(src_data)
                        dst_item = data_dir / rel_path
                        if not dst_item.exists():
                            dst_item.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, dst_item)
                            print(f"[init_app_data] Copied: {rel_path}")
        
        if not config_dir.exists():
            if src_config.exists():
                print(f"[init_app_data] Copying config directory...")
                shutil.copytree(src_config, config_dir)
                print(f"[init_app_data] Config directory copied to: {config_dir}")
            else:
                print(f"[init_app_data] Source config directory not found!")
                config_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(f"[init_app_data] Permission denied: {e}")
    except OSError as e:
        print(f"[init_app_data] OS error: {e}")
    except Exception as e:
        print(f"[init_app_data] Unexpected error: {e}")
        traceback.print_exc()


class AppCore:
    """
    应用核心单例类
    
    管理插件生命周期、全局事件、配置、日志等核心服务。
    """
    
    _instance: Optional['AppCore'] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._logger: Optional[LogManager] = None
        self._event_bus: Optional[EventBus] = None
        self._plugin_manager: Optional[PluginManager] = None
        self._config: Optional[AppConfig] = None
        self._config_path: Optional[Path] = None
        self._backup_manager: Optional[BackupManager] = None
        self._search_manager: Optional[GlobalSearchManager] = None
        self._settings_manager: Optional[AISettingsManager] = None
        self._ai_settings: Optional[AISettingsBridge] = None
        self._ai_chat_service: Optional[AIChatService] = None

    def initialize(self, config_path: str = None) -> None:
        """
        初始化核心服务
        
        Args:
            config_path: 配置文件路径，默认为 config/config.json
            
        Raises:
            RuntimeError: 核心服务初始化失败
        """
        init_app_data()
        
        try:
            self._logger = LogManager()
            self._logger.setup_main_logger()
            self._logger.setup_operation_logger()
            self._logger.info("AppCore logger initialized")
        except Exception as e:
            print(f"[AppCore] Failed to initialize logger: {e}")
            raise RuntimeError(f"日志管理器初始化失败：{e}")
        
        try:
            self._event_bus = EventBus()
        except Exception as e:
            self._logger.error(f"Failed to initialize event bus: {e}")
            raise RuntimeError(f"事件总线初始化失败: {e}")
        
        try:
            self._plugin_manager = PluginManager(self)
        except Exception as e:
            self._logger.error(f"Failed to initialize plugin manager: {e}")
            raise RuntimeError(f"插件管理器初始化失败: {e}")
        
        try:
            self._config = AppConfig()
            self._config_path = get_app_data_path("config/config.json")
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            qconfig.load(str(self._config_path), self._config)
        except Exception as e:
            self._logger.error(f"Failed to load config: {e}")
            raise RuntimeError(f"配置加载失败: {e}")
        
        try:
            db_path = get_app_data_path("data/data.db")
            print(f"[AppCore] db_path: {db_path}")
            print(f"[AppCore] db_path exists: {db_path.exists()}")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            DatabaseManager().initialize(str(db_path))
            print(f"[AppCore] Database initialized")
        except Exception as e:
            self._logger.error(f"Failed to initialize database: {e}")
            raise RuntimeError(f"数据库初始化失败: {e}")
        
        try:
            self._backup_manager = BackupManager(self)
            if self._config.auto_backup_enabled.value and self._config.auto_backup_path.value:
                self._backup_manager.check_and_backup()
        except Exception as e:
            self._logger.warning(f"Backup manager initialization failed: {e}")
        
        try:
            self._search_manager = GlobalSearchManager()
        except Exception as e:
            self._logger.warning(f"Search manager initialization failed: {e}")
        
        try:
            self._settings_manager = AISettingsManager()
            self._ai_settings = AISettingsBridge(self._settings_manager)
            self._ai_chat_service = AIChatService(
                settings_bridge=self._ai_settings,
                search_bridge=AISearchBridge(self._search_manager) if self._search_manager else None,
            )
        except Exception as e:
            self._logger.warning(f"AI service initialization failed: {e}")
        
        try:
            if self._config.efficiency_mode.value and is_efficiency_mode_supported():
                set_process_efficiency_mode(True)
                self._logger.info("Efficiency mode enabled")
        except Exception as e:
            self._logger.warning(f"Failed to set efficiency mode: {e}")
        
        self._logger.info("AppCore initialized")

    def shutdown(self) -> None:
        """
        关闭核心服务，释放资源
        """
        shutdown_errors = []
        
        if self._plugin_manager:
            try:
                self._plugin_manager.close_all()
            except Exception as e:
                shutdown_errors.append(f"Plugin manager: {e}")
                self._logger.error(f"Plugin manager shutdown error: {e}")
        
        if self._event_bus:
            try:
                self._event_bus.disconnect_all()
            except Exception as e:
                shutdown_errors.append(f"Event bus: {e}")
                self._logger.error(f"Event bus shutdown error: {e}")
        
        if self._config:
            try:
                qconfig.save()
            except Exception as e:
                shutdown_errors.append(f"Config save: {e}")
                self._logger.error(f"Config save error: {e}")
        
        if shutdown_errors:
            self._logger.warning(f"Shutdown completed with {len(shutdown_errors)} error(s)")
        else:
            self._logger.info("AppCore shutdown completed")

    @property
    def plugin_manager(self) -> PluginManager:
        if self._plugin_manager is None:
            raise RuntimeError("Plugin manager not initialized")
        return self._plugin_manager

    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            raise RuntimeError("Event bus not initialized")
        return self._event_bus

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            raise RuntimeError("Config not initialized")
        return self._config

    @property
    def logger(self) -> LogManager:
        if self._logger is None:
            raise RuntimeError("Logger not initialized")
        return self._logger

    @property
    def backup_manager(self) -> Optional[BackupManager]:
        return self._backup_manager
    
    @property
    def search_manager(self) -> Optional[GlobalSearchManager]:
        return self._search_manager

    @property
    def ai_settings(self) -> Optional[AISettingsBridge]:
        return self._ai_settings

    @property
    def ai_chat_service(self) -> Optional[AIChatService]:
        return self._ai_chat_service
