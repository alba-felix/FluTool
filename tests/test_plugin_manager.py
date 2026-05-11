import sys
import types
from pathlib import Path

from PyQt5.QtWidgets import QWidget

from core.plugin_interface import PluginInterface
from core.plugin_manager import PluginManager


class DummyLogger:
    """测试用日志对象"""

    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))

    def debug(self, message):
        self.messages.append(("debug", message))


class DummyCore:
    """测试用核心对象"""

    def __init__(self):
        self.logger = DummyLogger()
        self.search_manager = None


def write_plugin(plugin_root: Path, name: str, init_content: str, manifest_content: str = None) -> Path:
    """写入测试插件目录"""
    plugin_dir = plugin_root / name
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text(init_content, encoding="utf-8")
    if manifest_content is not None:
        (plugin_dir / "plugin.json").write_text(manifest_content, encoding="utf-8")
    return plugin_dir


def test_scan_plugins_prefers_json_manifest(tmp_path):
    """扫描插件时优先使用 plugin.json 元信息"""
    write_plugin(
        tmp_path,
        "manifest_plugin",
        """
from core import PluginInterface

class Plugin(PluginInterface):
    PLUGIN_ID = "python_id"
    PLUGIN_PRIORITY = 100
""",
        '{"id": "json_id", "priority": 1, "module": "plugins.manifest_plugin"}',
    )

    manager = PluginManager(DummyCore())
    plugins = manager.scan_plugins(str(tmp_path))

    assert plugins == ["json_id"]
    assert manager._plugin_modules["json_id"] == "plugins.manifest_plugin"
    assert "plugins.manifest_plugin" not in sys.modules


def test_scan_plugins_falls_back_to_python_manifest(tmp_path):
    """没有 plugin.json 时回退到 __init__.py AST 元信息"""
    write_plugin(
        tmp_path,
        "python_plugin",
        """
from core import PluginInterface

class Plugin(PluginInterface):
    PLUGIN_ID = "python_id"
    PLUGIN_PRIORITY = 2
""",
    )

    manager = PluginManager(DummyCore())
    plugins = manager.scan_plugins(str(tmp_path))

    assert plugins == ["python_id"]
    assert manager._plugin_modules["python_id"] == "plugins.python_plugin"
    assert "plugins.python_plugin" not in sys.modules


def test_scan_plugins_sorts_by_manifest_priority(tmp_path):
    """插件扫描结果按元信息优先级排序"""
    write_plugin(
        tmp_path,
        "slow_plugin",
        "from core import PluginInterface\nclass Plugin(PluginInterface):\n    PLUGIN_ID = 'slow'\n",
        '{"id": "slow", "priority": 20}',
    )
    write_plugin(
        tmp_path,
        "fast_plugin",
        "from core import PluginInterface\nclass Plugin(PluginInterface):\n    PLUGIN_ID = 'fast'\n",
        '{"id": "fast", "priority": 1}',
    )

    manager = PluginManager(DummyCore())
    plugins = manager.scan_plugins(str(tmp_path))

    assert plugins == ["fast", "slow"]


def test_builtin_plugins_have_json_manifests():
    """所有内置插件都提供 plugin.json，避免扫描阶段解析大模块"""
    plugin_root = Path("plugins")
    missing = [
        item.name
        for item in plugin_root.iterdir()
        if item.is_dir()
        and not item.name.startswith("_")
        and item.name != "__pycache__"
        and not (item / "plugin.json").exists()
    ]

    assert missing == []


def test_scan_builtin_plugins_uses_manifest_without_import(tmp_path):
    """打包扫描优先读取 plugin.json，不导入插件主体模块"""
    package_dir = tmp_path / "plugins"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    plugin_dir = package_dir / "packed_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("raise RuntimeError('should not import')", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        '{"id": "packed_plugin", "priority": 3, "module": "plugins.packed_plugin"}',
        encoding="utf-8",
    )

    original_plugins = sys.modules.pop("plugins", None)
    package_module = types.ModuleType("plugins")
    package_module.__path__ = [str(package_dir)]
    sys.modules["plugins"] = package_module

    try:
        manager = PluginManager(DummyCore())
        plugins = manager.scan_builtin_plugins()

        assert plugins == ["packed_plugin"]
        assert "plugins.packed_plugin" not in sys.modules
    finally:
        sys.modules.pop("plugins", None)
        if original_plugins is not None:
            sys.modules["plugins"] = original_plugins


