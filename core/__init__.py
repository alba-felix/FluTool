from .app_core import AppCore
from .config import AppConfig
from .event_bus import EventBus
from .log import LogManager
from .plugin_interface import PluginInterface
from .plugin_manager import PluginManager
from .settings import SettingsManager
from .utils import get_app_data_path, get_resource_path, get_local_app_data_dir
from .backup_manager import BackupManager
from .efficiency_mode import set_process_efficiency_mode, is_efficiency_mode_supported
from .search import SearchResult

__all__ = [
    'AppCore',
    'PluginInterface',
    'PluginManager',
    'EventBus',
    'AppConfig',
    'LogManager',
    'SettingsManager',
    'BackupManager',
    'set_process_efficiency_mode',
    'is_efficiency_mode_supported',
    'get_app_data_path',
    'get_resource_path',
    'get_local_app_data_dir',
    'SearchResult',
]
