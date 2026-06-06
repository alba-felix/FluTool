from typing import Optional, Callable, List

from PyQt5.QtWidgets import QApplication
from qfluentwidgets import qconfig, Theme, setTheme, isDarkTheme


TOOLTIP_STYLE_DARK = """
QToolTip {
    background-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    padding: 4px 8px;
}
"""

TOOLTIP_STYLE_LIGHT = """
QToolTip {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 4px 8px;
}
"""


class ThemeManager:
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
        self._update_tooltip_style()
        for callback in self._on_theme_changed_callbacks:
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

    def _update_tooltip_style(self):
        app = QApplication.instance()
        if app:
            style = TOOLTIP_STYLE_DARK if isDarkTheme() else TOOLTIP_STYLE_LIGHT
            app.setStyleSheet(style)

    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance