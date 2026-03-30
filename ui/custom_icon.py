"""
自定义 Fluent 图标类
支持从 ui/resources/ 目录加载自定义 SVG 图标
"""
from pathlib import Path
from enum import Enum

from PyQt5.QtGui import QIcon
from qfluentwidgets.common.icon import FluentIconBase
from qfluentwidgets.common.config import isDarkTheme, Theme


class CustomFluentIcon(FluentIconBase, Enum):
    """自定义 Fluent 图标
    
    图标文件命名规则:
    - 深色主题：{name}_dark.svg
    - 浅色主题：{name}_light.svg
    
    如果只有 dark 版本，则两个主题都使用 dark 版本
    """
    SYSTEM = "sys"
    PICTURE = "picture"
    ENV = "env"
    NOTEBOOK = "notebook"
    NOTEBOOK_LIST = "notebook_list"
    NOTEBOOK_FORMAT = "notebook_format"  # 有序列表图标
    ISLIST = "islist"
    TIME = "time"
    DIFFER = 'differ'
    REGEDIT = "regedit"
    DEVICE = "device"
    DISK = "disk"
    SERVICES = "services"
    TASK = "task"
    CONTROL_PANEL = "control_panel"
    SYSCONFIG = "sys_config"
    DESK = "desk"
    RECYCLE_BIN = "recycle_bin"
    CMD = "cmd"
    POWERSHELL = "powershell"
    WINVIEW = "winview"
    COMPUTER = "computer"
    NETFW = "netfw"
    GROUP_POLICY = "group_policy"
    BOOKMARK_TAG = "bookmark_tag"  # 书签插件橙色标签图标
    
    
    def path(self, theme=Theme.AUTO) -> str:
        """获取图标路径"""
        base_dir = Path(__file__).parent / "resources"
        
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
        """创建图标"""
        path = self.path(theme)
        if path:
            return QIcon(path)
        return QIcon()
