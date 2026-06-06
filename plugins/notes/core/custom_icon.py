"""自定义 Fluent 图标类"""
from pathlib import Path
from enum import Enum

from PyQt5.QtGui import QIcon
from qfluentwidgets.common.icon import FluentIconBase
from qfluentwidgets.common.config import isDarkTheme, Theme


class CustomFluentIcon(FluentIconBase, Enum):
    """自定义 Fluent 图标"""
    EXPAND = "expand"
    COLLAPSE = "collapse"
    SAVE = "save"
    EDIT = "edit"
    CODE = "code"
    IMAGE = "image"
    FAVORITE = "favorite"
    ARCHIVE = "archive"
    DELETE = "delete"
    EXPORT = "export"
    
    def path(self, theme=Theme.AUTO) -> str:
        base_dir = Path(__file__).parent.parent / "resources" / "icons"
        if theme == Theme.AUTO:
            theme = Theme.DARK if isDarkTheme() else Theme.LIGHT
        icon_name = f"{self.value}_{theme.value.lower()}.svg"
        icon_path = base_dir / icon_name
        if icon_path.exists():
            return str(icon_path)
        dark_path = base_dir / f"{self.value}_dark.svg"
        if dark_path.exists():
            return str(dark_path)
        light_path = base_dir / f"{self.value}_light.svg"
        if light_path.exists():
            return str(light_path)
        return ""
    
    def icon(self, theme=Theme.AUTO, color=None) -> QIcon:
        path = self.path(theme)
        if path:
            return QIcon(path)
        return QIcon()