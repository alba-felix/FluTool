import importlib
import importlib.resources
import ast
import inspect
import pkgutil
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from .plugin_interface import PluginInterface
from .plugin_cache import restore_scan_cache, save_scan_cache
from .plugin_manifest import (
    MANIFEST_FILENAMES,
    ManifestReaderFactory,
    PluginManifest,
    normalize_string,
    normalize_priority,
)


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
        self._plugin_modules: Dict[str, str] = {}
        self._loaded_plugins: Set[str] = set()
        self._failed_plugins: Set[str] = set()
        self._manifest_reader_factory = ManifestReaderFactory()

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
        
        # 尝试从缓存恢复
        cached = restore_scan_cache(scan_base=plugin_dir)
        if cached:
            cached_ids, cached_dirs, cached_modules = cached
            self._plugin_dirs.update(cached_dirs)
            self._plugin_modules.update(cached_modules)
            self._core.logger.info(f"Loaded {len(cached_ids)} plugins from cache")
            return cached_ids

        plugin_info: List[Tuple[float, str]] = []

        try:
            for item in plugin_dir.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    manifest = self._read_plugin_manifest(item)
                    if manifest and manifest.is_valid:
                        self._plugin_dirs[manifest.plugin_id] = item
                        self._plugin_modules[manifest.plugin_id] = manifest.module_name or f"plugins.{item.name}"
                        plugin_info.append((manifest.priority, manifest.plugin_id))
        except PermissionError as e:
            self._core.logger.error(f"Permission denied accessing plugin directory: {e}")
        except OSError as e:
            self._core.logger.error(f"OS error scanning plugins: {e}")

        plugin_info.sort(key=lambda x: x[0])
        plugin_ids = [plugin_id for _, plugin_id in plugin_info]

        save_scan_cache(plugin_ids, self._plugin_dirs, self._plugin_modules, plugin_dir)

        return plugin_ids

    def _read_plugin_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """读取插件元信息，不导入插件主体模块

        优先使用读取器工厂尝试 plugin.py / plugin.json，
        回退到 __init__.py AST 解析（兼容旧版插件）。
        """
        manifest = self._manifest_reader_factory.read_manifest(plugin_dir, self._core.logger)
        if manifest:
            return manifest
        return self._read_plugin_python_manifest(plugin_dir)

    def _read_builtin_plugin_manifest(self, plugin_name: str) -> Optional[PluginManifest]:
        """从包资源读取内置插件元信息，不导入插件主体模块"""
        manifest = self._read_builtin_manifest_from_resources(plugin_name)
        if manifest:
            return manifest
        return self._read_builtin_manifest_from_path(plugin_name)

    def _read_builtin_manifest_from_resources(self, plugin_name: str) -> Optional[PluginManifest]:
        """从包资源目录读取内置插件 manifest"""
        try:
            plugin_dir = importlib.resources.files("plugins").joinpath(plugin_name)
            if not plugin_dir.is_dir():
                return None
            return self._manifest_reader_factory.read_manifest(plugin_dir, self._core.logger)
        except (FileNotFoundError, ModuleNotFoundError):
            return None
        except Exception as e:
            self._core.logger.debug(f"Failed to read builtin manifest for {plugin_name}: {e}")
            return None

    def _read_builtin_manifest_from_path(self, plugin_name: str) -> Optional[PluginManifest]:
        """从已加载 plugins 包路径读取内置插件 manifest"""
        plugins_pkg = sys.modules.get("plugins")
        package_paths = getattr(plugins_pkg, "__path__", []) if plugins_pkg is not None else []
        for package_path in package_paths:
            plugin_dir = Path(package_path) / plugin_name
            if plugin_dir.is_dir():
                manifest = self._manifest_reader_factory.read_manifest(plugin_dir, self._core.logger)
                if manifest:
                    return manifest
        return None

    def _read_builtin_plugin_manifest_from_index(
        self,
        plugin_name: str,
    ) -> Optional[PluginManifest]:
        """从显式索引读取内置插件元信息"""
        manifest = self._get_builtin_plugin_index().get(plugin_name)
        if not manifest:
            return None

        plugin_id = normalize_string(manifest.get("id"))
        if not plugin_id:
            self._core.logger.warning(f"Plugin index missing id: {plugin_name}")
            return None

        priority = normalize_priority(manifest.get("priority", 999))
        module_name = normalize_string(manifest.get("module"))
        return PluginManifest(
            plugin_id=plugin_id,
            priority=priority,
            module_name=module_name,
            source=f"plugin_index:{plugin_name}",
        )

    def _get_builtin_plugin_index(self) -> Dict[str, Dict[str, Any]]:
        """获取显式内置插件索引"""
        try:
            from plugins import plugin_index
        except Exception as e:
            self._core.logger.debug(f"Failed to read builtin plugin index: {e}")
            return {}

        manifests: Dict[str, Dict[str, Any]] = {}
        indexed_manifests = getattr(plugin_index, "BUILTIN_PLUGIN_MANIFESTS", None)
        indexed_packages = getattr(plugin_index, "BUILTIN_PLUGIN_PACKAGES", None)

        if isinstance(indexed_manifests, (list, tuple)):
            for item in indexed_manifests:
                if not isinstance(item, dict):
                    continue
                package_name = normalize_string(item.get("package"))
                if not package_name:
                    continue
                manifests[package_name] = dict(item)
            return manifests

        if not isinstance(indexed_packages, (list, tuple)):
            self._core.logger.warning("Builtin plugin index must be a list or tuple")
            return {}

        for package_name in indexed_packages:
            normalized = normalize_string(package_name)
            if not normalized:
                continue
            manifests[normalized] = {
                "package": normalized,
                "id": normalized,
                "priority": 999,
                "module": f"plugins.{normalized}",
            }
        return manifests

    def _iter_builtin_plugin_names(self, plugins_pkg) -> List[str]:
        """列出内置插件包名，兼容 PyInstaller 下 pkgutil 枚举为空的情况"""
        names: List[str] = []
        seen: Set[str] = set()

        def add_name(name: Any) -> None:
            normalized = normalize_string(name)
            if not normalized or normalized.startswith("_") or normalized in seen:
                return
            seen.add(normalized)
            names.append(normalized)

        for name in self._iter_builtin_plugin_names_from_index():
            add_name(name)
        for name in self._iter_builtin_plugin_names_from_resources():
            add_name(name)
        for name in self._iter_builtin_plugin_names_from_paths(plugins_pkg):
            add_name(name)
        for name in self._iter_builtin_plugin_names_from_pkgutil(plugins_pkg):
            add_name(name)

        return names

    def _iter_builtin_plugin_names_from_index(self) -> Iterable[str]:
        """从显式索引读取插件包名，避免打包后无法枚举包资源"""
        return self._get_builtin_plugin_index().keys()

    def _has_manifest(self, plugin_dir: Path) -> bool:
        """检查插件目录是否包含任一 manifest 文件"""
        for filename in MANIFEST_FILENAMES:
            if (plugin_dir / filename).exists():
                return True
        return False

    def _iter_builtin_plugin_names_from_resources(self) -> Iterable[str]:
        """从包资源目录读取插件包名"""
        try:
            plugins_root = importlib.resources.files("plugins")
            return [
                item.name
                for item in plugins_root.iterdir()
                if item.is_dir() and self._has_manifest(item)
            ]
        except Exception as e:
            self._core.logger.debug(f"Failed to list builtin plugins from resources: {e}")
            return []

    def _iter_builtin_plugin_names_from_paths(self, plugins_pkg) -> Iterable[str]:
        """从 plugins 包路径读取插件包名"""
        package_paths = getattr(plugins_pkg, "__path__", []) if plugins_pkg is not None else []
        names: List[str] = []
        for package_path in package_paths:
            try:
                package_dir = Path(package_path)
                if not package_dir.exists():
                    continue
                names.extend(
                    item.name
                    for item in package_dir.iterdir()
                    if item.is_dir() and self._has_manifest(item)
                )
            except Exception as e:
                self._core.logger.debug(f"Failed to list builtin plugins from path {package_path}: {e}")
        return names

    def _iter_builtin_plugin_names_from_pkgutil(self, plugins_pkg) -> Iterable[str]:
        """从 pkgutil 枚举插件包名"""
        package_paths = getattr(plugins_pkg, "__path__", []) if plugins_pkg is not None else []
        try:
            return [name for finder, name, ispkg in pkgutil.iter_modules(package_paths) if ispkg]
        except Exception as e:
            self._core.logger.debug(f"Failed to list builtin plugins with pkgutil: {e}")
            return []

    def _read_plugin_python_manifest(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """从 __init__.py AST 中读取兼容元信息"""
        init_file = plugin_dir / "__init__.py"
        if not init_file.exists():
            return None

        try:
            tree = ast.parse(init_file.read_text(encoding="utf-8"))
        except Exception as e:
            self._core.logger.error(f"Failed to parse plugin manifest {plugin_dir}: {e}")
            return None

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not self._is_plugin_class_node(node):
                continue

            values = {}
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id in {"PLUGIN_ID", "PLUGIN_PRIORITY"}:
                        try:
                            values[target.id] = ast.literal_eval(stmt.value)
                        except Exception:
                            pass

            plugin_id = values.get("PLUGIN_ID")
            if not plugin_id:
                continue

            priority = normalize_priority(values.get("PLUGIN_PRIORITY", 999))
            return PluginManifest(
                plugin_id=str(plugin_id),
                priority=priority,
                source=str(init_file),
            )

        self._core.logger.warning(f"Plugin metadata not found in {plugin_dir}")
        return None

    def _is_plugin_class_node(self, node: ast.ClassDef) -> bool:
        """判断 AST 类节点是否继承 PluginInterface"""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "PluginInterface":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "PluginInterface":
                return True
        return False
    
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

    def _discover_by_module(self, module_name: str) -> Tuple[Optional[str], float]:
        """发现插件但不加载（共享实现，打包/开发两用）"""
        try:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    plugin_id = self._resolve_plugin_id(obj)
                    if not plugin_id:
                        continue
                    priority = normalize_priority(getattr(obj, "PLUGIN_PRIORITY", 999))
                    return plugin_id, priority
        except ImportError as e:
            self._core.logger.error(f"Failed to import plugin module {module_name}: {e}")
        except Exception as e:
            self._core.logger.error(f"Failed to discover plugin from {module_name}: {e}")
        return None, 999.0

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
            module_name = self._plugin_modules.get(plugin_id, f"plugins.{plugin_dir.name}")
            importlib.invalidate_caches()
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, PluginInterface) and 
                    obj is not PluginInterface and
                    obj.__module__ == module.__name__):
                    
                    try:
                        plugin = obj()

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
        加载所有插件（兼容入口，委托 scan + load 标准路径）
        
        Args:
            plugin_path: 插件目录路径
        """
        plugin_ids = self.scan_plugins(plugin_path)
        for plugin_id in plugin_ids:
            self.load_plugin(plugin_id)

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
        self._plugin_modules.clear()

    def scan_builtin_plugins(self) -> List[str]:
        """
        扫描内置插件（打包后使用）
        从已导入的 plugins 子模块中发现插件（按优先级排序）
        """
        plugin_info: List[Tuple[float, str]] = []

        try:
            import plugins as plugins_pkg
        except ImportError as e:
            self._core.logger.error(f"Failed to import plugins package: {e}")
            return []

        # 获取插件包路径作为缓存 base
        try:
            plugins_path = Path(plugins_pkg.__file__).parent
        except (AttributeError, TypeError):
            plugins_path = None

        # 尝试从缓存恢复
        if plugins_path and plugins_path.exists():
            cached = restore_scan_cache(scan_base=plugins_path)
            if cached:
                cached_ids, cached_dirs, cached_modules = cached
                self._plugin_dirs.update(cached_dirs)
                self._plugin_modules.update(cached_modules)
                self._core.logger.info(f"Loaded {len(cached_ids)} builtin plugins from cache")
                return cached_ids

        try:
            for name in self._iter_builtin_plugin_names(plugins_pkg):
                module_name = f"plugins.{name}"
                manifest = self._read_builtin_plugin_manifest(name)
                if not manifest:
                    manifest = self._read_builtin_plugin_manifest_from_index(name)
                if manifest:
                    if manifest.module_name:
                        module_name = manifest.module_name
                    plugin_id = manifest.plugin_id
                    priority = manifest.priority
                else:
                    plugin_id, priority = self._discover_by_module(module_name)

                if not plugin_id:
                    continue

                self._plugin_dirs[plugin_id] = Path(name)
                self._plugin_modules[plugin_id] = module_name
                plugin_info.append((priority, plugin_id))
                self._core.logger.info(f"Discovered builtin plugin: {plugin_id} (priority: {priority})")
        except Exception as e:
            self._core.logger.error(f"Failed to scan builtin plugins: {e}")

        plugin_info.sort(key=lambda x: x[0])
        plugin_ids = [plugin_id for _, plugin_id in plugin_info]

        # 保存缓存供下次启动使用
        if plugins_path and plugin_ids:
            save_scan_cache(plugin_ids, self._plugin_dirs, self._plugin_modules, plugins_path)

        return plugin_ids


