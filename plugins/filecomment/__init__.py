"""filecomment 插件 - 文件夹备注

全局快捷键唤出浮窗，对当前文件夹写备注。
入口：__init__.py 定义 Plugin；plugin.py 仅保留扫描元信息。
"""
import os
from typing import Optional

from PyQt5.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface
from .floating_window import FloatingWindow
from .hotkey_manager import HotkeyManager
from .service import CommentService


def _looks_like_path(text: str) -> bool:
    """通用路径特征判断：盘符+反斜杠，或 UNC 路径"""
    if not text:
        return False
    if len(text) >= 2 and text[1] == ":" and "\\" in text:
        return True
    if text.startswith("\\\\") and len(text) > 2:
        return True
    return False


def _parse_explorer_title(title: str) -> Optional[str]:
    """从资源管理器窗口标题解析文件夹路径（不依赖固定窗口名后缀）

    资源管理器标题因系统/语言/版本而异，常见形态：
    - "C:\\path"
    - "C:\\path - 文件资源管理器" / "C:\\path - 文件夹"
    - "文件夹名 - C:\\path"（新旧系统混合）
    统一做法：按 " - " 切段，找到盘符段后向右贪心并入，
    用真实目录存在性过滤"文件资源管理器"等非路径段，
    从而保留路径自身含 " - " 的情况（如 "H:\\backup\\2026 - 项目"）。
    """
    if not title:
        return None
    segments = [s.strip() for s in title.split(" - ") if s.strip()]
    start = next((i for i, s in enumerate(segments) if _looks_like_path(s)), None)
    if start is None:
        return None
    candidate = segments[start]
    for s in segments[start + 1:]:
        trial = f"{candidate} - {s}"
        if os.path.isdir(trial):
            candidate = trial
        else:
            break
    return candidate


class Plugin(PluginInterface):
    """文件夹备注插件 - 全局快捷键唤出浮窗，对当前文件夹写备注"""

    # 已禁用：插件不再加载（代码完整保留），如需恢复改回 "filecomment"
    PLUGIN_ID = ""
    PLUGIN_NAME = "文件夹备注"
    PLUGIN_ICON = FIF.FOLDER
    PLUGIN_PRIORITY = 13.1
    PLUGIN_HIDDEN = False

    def __init__(self):
        super().__init__()
        self._service: Optional[CommentService] = None
        self._hotkey_mgr: Optional[HotkeyManager] = None
        self._floating: Optional[FloatingWindow] = None

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info("Plugin 'filecomment' initialized")

        config = core.config
        data_path = config.filecomment_data_path.value or None
        self._service = CommentService(data_path)

        self._hotkey_mgr = HotkeyManager(hotkey=config.filecomment_hotkey.value)
        self._hotkey_mgr.hotkey_pressed.connect(self._on_hotkey)
        self._hotkey_mgr.start()

        # 恢复资源管理器右键菜单状态
        from core.utils import set_explorer_context_menu
        set_explorer_context_menu(config.filecomment_context_menu.value)

    def shutdown(self) -> None:
        if self._hotkey_mgr:
            self._hotkey_mgr.stop()
        self.core.logger.info("Plugin 'filecomment' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        from .settings_dialog import SettingsDialog
        panel = SettingsDialog(self.core, parent, embedded=True)
        panel.settings_changed.connect(self._apply_settings)
        return panel

    def _apply_settings(self) -> None:
        """设置变更后重建 service 并重启热键监听"""
        config = self.core.config
        self._service = CommentService(config.filecomment_data_path.value or None)
        if self._floating is not None:
            self._floating.set_service(self._service)
        if self._hotkey_mgr:
            self._hotkey_mgr.stop()
        self._hotkey_mgr = HotkeyManager(hotkey=config.filecomment_hotkey.value)
        self._hotkey_mgr.hotkey_pressed.connect(self._on_hotkey)
        self._hotkey_mgr.start()

    def _do_load_data(self) -> None:
        pass

    def _on_hotkey(self) -> None:
        """全局快捷键触发：获取当前 Explorer 路径，弹出浮窗"""
        path = self._get_explorer_path()
        if not path:
            self.core.logger.info("filecomment: 未检测到 Explorer 窗口")
            return
        self.open_comment(path)

    def open_comment(self, folder_path: str) -> None:
        """对指定文件夹弹出备注浮窗（快捷键 / 右键菜单 / 单实例转发共用入口）"""
        folder_path = folder_path.strip().strip('"')
        if not folder_path:
            return
        if self._floating is None:
            self._floating = FloatingWindow(self._service)
        self._floating.trigger(folder_path)

    @staticmethod
    def _get_explorer_path() -> Optional[str]:
        """获取当前 Explorer 窗口的路径"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None

            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return None

            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return _parse_explorer_title(buf.value)
        except Exception:
            return None