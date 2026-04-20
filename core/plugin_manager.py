import importlib
import inspect
import pkgutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from .plugin_interface import PluginInterface


class PluginManager:
    """
    插件管理器
    
    支持懒加载机制：
    1. scan_plugins() - 扫描插件目录，注册插件元信息
    2. load_plugin() - 加载单个插件（initialize）
    3. get_plugin_widget() - 获取插件界面（懒加载）
    
    所有插件操作都有错误隔离，不会影响主线程
    """
    
    def __init__(self, core):
        if core is None:
            raise ValueError("Core instance cannot be None")
        self._core = core
        self._plugins: Dict[str, PluginInterface] = {}
        self._plugin_dirs: Dict[str, Path] = {}
        self._loaded_plugins: Set[str] = set()
        self._failed_plugins: Set[str] = set()

    def scan_plugins(self, plugin_path: str) -> List[str]:
        """
        扫描插件目录，返回插件ID列表（按优先级排序）
        
        Args:
            plugin_path: 插件目录路径
            
        Returns:
            发现的插件ID列表
        """
        if not plugin_path:
            self._core.logger.warning("Plugin path is empty")
            return []
        
        plugin_dir = Path(plugin_path)
        if not plugin_dir.exists():
            self._core.logger.warning(f"Plugin directory not found: {plugin_path}")
            return []
        
        if not plugin_dir.is_dir():
            self._core.logger.warning(f"Plugin path is not a directory: {plugin_path}")
            return []
        
        plugin_info: List[Tuple[int, str]] = []
        
        try:
            for item in plugin_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    plugin_id = self._discover_plugin(item)
                    if plugin_id:
                        self._plugin_dirs[plugin_id] = item
                        priority = self._get_plugin_priority(plugin_id)
                        plugin_info.append((priority, plugin_id))
        except PermissionError as e:
            self._core.logger.error(f"Permission denied accessing plugin directory: {e}")
        except OSError as e:
            self._core.logger.error(f"OS error scanning plugins: {e}")
        
        plugin_info.sort(key=lambda x: x[0])
        return [plugin_id for _, plugin_id in plugin_info]
    
    def _get_plugin_priority(self, plugin_id: str) -> int:
        """
        获取插件优先级
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            优先级数值（默认999）
        """
        if not plugin_id:
            return 999
        
        plugin_dir = self._plugin_dirs.get(plugin_id)
        if not plugin_dir:
            return 999
        
        try:
            module_name = f"plugins.{plugin_dir.name}"
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    priority = getattr(obj, "PLUGIN_PRIORITY", 999)
                    return int(priority) if priority is not None else 999
        except Exception as e:
            self._core.logger.warning(f"Failed to get priority for {plugin_id}: {e}")
        
        return 999

    def _resolve_plugin_id(self, plugin_class) -> str:
        if plugin_class is None:
            return ""
        
        plugin_id = getattr(plugin_class, "PLUGIN_ID", "")
        if plugin_id:
            return plugin_id
        plugin_id = getattr(plugin_class, "_id", "")
        if plugin_id:
            return plugin_id
        
        try:
            plugin = plugin_class()
            return plugin.get_id()
        except Exception as e:
            self._core.logger.debug(f"Failed to instantiate plugin class for ID resolution: {e}")
            return ""

    def _discover_plugin(self, plugin_dir: Path) -> Optional[str]:
        """
        发现插件但不加载
        
        Args:
            plugin_dir: 插件目录
            
        Returns:
            插件ID或None
        """
        try:
            module_name = f"plugins.{plugin_dir.name}"
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    plugin_id = self._resolve_plugin_id(obj)
                    if plugin_id:
                        return plugin_id
        except Exception as e:
            self._core.logger.error(f"Failed to discover plugin from {plugin_dir}: {e}")
        return None

    def load_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """
        加载指定插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            加载的插件对象或None
        """
        if not plugin_id:
            self._core.logger.warning("Plugin ID is empty")
            return None
        
        if plugin_id in self._loaded_plugins:
            return self._plugins.get(plugin_id)
        
        if plugin_id in self._failed_plugins:
            self._core.logger.debug(f"Plugin {plugin_id} already failed to load, skipping")
            return None
        
        plugin_dir = self._plugin_dirs.get(plugin_id)
        if not plugin_dir:
            self._core.logger.warning(f"Plugin directory not found for {plugin_id}")
            return None
        
        try:
            module_name = f"plugins.{plugin_dir.name}"
            importlib.invalidate_caches()
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    
                    try:
                        plugin = obj()
                        
                        # 为插件设置专用日志记录器
                        plugin_logger = self._core.logger.get_plugin_logger(plugin_id)
                        plugin._set_logger(plugin_logger)
                        
                        plugin.initialize(self._core)
                        
                        actual_id = plugin.get_id()
                        if not actual_id:
                            self._core.logger.warning(f"Plugin has no ID, using {plugin_id}")
                            actual_id = plugin_id
                        
                        self._plugins[actual_id] = plugin
                        self._loaded_plugins.add(actual_id)
                        
                        if self._core.search_manager and plugin.supports_search():
                            try:
                                self._core.search_manager.register_plugin(plugin)
                            except Exception as e:
                                self._core.logger.error(f"Failed to register search for {plugin_id}: {e}")
                        
                        plugin_logger.info(f"Plugin '{plugin.get_name()}' initialized")
                        return plugin
                        
                    except Exception as e:
                        self._failed_plugins.add(plugin_id)
                        self._core.logger.error(f"Failed to initialize plugin {plugin_id}: {e}")
                        self._core.logger.debug(traceback.format_exc())
                        return None
                        
        except ImportError as e:
            self._failed_plugins.add(plugin_id)
            self._core.logger.error(f"Failed to import plugin {plugin_id}: {e}")
        except Exception as e:
            self._failed_plugins.add(plugin_id)
            self._core.logger.error(f"Failed to load plugin {plugin_id}: {e}")
            self._core.logger.debug(traceback.format_exc())
            
        return None

    def load_all_plugins(self, plugin_path: str) -> None:
        """
        加载所有插件
        
        Args:
            plugin_path: 插件目录路径
        """
        plugin_dir = Path(plugin_path)
        if not plugin_dir.exists():
            self._core.logger.warning(f"Plugin directory not found: {plugin_path}")
            return
        for item in plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                self._load_plugin(item)

    def _load_plugin(self, plugin_dir: Path) -> Optional[PluginInterface]:
        """
        加载单个插件
        
        Args:
            plugin_dir: 插件目录
            
        Returns:
            加载的插件对象或None
        """
        try:
            module_name = f"plugins.{plugin_dir.name}"
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    plugin = obj()
                    plugin.initialize(self._core)
                    self._plugins[plugin.get_id()] = plugin
                    self._loaded_plugins.add(plugin.get_id())
                    if self._core.search_manager and plugin.supports_search():
                        self._core.search_manager.register_plugin(plugin)
                    self._core.logger.info(f"Loaded plugin: {plugin.get_name()}")
                    return plugin
        except Exception as e:
            self._core.logger.error(f"Failed to load plugin from {plugin_dir}: {e}")
        return None

    def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            是否成功卸载
        """
        if not plugin_id:
            return False
        
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return False
        
        try:
            plugin.shutdown()
        except Exception as e:
            self._core.logger.error(f"Error during plugin shutdown {plugin_id}: {e}")
        
        if self._core.search_manager and plugin.supports_search():
            try:
                self._core.search_manager.unregister_plugin(plugin_id)
            except Exception as e:
                self._core.logger.error(f"Error unregistering search for {plugin_id}: {e}")
        
        del self._plugins[plugin_id]
        self._loaded_plugins.discard(plugin_id)
        self._core.logger.info(f"Unloaded plugin: {plugin_id}")
        return True

    def get_plugins(self) -> List[PluginInterface]:
        """获取所有已加载的插件"""
        return list(self._plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """获取指定插件"""
        return self._plugins.get(plugin_id)

    def is_loaded(self, plugin_id: str) -> bool:
        """检查插件是否已加载"""
        return plugin_id in self._loaded_plugins

    def get_discovered_plugins(self) -> List[str]:
        """获取已发现的插件ID列表"""
        return list(self._plugin_dirs.keys())

    def clear(self) -> None:
        """清理所有已加载的插件"""
        for plugin_id in list(self._plugins.keys()):
            self.unload_plugin(plugin_id)

    def close_all(self) -> None:
        """关闭所有插件并清理资源"""
        self.clear()
        self._plugin_dirs.clear()

    def scan_builtin_plugins(self) -> List[str]:
        """
        扫描内置插件（打包后使用）
        从已导入的 plugins 子模块中发现插件（按优先级排序）
        """
        plugin_info: List[Tuple[int, str]] = []
        
        try:
            import plugins as plugins_pkg
        except ImportError as e:
            self._core.logger.error(f"Failed to import plugins package: {e}")
            return []
        
        try:
            for finder, name, ispkg in pkgutil.iter_modules(plugins_pkg.__path__):
                if name.startswith('_'):
                    continue
                    
                module_name = f"plugins.{name}"
                try:
                    module = importlib.import_module(module_name)
                    for attr_name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, PluginInterface) and 
                            obj is not PluginInterface and
                            obj.__module__ == module.__name__):
                            plugin_id = self._resolve_plugin_id(obj)
                            if not plugin_id:
                                continue
                            self._plugin_dirs[plugin_id] = Path(name)
                            
                            priority = getattr(obj, "PLUGIN_PRIORITY", 999)
                            priority = int(priority) if priority is not None else 999
                            plugin_info.append((priority, plugin_id))
                            self._core.logger.info(f"Discovered builtin plugin: {plugin_id} (priority: {priority})")
                except ImportError as e:
                    self._core.logger.error(f"Failed to import builtin plugin {name}: {e}")
                except Exception as e:
                    self._core.logger.error(f"Failed to scan builtin plugin {name}: {e}")
        except Exception as e:
            self._core.logger.error(f"Failed to scan builtin plugins: {e}")
        
        plugin_info.sort(key=lambda x: x[0])
        return [plugin_id for _, plugin_id in plugin_info]
