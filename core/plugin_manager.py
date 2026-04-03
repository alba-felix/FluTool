import importlib
import inspect
import pkgutil
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
    """
    
    def __init__(self, core):
        self._core = core
        self._plugins: Dict[str, PluginInterface] = {}
        self._plugin_dirs: Dict[str, Path] = {}
        self._loaded_plugins: Set[str] = set()

    def scan_plugins(self, plugin_path: str) -> List[str]:
        """
        扫描插件目录，返回插件ID列表（按优先级排序）
        
        Args:
            plugin_path: 插件目录路径
            
        Returns:
            发现的插件ID列表
        """
        plugin_dir = Path(plugin_path)
        if not plugin_dir.exists():
            self._core.logger.warning(f"Plugin directory not found: {plugin_path}")
            return []
        
        # 扫描插件并收集优先级信息
        plugin_info: List[Tuple[int, str]] = []  # (priority, plugin_id)
        
        for item in plugin_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugin_id = self._discover_plugin(item)
                if plugin_id:
                    self._plugin_dirs[plugin_id] = item
                    
                    # 获取插件优先级
                    priority = self._get_plugin_priority(plugin_id)
                    plugin_info.append((priority, plugin_id))
        
        # 按优先级排序（数字越小越靠前）
        plugin_info.sort(key=lambda x: x[0])
        
        # 返回排序后的插件ID列表
        return [plugin_id for _, plugin_id in plugin_info]
    
    def _get_plugin_priority(self, plugin_id: str) -> int:
        """
        获取插件优先级
        
        Args:
            plugin_id: 插件ID
            
        Returns:
            优先级数值（默认999）
        """
        try:
            plugin_dir = self._plugin_dirs.get(plugin_id)
            if not plugin_dir:
                return 999
            
            module_name = f"plugins.{plugin_dir.name}"
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    # 获取 PLUGIN_PRIORITY 属性，默认为 999
                    priority = getattr(obj, "PLUGIN_PRIORITY", 999)
                    return int(priority)
        except Exception as e:
            self._core.logger.warning(f"Failed to get priority for {plugin_id}: {e}")
        
        return 999

    def _resolve_plugin_id(self, plugin_class) -> str:
        plugin_id = getattr(plugin_class, "PLUGIN_ID", "")
        if plugin_id:
            return plugin_id
        plugin_id = getattr(plugin_class, "_id", "")
        if plugin_id:
            return plugin_id
        try:
            plugin = plugin_class()
            return plugin.get_id()
        except Exception:
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
        if plugin_id in self._loaded_plugins:
            return self._plugins.get(plugin_id)
        plugin_dir = self._plugin_dirs.get(plugin_id)
        if not plugin_dir:
            return None
        try:
            module_name = f"plugins.{plugin_dir.name}"
            importlib.invalidate_caches()
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
            self._core.logger.error(f"Failed to load plugin {plugin_id}: {e}")
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
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return False
        plugin.shutdown()
        if self._core.search_manager and plugin.supports_search():
            self._core.search_manager.unregister_plugin(plugin_id)
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
        plugin_info: List[Tuple[int, str]] = []  # (priority, plugin_id)
        
        try:
            import plugins as plugins_pkg
            for finder, name, ispkg in pkgutil.iter_modules(plugins_pkg.__path__):
                if not name.startswith('_'):
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
                                
                                # 获取优先级
                                priority = getattr(obj, "PLUGIN_PRIORITY", 999)
                                plugin_info.append((priority, plugin_id))
                                self._core.logger.info(f"Discovered builtin plugin: {plugin_id} (priority: {priority})")
                    except Exception as e:
                        self._core.logger.error(f"Failed to scan builtin plugin {name}: {e}")
        except Exception as e:
            self._core.logger.error(f"Failed to scan builtin plugins: {e}")
        
        # 按优先级排序
        plugin_info.sort(key=lambda x: x[0])
        
        # 返回排序后的插件ID列表
        return [plugin_id for _, plugin_id in plugin_info]
