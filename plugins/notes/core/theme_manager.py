from typing import Optional, Callable, List

from qfluentwidgets import qconfig, Theme, setTheme


class ThemeManager:
    """主题桥接器，统一跟随主程序的全局主题状态。"""

    _instance: Optional['ThemeManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._on_theme_changed_callbacks: List[Callable] = []
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme: Theme):
        for callback in list(self._on_theme_changed_callbacks):
            callback(theme)

    def register_callback(self, callback: Callable):
        self._on_theme_changed_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        if callback in self._on_theme_changed_callbacks:
            self._on_theme_changed_callbacks.remove(callback)

    def is_dark(self) -> bool:
        return qconfig.theme == Theme.DARK

    def set_dark(self):
        setTheme(Theme.DARK)

    def set_light(self):
        setTheme(Theme.LIGHT)

    def toggle(self):
        if self.is_dark():
            self.set_light()
        else:
            self.set_dark()

    def get_current_theme(self) -> Theme:
        return qconfig.theme

    def notify_current_theme(self) -> None:
        """主动同步一次当前主题，便于新窗口初始化。"""
        self._on_theme_changed(self.get_current_theme())

    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
