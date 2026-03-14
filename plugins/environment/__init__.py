"""
环境变量插件
提供系统环境变量查看和管理功能
"""
import os
import sys
import winreg
from typing import Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget
)
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, isDarkTheme, qconfig,
    TransparentToolButton, SubtitleLabel, ScrollArea
)
from core import PluginInterface
from ui import CustomFluentIcon


class EnvVarTableWidget(QWidget):
    """环境变量表格组件"""
    
    def __init__(self, env_vars: Dict[str, str], parent=None):
        super().__init__(parent)
        self.env_vars = env_vars
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 搜索框
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索环境变量...")
        self.search_input.textChanged.connect(self._filter_table)
        layout.addWidget(self.search_input)
        
        # 表格
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont("Consolas", 10))
        
        layout.addWidget(self.table)
        
        self._load_env_vars()
    
    def _load_env_vars(self):
        """加载环境变量"""
        self.table.setRowCount(len(self.env_vars))
        
        for row, (key, value) in enumerate(sorted(self.env_vars.items())):
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem(value)
            
            key_item.setFont(QFont("Consolas", 10))
            value_item.setFont(QFont("Consolas", 10))
            
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
        
        self._apply_style()
    
    def _apply_style(self):
        """应用表格样式"""
        if isDarkTheme():
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: #2d2d2d;
                    alternate-background-color: #3a3a3a;
                    gridline-color: #4d4d4d;
                    border: 1px solid #4d4d4d;
                    selection-background-color: #0078d4;
                    selection-color: white;
                    color: #ffffff;
                }
                QTableWidget::item {
                    padding: 4px;
                    border-right: 1px solid #4d4d4d;
                    border-bottom: 1px solid #4d4d4d;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #3d3d3d;
                    padding: 6px;
                    border: 1px solid #4d4d4d;
                    font-weight: bold;
                    color: #ffffff;
                }
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical {
                    background-color: #4d4d4d;
                    border-radius: 5px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5d5d5d;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
        else:
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: white;
                    alternate-background-color: #f9f9f9;
                    gridline-color: #e0e0e0;
                    border: 1px solid #e0e0e0;
                    selection-background-color: #0078d4;
                    selection-color: white;
                    color: #333333;
                }
                QTableWidget::item {
                    padding: 4px;
                    border-right: 1px solid #e0e0e0;
                    border-bottom: 1px solid #e0e0e0;
                    color: #333333;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    padding: 6px;
                    border: 1px solid #e0e0e0;
                    font-weight: bold;
                    color: #333333;
                }
                QScrollBar:vertical {
                    background-color: #f0f0f0;
                    width: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical {
                    background-color: #c0c0c0;
                    border-radius: 5px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #a0a0a0;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
    
    def _filter_table(self):
        """过滤表格内容"""
        filter_text = self.search_input.text().lower()
        
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            if key_item and value_item:
                is_visible = filter_text in key_item.text().lower() or filter_text in value_item.text().lower()
                self.table.setRowHidden(row, not is_visible)
    
    def refresh(self):
        """刷新环境变量"""
        self.env_vars = dict(os.environ)
        self._load_env_vars()
        self._filter_table()
    
    def set_env_vars(self, env_vars: Dict[str, str]):
        """设置环境变量"""
        self.env_vars = env_vars
        self._load_env_vars()


def get_user_env_vars() -> Dict[str, str]:
    """获取用户环境变量"""
    user_env = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ) as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    user_env[name] = value
                    i += 1
                except OSError:
                    break
    except Exception:
        pass
    return user_env


class EnvVarWidget(QWidget):
    """环境变量主组件"""
    
    PLUGIN_ID = "environment"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        
        self._setup_ui()
        self._apply_style()
        qconfig.themeChangedFinished.connect(self._apply_style)
    
    def _setup_ui(self):
        self.setObjectName("envVarWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签页
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # 刷新按钮（放在标签页右上角）
        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.clicked.connect(self._refresh_all)
        self.tab_widget.setCornerWidget(self.refresh_btn, Qt.TopRightCorner)
        
        # 系统环境变量标签页
        system_env_vars = dict(os.environ)
        self.system_tab = EnvVarTableWidget(system_env_vars, self)
        self.tab_widget.addTab(self.system_tab, "📜 系统环境变量")
        
        # 用户环境变量标签页
        user_env_vars = get_user_env_vars()
        self.user_tab = EnvVarTableWidget(user_env_vars, self)
        self.tab_widget.addTab(self.user_tab, "👤 用户环境变量")
        
        # Python Properties 标签页
        python_props = self._get_python_properties()
        self.python_tab = EnvVarTableWidget(python_props, self)
        self.tab_widget.addTab(self.python_tab, "🖖 Python Properties")
        
        main_layout.addWidget(self.tab_widget)
    
    def _get_python_properties(self) -> Dict[str, str]:
        """获取 Python 属性"""
        props = {
            "Python 版本": sys.version,
            "Python 路径": sys.executable,
            "Python 前缀": sys.prefix,
            "Python 基础前缀": sys.base_prefix,
            "平台": sys.platform,
            "字节顺序": sys.byteorder,
            "最大整数": str(sys.maxsize),
            "文件系统编码": sys.getfilesystemencoding(),
            "默认编码": sys.getdefaultencoding(),
            "标准输入编码": getattr(sys.stdin, 'encoding', 'unknown'),
            "标准输出编码": getattr(sys.stdout, 'encoding', 'unknown'),
            "标准错误编码": getattr(sys.stderr, 'encoding', 'unknown'),
            "递归限制": str(sys.getrecursionlimit()),
            "最大 Unicode": str(sys.maxunicode),
        }
        
        # 添加 Python 路径
        for i, path in enumerate(sys.path):
            props[f"Python 路径 [{i}]"] = path
        
        return props
    
    def _refresh_all(self):
        """刷新所有环境变量"""
        # 刷新系统环境变量
        self.system_tab.env_vars = dict(os.environ)
        self.system_tab._load_env_vars()
        self.system_tab._filter_table()
        
        # 刷新用户环境变量
        user_env_vars = get_user_env_vars()
        self.user_tab.set_env_vars(user_env_vars)
        
        # 刷新 Python 属性
        self.python_tab.set_env_vars(self._get_python_properties())
    
    def _apply_style(self):
        """应用样式"""
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#envVarWidget {
                    background-color: #1e1e1e;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:hover {
                    background-color: #3d3d3d;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    color: #009faa;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#envVarWidget {
                    background-color: #f5f5f5;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #f5f5f5;
                }
                QTabBar::tab {
                    background-color: #e0e0e0;
                    color: #333333;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:hover {
                    background-color: #d0d0d0;
                }
                QTabBar::tab:selected {
                    background-color: #f5f5f5;
                    color: #009faa;
                }
            """)
        
        # 更新表格样式
        self.system_tab._apply_style()
        self.user_tab._apply_style()
        self.python_tab._apply_style()


class Plugin(PluginInterface):
    """环境变量插件"""
    
    PLUGIN_ID = "environment"
    PLUGIN_NAME = "环境变量"
    PLUGIN_ICON = CustomFluentIcon.ENV
    PLUGIN_PRIORITY = 9
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        return EnvVarWidget(self.core, parent)
    
    def load_data(self) -> None:
        if self._widget:
            pass  # 环境变量不需要加载外部数据
