"""笔记管理插件 - 独立窗口模式"""
# 窗口切换：笔记窗口失去焦点（如点击主窗口）时自动隐藏，由 NotesWindow.focusOutEvent 处理

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface, get_app_data_path
from .core.runtime import NotesRuntime, set_notes_runtime, get_notes_runtime


class NotesWindowManager:
    """管理笔记窗口的单例"""

    _window = None
    _main_window = None
    _runtime = None

    @classmethod
    def set_main_window(cls, window):
        cls._main_window = window

    @classmethod
    def get_main_window(cls):
        """获取主窗口引用"""
        return cls._main_window

    @classmethod
    def set_runtime(cls, runtime):
        """设置 notes 运行时上下文"""
        cls._runtime = runtime

    @classmethod
    def show_window(cls):
        """显示笔记窗口（已隐藏则快速恢复）"""
        if cls._window is None:
            from .widgets.note_window import NotesWindow
            cls._window = NotesWindow(runtime=cls._runtime or get_notes_runtime())
            cls._window.setWindowFlags(cls._window.windowFlags() | Qt.Window)

        if not cls._window.isVisible():
            cls._window.show()

        cls._window.raise_()
        cls._window.activateWindow()

        # 主窗口中心偏移：向左 50，向下 30
        mw = cls._main_window
        if mw:
            notes_geom = cls._window.geometry()
            mw_geom = mw.geometry()
            center_x = mw_geom.x() + mw_geom.width() // 2
            center_y = mw_geom.y() + mw_geom.height() // 2
            notes_x = center_x - notes_geom.width() // 2 + 50
            notes_y = center_y - notes_geom.height() // 2 + 25
            cls._window.move(notes_x, notes_y)

    @classmethod
    def close_window(cls):
        """销毁笔记窗口并清理资源（仅插件退出时调用）"""
        if cls._window is not None:
            cls._window.allow_close()
            cls._window.close()
            cls._window.deleteLater()
            cls._window = None

    @classmethod
    def is_window_visible(cls) -> bool:
        """笔记窗口是否正在显示"""
        return cls._window is not None and cls._window.isVisible()

    @classmethod
    def toggle_window(cls):
        """切换笔记窗口的显示/隐藏"""
        if cls.is_window_visible():
            if cls._window is not None:
                cls._window.hide()
        else:
            cls.show_window()


class Plugin(PluginInterface):
    """笔记管理插件"""

    PLUGIN_ID = "notes"
    PLUGIN_NAME = "笔记管理"
    PLUGIN_ICON = FIF.DOCUMENT
    PLUGIN_PRIORITY = 40
    PLUGIN_HIDDEN = True

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info("笔记管理插件 initialized")

        # 缓存主窗口引用
        if hasattr(core, 'main_window') and core.main_window:
            NotesWindowManager.set_main_window(core.main_window)

        # 确保笔记数据目录存在
        get_app_data_path("data/notes").mkdir(parents=True, exist_ok=True)
        get_app_data_path("data/notes/images").mkdir(parents=True, exist_ok=True)
        get_app_data_path("data/notes/config").mkdir(parents=True, exist_ok=True)

        runtime = NotesRuntime.create_default()
        set_notes_runtime(runtime)
        NotesWindowManager.set_runtime(runtime)

    def shutdown(self) -> None:
        NotesWindowManager.close_window()
        self.core.logger.info("笔记管理插件 shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """独立窗口模式，不返回 widget"""
        return None

    def _do_load_data(self) -> None:
        pass

    def show_window(self) -> None:
        """显示笔记独立窗口"""
        NotesWindowManager.show_window()

    def toggle_window(self) -> None:
        """切换笔记窗口显示/隐藏"""
        NotesWindowManager.toggle_window()

    def is_window_visible(self) -> bool:
        """笔记窗口是否可见"""
        return NotesWindowManager.is_window_visible()
