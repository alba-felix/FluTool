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
    
    def _resolve_icon_path(self, name: str) -> str:
        """按优先级搜索图标文件"""
        # 1. 标准路径（开发/打包均可用）
        base_dir = Path(__file__).parent.parent / "resources" / "icons"
        icon_path = base_dir / name
        if icon_path.exists():
            return str(icon_path)
        # 2. 兜底：通过 get_icon_path 搜索
        from .path_util import PathUtil
        fallback = Path(PathUtil.get_icon_path(name))
        if fallback.exists():
            return str(fallback)
        return ""

    def path(self, theme=Theme.AUTO) -> str:
        if theme == Theme.AUTO:
            theme = Theme.DARK if isDarkTheme() else Theme.LIGHT
        icon_name = f"{self.value}_{theme.value.lower()}.svg"
        result = self._resolve_icon_path(icon_name)
        if result:
            return result
        return self._resolve_icon_path(f"{self.value}_dark.svg")
    
    def icon(self, theme=Theme.AUTO, color=None) -> QIcon:
        path = self.path(theme)
        if path:
            return QIcon(path)
        return QIcon()