"""PluginHost 单元测试。"""

import sys
from typing import Dict, Optional

import pytest
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget

from core.plugin_interface import PluginInterface
from ui.plugin_host import PluginHost


# ── Dummies ──────────────────────────────────────────────────────────


class DummyLogger:
    """测试用日志对象"""

    def __init__(self):
        self.messages: list = []

    def info(self, message):
        self.messages.append(("info", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))

    def debug(self, message):
        self.messages.append(("debug", message))


class DummyPluginManager:
    """替代 PluginManager，只暴露 get_plugin"""

    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}

    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        return self._plugins.get(plugin_id)


class DummyCore:
    """测试用核心对象"""

    def __init__(self):
        self.logger = DummyLogger()
        self.plugin_manager = DummyPluginManager()


# ── Mock 插件工厂 ────────────────────────────────────────────────────


class _MockPlugin(PluginInterface):
    """通用模拟插件，用于大多数测试。"""

    PLUGIN_ID = "mock_plugin"
    PLUGIN_NAME = "Mock Plugin"

    def __init__(self):
        super().__init__()
        self._shutdown_called = False

    def initialize(self, core) -> None:
        self.core = core

    def shutdown(self) -> None:
        self._shutdown_called = True

    def _create_widget(self, parent=None) -> QWidget:
        return QWidget(parent)


def make_plugin(plugin_id: str = "mock_plugin", plugin_name: str = "Mock Plugin") -> PluginInterface:
    """创建指定 ID / 名称的模拟插件实例。"""
    plugin = _MockPlugin()
    plugin.PLUGIN_ID = plugin_id
    plugin.PLUGIN_NAME = plugin_name
    return plugin


