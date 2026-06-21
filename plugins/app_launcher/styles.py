"""应用启动插件样式定义"""
from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, qconfig


class AppStyleSheet(StyleSheetBase, Enum):
    """应用样式表枚举"""
    TAB_WIDGET = "tab_widget"
    CATEGORY_TAB = "category_tab"
    SCROLL_CONTENT = "scroll_content"

    def path(self, theme=Theme.AUTO):
        """根据主题返回样式文件路径"""
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return ""


LIGHT_STYLES = {
    "tab_bar": """
        QTabBar::tab {
            background: transparent;
            padding: 8px 20px;
            margin: 0;
            font-size: 14px;
            font-weight: 500;
            min-width: 80px;
            color: #333333;
        }
        QTabBar::tab:hover {
            background: rgba(0, 0, 0, 0.05);
            border-radius: 4px;
        }
        QTabBar::tab:selected {
            color: #009faa;
            border-bottom: 2px solid #009faa;
        }
        QTabBar::tab:first {
            background: #e8f4f5;
            color: #00787f;
            border-radius: 4px;
        }
        QTabBar::tab:first:hover {
            background: #d4eaec;
        }
        QTabBar::tab:first:selected {
            background: #009faa;
            color: #ffffff;
            border-bottom: none;
        }
    """,

    "category_tab": """
        QWidget {
            background-color: #f5f5f5;
            border-radius: 8px;
        }
    """,

    "scroll_content": """
        QWidget {
            background-color: #ffffff;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
    """
}

DARK_STYLES = {
    "tab_bar": """
        QTabBar::tab {
            background: transparent;
            padding: 8px 20px;
            margin: 0;
            font-size: 14px;
            font-weight: 500;
            min-width: 80px;
            color: #ffffff;
        }
        QTabBar::tab:hover {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        QTabBar::tab:selected {
            color: #009faa;
            border-bottom: 2px solid #009faa;
        }
        QTabBar::tab:first {
            background: #1a3a3c;
            color: #4dd0e1;
            border-radius: 4px;
        }
        QTabBar::tab:first:hover {
            background: #234e50;
        }
        QTabBar::tab:first:selected {
            background: #009faa;
            color: #ffffff;
            border-bottom: none;
        }
    """,

    "category_tab": """
        QWidget {
            background-color: #2d2d2d;
            border-radius: 8px;
        }
    """,

    "scroll_content": """
        QWidget {
            background-color: #1e1e1e;
            border-radius: 8px;
            border: 1px solid #3d3d3d;
        }
    """
}