def test_scan_builtin_plugins_reads_manifest_from_package_resources(tmp_path, monkeypatch):
    """内置插件扫描可通过包资源读取 plugin.json，避免依赖 finder.path"""
    package_dir = tmp_path / "plugins"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    plugin_dir = package_dir / "resource_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("raise RuntimeError('should not import')", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        '{"id": "resource_plugin", "priority": 4}',
        encoding="utf-8",
    )

    class FinderWithoutPath:
        pass

    original_plugins = sys.modules.pop("plugins", None)
    original_plugin_module = sys.modules.pop("plugins.resource_plugin", None)
    package_module = types.ModuleType("plugins")
    package_module.__path__ = [str(package_dir)]
    plugin_module = types.ModuleType("plugins.resource_plugin")
    plugin_module.__file__ = str(plugin_dir / "__init__.py")
    plugin_module.__path__ = [str(plugin_dir)]
    plugin_module.__spec__ = None
    sys.modules["plugins"] = package_module
    sys.modules["plugins.resource_plugin"] = plugin_module

    def fake_iter_modules(paths):
        return [(FinderWithoutPath(), "resource_plugin", True)]

    monkeypatch.setattr("core.plugin_manager.pkgutil.iter_modules", fake_iter_modules)

    try:
        manager = PluginManager(DummyCore())
        plugins = manager.scan_builtin_plugins()

        assert plugins == ["resource_plugin"]
        assert manager._plugin_modules["resource_plugin"] == "plugins.resource_plugin"
    finally:
        sys.modules.pop("plugins", None)
        sys.modules.pop("plugins.resource_plugin", None)
        if original_plugins is not None:
            sys.modules["plugins"] = original_plugins
        if original_plugin_module is not None:
            sys.modules["plugins.resource_plugin"] = original_plugin_module


def test_scan_builtin_plugins_uses_index_when_pkgutil_is_empty(tmp_path, monkeypatch):
    """打包后 pkgutil 无法枚举子包时，使用显式索引发现内置插件"""
    package_dir = tmp_path / "plugins"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    plugin_dir = package_dir / "indexed_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("raise RuntimeError('should not import')", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        '{"id": "indexed_plugin", "priority": 5}',
        encoding="utf-8",
    )

    original_plugins = sys.modules.pop("plugins", None)
    original_index = sys.modules.pop("plugins.plugin_index", None)
    package_module = types.ModuleType("plugins")
    package_module.__path__ = [str(package_dir)]
    index_module = types.ModuleType("plugins.plugin_index")
    index_module.BUILTIN_PLUGIN_MANIFESTS = [
        {
            "package": "indexed_plugin",
            "id": "indexed_plugin",
            "priority": 5,
            "module": "plugins.indexed_plugin",
        }
    ]
    index_module.BUILTIN_PLUGIN_PACKAGES = ["indexed_plugin"]
    sys.modules["plugins"] = package_module
    sys.modules["plugins.plugin_index"] = index_module

    monkeypatch.setattr("core.plugin_manager.pkgutil.iter_modules", lambda paths: [])

    try:
        manager = PluginManager(DummyCore())
        plugins = manager.scan_builtin_plugins()

        assert plugins == ["indexed_plugin"]
        assert "plugins.indexed_plugin" not in sys.modules
    finally:
        sys.modules.pop("plugins", None)
        sys.modules.pop("plugins.plugin_index", None)
        if original_plugins is not None:
            sys.modules["plugins"] = original_plugins
        if original_index is not None:
            sys.modules["plugins.plugin_index"] = original_index


def test_build_script_collects_plugin_package_data():
    """打包脚本收集插件模块，但不复制插件源码目录"""
    build_script = Path("build.bat").read_text(encoding="utf-8").lower()

    assert '--additional-hooks-dir "hooks"' in build_script
    assert "--collect-submodules plugins" in build_script
    assert '--add-data "plugins;plugins/"' not in build_script
    assert '--hidden-import "ui.common"' in build_script
    assert '--hidden-import "core.async_loader"' in build_script
    assert '--hidden-import "configparser"' in build_script
    assert '--hidden-import "markdown"' in build_script
    assert "exit /b %build_exit_code%" in build_script

    hook_script = Path("hooks/hook-plugins.py").read_text(encoding="utf-8").lower()
    assert 'collect_submodules("plugins")' in hook_script


def test_load_plugin_does_not_duplicate_plugin_initialize_log(tmp_path):
    """插件管理器不重复记录插件自己的初始化日志"""
    module_name = "test_plugin_manager_runtime_plugin"
    module = types.ModuleType(module_name)

    class RuntimePlugin(PluginInterface):
        PLUGIN_ID = "runtime_plugin"
        PLUGIN_NAME = "运行时插件"

        def initialize(self, core) -> None:
            self.core = core
            core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

        def shutdown(self) -> None:
            pass

        def _create_widget(self, parent=None) -> QWidget:
            return QWidget(parent)

    RuntimePlugin.__module__ = module_name
    module.RuntimePlugin = RuntimePlugin
    sys.modules[module_name] = module

    try:
        core = DummyCore()
        manager = PluginManager(core)
        manager._plugin_dirs["runtime_plugin"] = tmp_path
        manager._plugin_modules["runtime_plugin"] = module_name

        plugin = manager.load_plugin("runtime_plugin")

        assert plugin is not None
        assert core.logger.messages.count(("info", "Plugin '运行时插件' initialized")) == 1
    finally:
        sys.modules.pop(module_name, None)