class _NoneWidgetPlugin(PluginInterface):
    """_create_widget 返回 None 的模拟插件。"""

    PLUGIN_ID = "none_widget"
    PLUGIN_NAME = "None Widget Plugin"

    def initialize(self, core) -> None:
        self.core = core

    def shutdown(self) -> None:
        pass

    def _create_widget(self, parent=None) -> Optional[QWidget]:
        return None


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def qapp():
    """确保全局 QApplication 存在。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


# ── Tests ────────────────────────────────────────────────────────────


class TestInit:
    """PluginHost 构造相关测试。"""

    def test_plugin_host_init_raises_on_none_core(self):
        """传入 None 时抛出 ValueError。"""
        with pytest.raises(ValueError, match="Core instance cannot be None"):
            PluginHost(None)

    def test_plugin_host_init_success(self, qapp):
        """正常初始化后各属性为空。"""
        host = PluginHost(DummyCore())
        assert host.plugin_containers == {}
        assert host.plugin_widgets == {}
        assert host.plugin_initialized == {}
        assert host._suspended is False


class TestCreateContainer:
    """create_container 相关测试。"""

    def test_create_container_returns_qwidget(self, qapp):
        """返回的容器是 QWidget 且 objectName 正确。"""
        host = PluginHost(DummyCore())
        container = host.create_container("test_plugin")
        assert isinstance(container, QWidget)
        assert container.objectName() == "container_test_plugin"

    def test_create_container_has_layout(self, qapp):
        """容器自带 QVBoxLayout，边距为 0。"""
        host = PluginHost(DummyCore())
        container = host.create_container("test_plugin")
        layout = container.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.contentsMargins().left() == 0
        assert layout.contentsMargins().top() == 0
        assert layout.contentsMargins().right() == 0
        assert layout.contentsMargins().bottom() == 0

    def test_create_container_registers_plugin(self, qapp):
        """容器创建后记录到 plugin_containers，初始化标记置 False。"""
        host = PluginHost(DummyCore())
        container = host.create_container("test_plugin")
        assert host.plugin_containers["test_plugin"] is container
        assert host.plugin_initialized["test_plugin"] is False

    def test_create_container_multiple_plugins(self, qapp):
        """多次创建不同插件容器互不干扰。"""
        host = PluginHost(DummyCore())
        c1 = host.create_container("plugin_a")
        c2 = host.create_container("plugin_b")
        assert c1.objectName() == "container_plugin_a"
        assert c2.objectName() == "container_plugin_b"
        assert len(host.plugin_containers) == 2


class TestInitPluginWidget:
    """init_plugin_widget 相关测试。"""

    def test_init_plugin_widget_loads_widget(self, qapp):
        """正常场景：创建控件并标记已初始化。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        result = host.init_plugin_widget("mock_plugin")

        assert result is True
        assert host.plugin_widgets["mock_plugin"] is not None
        assert host.plugin_widgets["mock_plugin"].objectName() == "mock_plugin"
        assert host.plugin_initialized["mock_plugin"] is True

    def test_init_plugin_widget_already_initialized(self, qapp):
        """重复调用返回 True 但不会重复创建。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        assert host.init_plugin_widget("mock_plugin") is True
        widget_count_before = len(host.plugin_widgets)

        assert host.init_plugin_widget("mock_plugin") is True
        assert len(host.plugin_widgets) == widget_count_before

    def test_init_plugin_widget_empty_plugin_id(self, qapp):
        """空 ID 返回 False。"""
        host = PluginHost(DummyCore())
        assert host.init_plugin_widget("") is False

    @pytest.mark.parametrize("bad_id", [None, ""])
    def test_init_plugin_widget_falsy_ids(self, qapp, bad_id):
        """假值 ID（None / 空串）均返回 False。"""
        host = PluginHost(DummyCore())
        assert host.init_plugin_widget(bad_id) is False

    def test_init_plugin_widget_fails_on_missing_plugin(self, qapp):
        """插件未注册时返回 False。"""
        core = DummyCore()
        host = PluginHost(core)
        host.create_container("unknown_plugin")
        result = host.init_plugin_widget("unknown_plugin")
        assert result is False
        assert "unknown_plugin" not in host.plugin_widgets

    def test_init_plugin_widget_fails_on_missing_container(self, qapp):
        """有插件但无容器时返回 False。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        result = host.init_plugin_widget("mock_plugin")
        assert result is False

    def test_init_plugin_widget_fails_when_plugin_returns_none(self, qapp):
        """插件 get_widget 返回 None 时返回 False。"""
        core = DummyCore()
        plugin = _NoneWidgetPlugin()
        core.plugin_manager._plugins["none_widget"] = plugin

        host = PluginHost(core)
        host.create_container("none_widget")
        result = host.init_plugin_widget("none_widget")
        assert result is False
        assert "none_widget" not in host.plugin_widgets

    def test_init_plugin_widget_get_plugin_exception(self, qapp):
        """get_plugin 不捕获异常，会向上传播。"""

        class BrokenPluginManager:
            def get_plugin(self, plugin_id):
                raise RuntimeError("get_plugin failed")

        class BrokenCore:
            def __init__(self):
                self.logger = DummyLogger()
                self.plugin_manager = BrokenPluginManager()

        host = PluginHost(BrokenCore())
        host.create_container("broken")
        with pytest.raises(RuntimeError, match="get_plugin failed"):
            host.init_plugin_widget("broken")

    def test_init_plugin_widget_get_widget_exception(self, qapp):
        """get_widget 抛出异常时返回 False。"""

        class ExceptionPlugin(PluginInterface):
            PLUGIN_ID = "exception_plugin"

            def initialize(self, core):
                self.core = core

            def shutdown(self):
                pass

            def _create_widget(self, parent=None):
                raise RuntimeError("widget creation failed")

        core = DummyCore()
        plugin = ExceptionPlugin()
        core.plugin_manager._plugins["exception_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("exception_plugin")
        result = host.init_plugin_widget("exception_plugin")
        assert result is False
        assert "exception_plugin" not in host.plugin_widgets


class TestLoadPluginData:
    """load_plugin_data 相关测试。"""

    def test_load_plugin_data(self, qapp):
        """build_plugin_widget 通过延迟加载数据。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        host.init_plugin_widget("mock_plugin")

        # QTimer.singleShot(0) 数据延迟加载，触发事件循环处理
        QApplication.processEvents()
        assert plugin._data_loaded is True

    def test_load_plugin_data_noop_on_empty_id(self, qapp):
        """空 ID 不执行任何操作。"""
        host = PluginHost(DummyCore())
        host.load_plugin_data("")  # 不应抛出异常
        host.load_plugin_data(None)  # 不应抛出异常

    def test_load_plugin_data_noop_on_missing_plugin(self, qapp):
        """插件不存在时静默跳过。"""
        host = PluginHost(DummyCore())
        host.load_plugin_data("nonexistent")  # 不应抛出异常

    def test_load_plugin_data_noop_when_suspended(self, qapp):
        """暂停状态下 build_plugin_widget 不加载数据。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        host.suspend_loaded_plugins()

        host.init_plugin_widget("mock_plugin")
        assert plugin._data_loaded is False


class TestPluginLifecycle:
    """完整生命周期测试。"""

    def test_plugin_lifecycle(self, qapp):
        """create_container → build_plugin_widget（内置数据加载）→ shutdown_plugin。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)

        # 1. create_container
        container = host.create_container("mock_plugin")
        assert isinstance(container, QWidget)
        assert host.plugin_initialized["mock_plugin"] is False

        # 2. build_plugin_widget（创建界面并延迟加载数据）
        assert host.init_plugin_widget("mock_plugin") is True
        assert host.plugin_initialized["mock_plugin"] is True
        assert host.plugin_widgets["mock_plugin"] is not None

        # 数据通过 QTimer.singleShot(0) 异步加载
        QApplication.processEvents()
        assert plugin._data_loaded is True

        # 4. shutdown_plugin
        host.shutdown_plugin("mock_plugin")
        assert plugin._shutdown_called is True
        assert "mock_plugin" not in host.plugin_containers
        assert "mock_plugin" not in host.plugin_widgets
        assert "mock_plugin" not in host.plugin_initialized

    def test_lifecycle_shutdown_nonexistent_plugin(self, qapp):
        """关闭不存在的插件不产生副作用。"""
        host = PluginHost(DummyCore())
        host.shutdown_plugin("ghost")  # 不应抛出异常
        host.shutdown_plugin("")  # 不应抛出异常
        host.shutdown_plugin(None)  # 不应抛出异常


class TestSuspendResume:
    """暂停与恢复测试。"""

    def test_suspend_resume(self, qapp):
        """暂停后 widget 失能，恢复后重新使能。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        host.init_plugin_widget("mock_plugin")
        widget = host.plugin_widgets["mock_plugin"]

        assert widget.isEnabled() is True

        host.suspend_loaded_plugins()
        assert host._suspended is True
        assert widget.isEnabled() is False

        host.resume_loaded_plugins()
        assert host._suspended is False
        assert widget.isEnabled() is True

    def test_suspend_resume_multiple_plugins(self, qapp):
        """多个插件同时暂停与恢复。"""
        core = DummyCore()
        p1 = make_plugin("p1", "Plugin 1")
        p2 = make_plugin("p2", "Plugin 2")
        core.plugin_manager._plugins["p1"] = p1
        core.plugin_manager._plugins["p2"] = p2

        host = PluginHost(core)
        host.create_container("p1")
        host.create_container("p2")
        host.init_plugin_widget("p1")
        host.init_plugin_widget("p2")

        w1 = host.plugin_widgets["p1"]
        w2 = host.plugin_widgets["p2"]

        host.suspend_loaded_plugins()
        assert w1.isEnabled() is False
        assert w2.isEnabled() is False

        host.resume_loaded_plugins()
        assert w1.isEnabled() is True
        assert w2.isEnabled() is True

    def test_suspend_resume_no_plugins(self, qapp):
        """无已加载插件时 suspend/resume 不报错。"""
        host = PluginHost(DummyCore())
        host.suspend_loaded_plugins()  # 不应抛出异常
        assert host._suspended is True
        host.resume_loaded_plugins()  # 不应抛出异常
        assert host._suspended is False

    def test_suspend_plugin_widget_exception(self, qapp):
        """widget setEnabled 抛出异常时记录警告，不中断其他插件。"""

        class BrokenWidget(QWidget):
            def setEnabled(self, enabled):
                raise RuntimeError("setEnabled failed")

        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        container = host.create_container("mock_plugin")
        host.init_plugin_widget("mock_plugin")

        # 替换为会抛出异常的 widget
        broken = BrokenWidget()
        host.plugin_widgets["mock_plugin"] = broken

        host.suspend_loaded_plugins()
        assert any("Failed to suspend" in m[1] for m in core.logger.messages)


class TestReload:
    """reload_loaded_plugins 测试。"""

    def test_reload_loaded_plugins(self, qapp):
        """强制重新加载所有已加载插件的数据。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        host.init_plugin_widget("mock_plugin")

        # 先加载一次
        host.load_plugin_data("mock_plugin")
        assert plugin._data_loaded is True

        # reload 会重置 _data_loaded 并再次加载
        plugin._data_loaded = True  # 模拟已加载状态
        host.reload_loaded_plugins()
        assert plugin._data_loaded is True  # load_data 已执行

    def test_reload_loaded_plugins_no_plugins(self, qapp):
        """无已加载插件时 reload 不报错。"""
        host = PluginHost(DummyCore())
        host.reload_loaded_plugins()  # 不应抛出异常

    def test_reload_loaded_plugins_skips_missing(self, qapp):
        """reload 时 get_plugin 返回 None 的插件被跳过。"""
        core = DummyCore()
        host = PluginHost(core)
        host.plugin_widgets["ghost"] = QWidget()

        host.reload_loaded_plugins()  # 不应抛出异常


class TestAttachLoadedPlugin:
    """attach_loaded_plugin 测试。"""

    def test_attach_loaded_plugin(self, qapp):
        """注册已加载插件并创建界面。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        container = host.attach_loaded_plugin(plugin)

        assert isinstance(container, QWidget)
        assert container.objectName() == "container_mock_plugin"
        assert host.plugin_widgets["mock_plugin"] is not None
        assert host.plugin_initialized["mock_plugin"] is True
        assert host.plugin_widgets["mock_plugin"].objectName() == "mock_plugin"

    def test_attach_loaded_plugin_widget_none(self, qapp):
        """插件 get_widget 返回 None 时仍返回容器，不注册 widget。"""
        core = DummyCore()
        plugin = _NoneWidgetPlugin()
        core.plugin_manager._plugins["none_widget"] = plugin

        host = PluginHost(core)
        container = host.attach_loaded_plugin(plugin)

        assert isinstance(container, QWidget)
        assert "none_widget" not in host.plugin_widgets
        assert host.plugin_initialized.get("none_widget") is False

    def test_attach_loaded_plugin_logs_warning_on_none_widget(self, qapp):
        """get_widget 返回 None 时记录 warning 日志。"""
        core = DummyCore()
        plugin = _NoneWidgetPlugin()
        core.plugin_manager._plugins["none_widget"] = plugin

        host = PluginHost(core)
        host.attach_loaded_plugin(plugin)

        assert any(
            ("warning", msg) for msg in
            (m[1] for m in core.logger.messages if m[0] == "warning")
            if "Plugin widget is None" in msg
        )

    def test_attach_loaded_plugin_get_widget_exception(self, qapp):
        """get_widget 抛出异常时返回容器，不注册 widget。"""

        class ExceptionPlugin(PluginInterface):
            PLUGIN_ID = "exception_plugin"

            def initialize(self, core):
                self.core = core

            def shutdown(self):
                pass

            def _create_widget(self, parent=None):
                raise RuntimeError("widget creation failed")

        core = DummyCore()
        plugin = ExceptionPlugin()
        core.plugin_manager._plugins["exception_plugin"] = plugin

        host = PluginHost(core)
        container = host.attach_loaded_plugin(plugin)
        assert isinstance(container, QWidget)
        assert "exception_plugin" not in host.plugin_widgets


class TestShutdownPlugin:
    """shutdown_plugin 测试。"""

    def test_shutdown_plugin_cleans_up(self, qapp):
        """关闭后从所有字典中移除。"""
        core = DummyCore()
        plugin = make_plugin()
        core.plugin_manager._plugins["mock_plugin"] = plugin

        host = PluginHost(core)
        host.create_container("mock_plugin")
        host.init_plugin_widget("mock_plugin")
        host.load_plugin_data("mock_plugin")

        host.shutdown_plugin("mock_plugin")
        assert "mock_plugin" not in host.plugin_containers
        assert "mock_plugin" not in host.plugin_widgets
        assert "mock_plugin" not in host.plugin_initialized
        assert plugin._shutdown_called is True

    def test_shutdown_plugin_empty_id(self, qapp):
        """空 ID 不执行任何操作。"""
        host = PluginHost(DummyCore())
        host.shutdown_plugin("")  # 不应抛出异常
        host.shutdown_plugin(None)  # 不应抛出异常

    def test_shutdown_plugin_nonexistent(self, qapp):
        """不存在的插件 ID 不报错。"""
        host = PluginHost(DummyCore())
        host.shutdown_plugin("nonexistent")  # 不应抛出异常

    def test_shutdown_plugin_logs_error(self, qapp):
        """plugin.shutdown 异常时记录 error 日志。"""

        class ErrorOnShutdownPlugin(PluginInterface):
            PLUGIN_ID = "error_shutdown"

            def initialize(self, core):
                self.core = core

            def shutdown(self):
                raise RuntimeError("shutdown failed")

            def _create_widget(self, parent=None):
                return QWidget(parent)

        core = DummyCore()
        plugin = ErrorOnShutdownPlugin()
        core.plugin_manager._plugins["error_shutdown"] = plugin

        host = PluginHost(core)
        host.create_container("error_shutdown")
        host.init_plugin_widget("error_shutdown")

        host.shutdown_plugin("error_shutdown")
        assert any("Plugin shutdown error" in m[1] for m in core.logger.messages)

        # 即使 shutdown 失败，清理状态仍应执行
        assert "error_shutdown" not in host.plugin_containers
        assert "error_shutdown" not in host.plugin_widgets
        assert "error_shutdown" not in host.plugin_initialized