from typing import Optional
from pathlib import Path
import sys
import shutil
from .plugin_manager import PluginManager
from .event_bus import EventBus
from .log import LogManager
from .config import AppConfig
from .utils import get_app_data_path, get_resource_path
from qfluentwidgets import qconfig
from storage.database import DatabaseManager


def init_app_data() -> None:
    """
    初始化应用数据目录
    
    打包后首次运行时，将 data 和 config 从 MEIPASS 复制到 exe 所在目录
    """
    if not getattr(sys, 'frozen', False):
        return
    
    data_dir = get_app_data_path("data")
    config_dir = get_app_data_path("config")
    
    if not data_dir.exists():
        src_data = get_resource_path("data")
        if src_data.exists():
            shutil.copytree(src_data, data_dir)
    
    if not config_dir.exists():
        src_config = get_resource_path("config")
        if src_config.exists():
            shutil.copytree(src_config, config_dir)


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

    def initialize(self, config_path: str = None) -> None:
        """
        初始化核心服务
        
        Args:
            config_path: 配置文件路径，默认为 config/config.json
        """
        init_app_data()
        
        self._logger = LogManager()
        self._event_bus = EventBus()
        self._plugin_manager = PluginManager(self)
        self._config = AppConfig()
        self._config_path = get_app_data_path("config/config.json")
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        qconfig.load(str(self._config_path), self._config)
        
        db_path = get_app_data_path("data/data.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        DatabaseManager().initialize(str(db_path))
        
        self._logger.info("AppCore initialized")

    def shutdown(self) -> None:
        """
        关闭核心服务，释放资源
        """
        if self._plugin_manager:
            self._plugin_manager.close_all()
        if self._event_bus:
            self._event_bus.disconnect_all()
        if self._config:
            qconfig.save()
        self._logger.info("AppCore shutdown")

    @property
    def plugin_manager(self) -> PluginManager:
        return self._plugin_manager

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def config(self) -> AppConfig:
        return self._config

    @property
    def logger(self) -> LogManager:
        return self._logger
