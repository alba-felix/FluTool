"""
应用启动插件
提供应用程序快捷启动功能，支持分类、拖拽、图标提取
"""
import os
import json
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
from enum import Enum

from PyQt5.QtCore import Qt, QSize, QFileInfo, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFileDialog, QFileIconProvider, QScrollArea,
    QTabWidget, QTabBar, QMenu, QAction, QLabel, QFrame
)
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QPainter, QColor, QBrush, QPen
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, CardWidget, StrongBodyLabel,
    TransparentToolButton, BodyLabel, IconWidget, CaptionLabel,
    MessageBox, MessageBoxBase, SubtitleLabel, setCustomStyleSheet,
    StyleSheetBase, Theme, qconfig, isDarkTheme, PrimaryPushButton,
    ScrollArea, SmoothScrollArea
)

from core.plugin_interface import PluginInterface
from storage.database import DatabaseManager


CARD_WIDTH = 120
CARD_HEIGHT = 35
ICON_SIZE = 24


class CustomTabBar(QTabBar):
    """自定义标签栏，为第一个标签添加特殊样式"""
    
    category_context_menu_requested = pyqtSignal(int, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_index = -1
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        tab_index = self.tabAt(pos)
        if tab_index > 0:
            category_id = self.tabData(tab_index)
            if category_id is not None:
                self.category_context_menu_requested.emit(category_id, self.mapToGlobal(pos))
    
    def enterEvent(self, event):
        super().enterEvent(event)
        self._update_hovered_index()
    
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hovered_index = -1
        self.update()
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self._update_hovered_index()
    
    def _update_hovered_index(self):
        """更新悬停索引"""
        for i in range(self.count()):
            if self.tabRect(i).contains(self.mapFromGlobal(self.cursor().pos())):
                if self._hovered_index != i:
                    self._hovered_index = i
                    self.update()
                return
        if self._hovered_index != -1:
            self._hovered_index = -1
            self.update()
    
    def paintEvent(self, event):
        """自定义绘制"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for i in range(self.count()):
            rect = self.tabRect(i)
            is_selected = i == self.currentIndex()
            is_hovered = i == self._hovered_index
            is_first = i == 0
            
            if is_first:
                self._draw_first_tab(painter, rect, is_selected, is_hovered)
            else:
                self._draw_normal_tab(painter, rect, is_selected, is_hovered)
    
    def _draw_first_tab(self, painter, rect, is_selected, is_hovered):
        """绘制第一个标签（全部）"""
        if isDarkTheme():
            if is_selected:
                bg_color = QColor("#009faa")
                text_color = QColor("#ffffff")
            elif is_hovered:
                bg_color = QColor("#234e50")
                text_color = QColor("#4dd0e1")
            else:
                bg_color = QColor("#1a3a3c")
                text_color = QColor("#4dd0e1")
        else:
            if is_selected:
                bg_color = QColor("#009faa")
                text_color = QColor("#ffffff")
            elif is_hovered:
                bg_color = QColor("#d4eaec")
                text_color = QColor("#00787f")
            else:
                bg_color = QColor("#e8f4f5")
                text_color = QColor("#00787f")
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
        
        painter.setPen(QPen(text_color))
        font = self.font()
        font.setPointSize(11)
        font.setWeight(75)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.tabText(0))
    
    def _draw_normal_tab(self, painter, rect, is_selected, is_hovered):
        """绘制普通标签"""
        if isDarkTheme():
            text_color = QColor("#ffffff") if not is_selected else QColor("#009faa")
            hover_bg = QColor(255, 255, 255, 25)
        else:
            text_color = QColor("#333333") if not is_selected else QColor("#009faa")
            hover_bg = QColor(0, 0, 0, 12)
        
        if is_hovered and not is_selected:
            painter.setBrush(QBrush(hover_bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
        
        painter.setPen(QPen(text_color))
        font = self.font()
        font.setPointSize(10)
        font.setWeight(50)
        painter.setFont(font)
        
        tab_index = 0
        for i in range(self.currentIndex()):
            if i == 0:
                continue
            tab_index = i
        
        actual_index = rect.x() > self.tabRect(0).right() and 1 or 0
        for i in range(self.count()):
            if self.tabRect(i) == rect:
                actual_index = i
                break
        
        painter.drawText(rect, Qt.AlignCenter, self.tabText(actual_index))
        
        if is_selected:
            pen = QPen(QColor("#009faa"), 2)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            y = rect.bottom() - 1
            painter.drawLine(rect.left() + 10, y, rect.right() - 10, y)


# ==================== 样式定义 ====================
class AppStyleSheet(StyleSheetBase, Enum):
    """应用样式表枚举"""
    TAB_WIDGET = "tab_widget"
    CATEGORY_TAB = "category_tab"
    SCROLL_CONTENT = "scroll_content"
    
    def path(self, theme=Theme.AUTO):
        """根据主题返回样式文件路径"""
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return ""


# 直接定义样式字符串
LIGHT_STYLES = {
    "tab_bar": """
        QTabBar::tab {
            background: transparent;
            #padding: 8px 20px;
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


# ==================== 对话框组件 ====================
class InputDialog(MessageBoxBase):
    """Fluent 风格输入对话框"""
    
    def __init__(self, title: str, label: str, default_text: str = "", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self.input_edit = LineEdit(self)
        self.input_edit.setText(default_text)
        self.input_edit.setPlaceholderText(label)
        self.input_edit.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.input_edit)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(350)
        
        self.input_edit.setFocus()
    
    def get_text(self) -> str:
        return self.input_edit.text().strip()


# ==================== 卡片组件 ====================
class AppCard(CardWidget):
    """应用卡片组件"""
    
    app_clicked = pyqtSignal(dict)
    app_deleted = pyqtSignal(dict)
    
    def __init__(self, app_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self._is_hover = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setBorderRadius(8)
        
        # 设置 CardWidget 背景透明
        self.setStyleSheet("CardWidget { background: transparent; border: none; }")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 图标
        icon_label = self._load_icon()
        layout.addWidget(icon_label)
        
        # 名称
        name_label = BodyLabel(self.app_data.get('name', 'Unknown'), self)
        name_label.setWordWrap(False)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("background: transparent; color: inherit;")
        layout.addWidget(name_label, 1)
    
    def _load_icon(self) -> QLabel:
        """加载图标"""
        icon_label = QLabel()
        icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
        icon_label.setStyleSheet("background: transparent;")
        
        # 获取设备像素比，用于高 DPI 支持
        dpr = self.devicePixelRatioF()
        target_size = int(ICON_SIZE * dpr)
        
        icon_path = self.app_data.get('icon_path', '')
        if icon_path:
            base_dir = Path(__file__).parent.parent.parent
            abs_icon_path = base_dir / icon_path
            if abs_icon_path.exists():
                pixmap = QPixmap(str(abs_icon_path))
                if not pixmap.isNull():
                    pixmap.setDevicePixelRatio(dpr)
                    scaled_pixmap = pixmap.scaled(
                        target_size, target_size,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    scaled_pixmap.setDevicePixelRatio(dpr)
                    icon_label.setPixmap(scaled_pixmap)
                    return icon_label
        
        app_path = self.app_data.get('target_path', '')
        if app_path and os.path.exists(app_path):
            try:
                icon_provider = QFileIconProvider()
                file_info = QFileInfo(app_path)
                file_icon = icon_provider.icon(file_info)
                
                if not file_icon.isNull():
                    pixmap = file_icon.pixmap(target_size, target_size)
                    if not pixmap.isNull():
                        pixmap.setDevicePixelRatio(dpr)
                        icon_label.setPixmap(pixmap)
                        return icon_label
            except Exception:
                pass
        
        icon_label.setText("📦")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        return icon_label
    
    def enterEvent(self, event):
        """鼠标进入"""
        self._is_hover = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开"""
        self._is_hover = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, e):
        """自定义绘制"""
        super().paintEvent(e)
        
        if self._is_hover:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 根据主题选择悬停背景色
            if isDarkTheme():
                painter.setBrush(QBrush(QColor(255, 255, 255, 20)))
                painter.setPen(Qt.NoPen)
            else:
                painter.setBrush(QBrush(QColor(0, 0, 0, 10)))
                painter.setPen(Qt.NoPen)
            
            painter.drawRoundedRect(self.rect(), 8, 8)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.app_clicked.emit(self.app_data)
        elif event.button() == Qt.RightButton:
            self._show_context_menu()
        super().mousePressEvent(event)
    
    def _show_context_menu(self):
        """显示右键菜单"""
        menu = QMenu(self)
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.app_deleted.emit(self.app_data))
        menu.addAction(delete_action)
        menu.exec_(QCursor.pos())


class AddAppCard(CardWidget):
    """添加应用卡片"""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_hover = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setBorderRadius(8)
        
        # 设置背景透明
        self.setStyleSheet("CardWidget { background: transparent; border: none; }")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        icon_label = IconWidget(FIF.ADD, self)
        icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)
        
        text_label = CaptionLabel("添加应用", self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet("background: transparent; color: inherit;")
        layout.addWidget(text_label, 1)
        
        # 设置边框
        self._update_border()
    
    def _update_border(self):
        """更新边框样式"""
        if isDarkTheme():
            self.setStyleSheet("""
                CardWidget {
                    background: transparent;
                    border: 1px dashed #505050;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                CardWidget {
                    background: transparent;
                    border: 1px dashed #cccccc;
                    border-radius: 8px;
                }
            """)
    
    def enterEvent(self, event):
        """鼠标进入"""
        self._is_hover = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开"""
        self._is_hover = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, e):
        """自定义绘制"""
        super().paintEvent(e)
        
        if self._is_hover:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 根据主题选择悬停背景色
            if isDarkTheme():
                painter.setBrush(QBrush(QColor(0, 159, 170, 30)))
                painter.setPen(QPen(QColor(0, 159, 170), 1))
            else:
                painter.setBrush(QBrush(QColor(0, 159, 170, 20)))
                painter.setPen(QPen(QColor(0, 159, 170), 1))
            
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ==================== 分类标签页组件 ====================
class CategoryTab(QScrollArea):
    """分类标签页内容 - 使用 ScrollArea 作为容器"""
    
    app_clicked = pyqtSignal(dict)
    app_deleted = pyqtSignal(dict)
    add_app_clicked = pyqtSignal()
    
    def __init__(self, category_id: Optional[int], parent=None):
        super().__init__(parent)
        self.category_id = category_id
        self._setup_ui()
        self._apply_style()
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def _setup_ui(self):
        """设置界面"""
        # 设置滚动区域属性
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.NoFrame)
        
        # 创建内容容器 - 这是卡片组的背景板
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        self.content_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.content_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        # 内容容器的布局
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)
        
        # 卡片网格容器 - 这也是背景板的一部分
        self.grid_container = QWidget()
        self.grid_container.setObjectName("gridContainer")
        
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.grid_container)
        layout.addStretch()
        
        self.setWidget(self.content_widget)
    
    def _apply_style(self):
        """应用样式"""
        # 为整个标签页设置背景
        if isDarkTheme():
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #1a1a1a;
                    border-radius: 8px;
                }
                QWidget#gridContainer {
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #f5f5f5;
                    border: none;
                }
            """)
            self.content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f5f5f5;
                    border-radius: 8px;
                }
                QWidget#gridContainer {
                    background-color: transparent;
                }
            """)

            
    
    def showEvent(self, event):
        """确保每次显示时样式正确"""
        super().showEvent(event)
        self._apply_style()
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        add_action = QAction("添加应用", self)
        add_action.triggered.connect(self.add_app_clicked.emit)
        menu.addAction(add_action)
        menu.exec_(self.mapToGlobal(pos))
    
    def refresh_apps(self, apps: List[Dict[str, Any]]):
        """刷新应用列表"""
        # 清空现有卡片
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)
        
        # 添加应用卡片
        for idx, app_data in enumerate(apps):
            card = AppCard(app_data, self.grid_container)
            card.app_clicked.connect(self.app_clicked.emit)
            card.app_deleted.connect(self.app_deleted.emit)
            self.grid_layout.addWidget(card, idx // 6, idx % 6)
        
        # 添加"添加应用"卡片
        add_card = AddAppCard(self.grid_container)
        add_card.clicked.connect(self.add_app_clicked.emit)
        add_idx = len(apps)
        self.grid_layout.addWidget(add_card, add_idx // 6, add_idx % 6)
    
    def resizeEvent(self, event):
        """调整大小时更新网格列数"""
        super().resizeEvent(event)
        self._update_grid_columns()
    
    def _update_grid_columns(self):
        """更新网格列数"""
        if not hasattr(self, 'grid_layout') or not self.grid_layout:
            return
        
        # 计算可用的宽度
        available_width = self.viewport().width() - 40  # 减去左右边距
        
        # 计算列数
        spacing = 10
        cols = max(1, int((available_width + spacing) / (CARD_WIDTH + spacing)))
        
        # 获取所有卡片
        widgets = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())
        
        # 重新布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
        
        for i, widget in enumerate(widgets):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(widget, row, col)


# ==================== 主组件 ====================
class AppLauncherWidget(QWidget):
    """应用启动组件"""
    
    PLUGIN_ID = "app_launcher"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self.category_tabs = {}  # 缓存标签页
        self._init_paths()
        self._init_scroll_buttons()
        self._setup_ui()
        self._apply_styles()
        
        # 监听主题变化
        qconfig.themeChanged.connect(self._on_theme_changed)
    
    def _init_scroll_buttons(self):
        """初始化滚动按钮"""
        self._up_btn = PushButton("", self)
        self._up_btn.setIcon(FIF.CARE_UP_SOLID)
        self._up_btn.setFixedSize(48, 24)
        self._up_btn.setCursor(Qt.PointingHandCursor)
        self._up_btn.hide()
        self._up_btn.clicked.connect(self._scroll_up)
        
        self._down_btn = PushButton("", self)
        self._down_btn.setIcon(FIF.CARE_DOWN_SOLID)
        self._down_btn.setFixedSize(48, 24)
        self._down_btn.setCursor(Qt.PointingHandCursor)
        self._down_btn.hide()
        self._down_btn.clicked.connect(self._scroll_down)
    
    def _scroll_up(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab and isinstance(current_tab, QScrollArea):
            bar = current_tab.verticalScrollBar()
            bar.setValue(bar.value() - 100)
    
    def _scroll_down(self):
        current_tab = self.tab_widget.currentWidget()
        if current_tab and isinstance(current_tab, QScrollArea):
            bar = current_tab.verticalScrollBar()
            bar.setValue(bar.value() + 100)
    
    def _check_scroll_buttons(self):
        """检查并更新滚动按钮显示"""
        current_tab = self.tab_widget.currentWidget()
        if not current_tab or not isinstance(current_tab, QScrollArea):
            self._up_btn.hide()
            self._down_btn.hide()
            return
        
        scroll_area = current_tab
        widget_height = scroll_area.widget().height() if scroll_area.widget() else 0
        viewport_height = scroll_area.viewport().height()
        
        if widget_height > viewport_height:
            bar = scroll_area.verticalScrollBar()
            self._up_btn.setVisible(bar.value() > 0)
            self._down_btn.setVisible(bar.value() < bar.maximum())
        else:
            self._up_btn.hide()
            self._down_btn.hide()
    
    def _on_tab_changed(self, index):
        """标签页切换时检查滚动按钮"""
        self._check_scroll_buttons()
    
    def _init_paths(self):
        """初始化路径"""
        base_dir = Path(__file__).parent.parent.parent
        self.icon_dir = base_dir / "data" / "app_icons"
        self.icon_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_ui(self):
        """构建界面"""
        self.setObjectName("appLauncherWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 搜索区域
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)
        search_layout.setContentsMargins(20, 20, 20, 10)
        
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索应用...")
        self.search_input.setClearButtonEnabled(True)
        
        # 搜索延迟
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._perform_search)
        self.search_input.textChanged.connect(lambda: self.search_timer.start(200))
        
        scan_btn = PushButton("扫描应用", self)
        scan_btn.setIcon(FIF.SEARCH)
        scan_btn.clicked.connect(self._scan_apps)
        
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(scan_btn)
        
        # 向上滚动按钮
        self._up_btn_container = QWidget()
        up_layout = QHBoxLayout(self._up_btn_container)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.addStretch()
        up_layout.addWidget(self._up_btn)
        
        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setDocumentMode(True)
        
        # 使用自定义 TabBar
        custom_tab_bar = CustomTabBar(self)
        custom_tab_bar.category_context_menu_requested.connect(self._show_category_menu)
        self.tab_widget.setTabBar(custom_tab_bar)
        
        # 向下滚动按钮
        self._down_btn_container = QWidget()
        down_layout = QHBoxLayout(self._down_btn_container)
        down_layout.setContentsMargins(0, 0, 0, 0)
        down_layout.addStretch()
        down_layout.addWidget(self._down_btn)
        
        # 添加到主布局
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self._up_btn_container)
        main_layout.addWidget(self.tab_widget, 1)
        main_layout.addWidget(self._down_btn_container)
        
        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _apply_styles(self):
        """应用样式"""
        # 为整个组件设置背景
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#appLauncherWidget {
                    background-color: #1a1a1a;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#appLauncherWidget {
                    background-color: #f5f5f5;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #f5f5f5;
                }
            """)
        
        # 确保 corner widget 可见
        corner_widget = self.tab_widget.cornerWidget()
        if corner_widget:
            corner_widget.setVisible(True)
            corner_widget.raise_()
        
        # 为已存在的标签页应用样式
        for tab in self.category_tabs.values():
            if isinstance(tab, CategoryTab):
                tab._apply_style()
        
        # 刷新自定义 TabBar
        if hasattr(self.tab_widget, 'tabBar'):
            self.tab_widget.tabBar().update()
    
    def _on_theme_changed(self):
        """主题变化时更新样式"""
        self._apply_styles()
        
        # 强制刷新所有标签页
        for tab in self.category_tabs.values():
            if isinstance(tab, CategoryTab):
                apps = self.db.get_apps(self.PLUGIN_ID, tab.category_id)
                tab.refresh_apps(apps)
    
    def load_data(self) -> None:
        """加载应用数据"""
        self._load_categories()
    
    def _load_categories(self):
        """加载分类"""
        self.tab_widget.clear()
        self.category_tabs.clear()
        
        categories = self.db.get_categories(self.PLUGIN_ID)
        
        # 创建"全部"标签页
        all_tab = CategoryTab(None, self)
        all_tab.app_clicked.connect(self._launch_app)
        all_tab.app_deleted.connect(self._delete_app)
        all_tab.add_app_clicked.connect(self._add_app)
        all_tab_index = self.tab_widget.addTab(all_tab, "全部")
        self.tab_widget.tabBar().setTabData(all_tab_index, None)
        self.category_tabs[None] = all_tab
        
        all_apps = self.db.get_apps(self.PLUGIN_ID)
        all_tab.refresh_apps(all_apps)
        
        # 创建分类标签页
        for category in categories:
            tab = CategoryTab(category['id'], self)
            tab.app_clicked.connect(self._launch_app)
            tab.app_deleted.connect(self._delete_app)
            tab.add_app_clicked.connect(lambda cat_id=category['id']: self._add_app(cat_id))
            tab_index = self.tab_widget.addTab(tab, category['name'])
            self.tab_widget.tabBar().setTabData(tab_index, category['id'])
            self.category_tabs[category['id']] = tab
            
            apps = self.db.get_apps(self.PLUGIN_ID, category['id'])
            tab.refresh_apps(apps)
        
        # 添加分类按钮
        add_btn = TransparentToolButton(FIF.ADD, self)
        add_btn.setFixedSize(32, 32)
        add_btn.clicked.connect(self._add_category)
        self.tab_widget.setCornerWidget(add_btn)
        
        # 应用样式
        self._apply_styles()
    
    def _add_category(self):
        """添加分类"""
        dialog = InputDialog("添加分类", "请输入分类名称", parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if name:
                # 检查分类是否已存在
                existing_categories = [self.tab_widget.tabText(i) for i in range(1, self.tab_widget.count())]
                if name not in existing_categories:
                    self.db.add_category(self.PLUGIN_ID, name)
                    self._load_categories()
                else:
                    InfoBar.warning(
                        title="警告",
                        content="该分类已存在！",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
    
    def _show_category_menu(self, category_id: int, pos):
        """显示分类右键菜单"""
        from PyQt5.QtGui import QCursor
        
        menu = QMenu(self)
        
        edit_action = QAction("编辑分类", self)
        edit_action.triggered.connect(lambda: self._edit_category(category_id))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除分类", self)
        delete_action.triggered.connect(lambda: self._delete_category(category_id))
        menu.addAction(delete_action)
        
        menu.exec_(QCursor.pos())
    
    def _edit_category(self, category_id: int):
        """编辑分类"""
        categories = self.db.get_categories(self.PLUGIN_ID)
        current_name = ""
        for cat in categories:
            if cat['id'] == category_id:
                current_name = cat['name']
                break
        
        dialog = InputDialog("编辑分类", "请输入新的分类名称", current_name, self)
        if dialog.exec():
            new_name = dialog.get_text()
            if new_name and new_name != current_name:
                existing_categories = [self.tab_widget.tabText(i) for i in range(1, self.tab_widget.count())]
                if new_name not in existing_categories:
                    self.db.update_category(self.PLUGIN_ID, category_id, new_name)
                    self._load_categories()
                    InfoBar.success(
                        title="修改成功",
                        content=f"分类已重命名为 {new_name}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    InfoBar.warning(
                        title="警告",
                        content="该分类名称已存在！",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
    
    def _delete_category(self, category_id: int):
        """删除分类"""
        categories = self.db.get_categories(self.PLUGIN_ID)
        category_name = ""
        for cat in categories:
            if cat['id'] == category_id:
                category_name = cat['name']
                break
        
        box = MessageBox("删除分类", f"确定要删除分类 '{category_name}' 吗？\n该分类下的应用将移至\"全部\"分类。", self)
        if box.exec():
            apps = self.db.get_apps(self.PLUGIN_ID, category_id)
            for app in apps:
                icon_path = app.get('icon_path', '')
                if icon_path:
                    base_dir = Path(__file__).parent.parent.parent
                    abs_icon_path = base_dir / icon_path
                    if abs_icon_path.exists():
                        try:
                            abs_icon_path.unlink()
                        except Exception:
                            pass
            
            self.db.delete_category(self.PLUGIN_ID, category_id)
            self._load_categories()
            
            InfoBar.success(
                title="删除成功",
                content=f"已删除分类 {category_name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _add_app(self, category_id: Optional[int] = None):
        """添加应用"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用", "",
            "可执行文件 (*.exe);;所有文件 (*.*)"
        )
        
        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]
            icon_path = self._extract_icon(file_path)
            
            self.db.add_app(
                plugin_id=self.PLUGIN_ID,
                name=name,
                target_path=file_path,
                category_id=category_id,
                icon_path=icon_path
            )
            
            self._load_categories()
            
            InfoBar.success(
                title="添加成功",
                content=f"已添加 {name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _extract_icon(self, file_path: str) -> str:
        """从文件中提取图标并保存"""
        try:
            if not self.icon_dir.exists():
                self.icon_dir.mkdir(parents=True, exist_ok=True)
            
            file_info = QFileInfo(file_path)
            icon_provider = QFileIconProvider()
            file_icon = icon_provider.icon(file_info)
            
            if file_icon.isNull():
                return ""
            
            import hashlib
            hash_val = hashlib.md5(file_path.encode('utf-8', errors='ignore')).hexdigest()[:8]
            icon_name = f"icon_{hash_val}.png"
            icon_save_path = self.icon_dir / icon_name
            
            # 提取高分辨率图标以支持高 DPI
            pixmap = file_icon.pixmap(128, 128)
            if not pixmap.isNull() and pixmap.save(str(icon_save_path), "PNG"):
                return f"data/app_icons/{icon_name}"
                
        except Exception as e:
            self.core.logger.error(f"图标提取失败: {e}")
        
        return ""
    
    def _launch_app(self, app_data: Dict[str, Any]):
        """启动应用"""
        try:
            target_path = app_data.get('target_path', '')
            
            if not target_path:
                InfoBar.warning(
                    title="启动失败",
                    content="应用路径为空",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            arguments = app_data.get('arguments', '') or ''
            
            if not os.path.exists(target_path):
                InfoBar.warning(
                    title="启动失败",
                    content="应用文件不存在",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return
            
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                os.startfile(target_path)
            
            InfoBar.success(
                title="启动成功",
                content=f"已启动 {app_data.get('name', 'Unknown')}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.core.logger.error(f"启动失败: {e}")
            InfoBar.error(
                title="启动失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _delete_app(self, app_data: Dict[str, Any]):
        """删除应用"""
        box = MessageBox("删除应用", f"确定要删除 '{app_data.get('name', 'Unknown')}' 吗？", self)
        if box.exec():
            app_id = app_data.get('id')
            if app_id is not None:
                # 删除图标文件
                icon_path = app_data.get('icon_path', '')
                if icon_path:
                    base_dir = Path(__file__).parent.parent.parent
                    abs_icon_path = base_dir / icon_path
                    if abs_icon_path.exists():
                        try:
                            abs_icon_path.unlink()
                        except Exception as e:
                            self.core.logger.warning(f"删除图标文件失败: {e}")
                
                self.db.delete_app(self.PLUGIN_ID, app_id)
                self._load_categories()
                
                InfoBar.success(
                    title="删除成功",
                    content=f"已删除 {app_data.get('name', 'Unknown')}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _perform_search(self):
        """执行搜索"""
        text = self.search_input.text().strip()
        
        if not text:
            # 显示所有应用
            for category_id, tab in self.category_tabs.items():
                apps = self.db.get_apps(self.PLUGIN_ID, category_id)
                tab.refresh_apps(apps)
        else:
            # 搜索应用
            apps = self.db.search_apps(self.PLUGIN_ID, text)
            
            # 更新"全部"标签页
            if None in self.category_tabs:
                self.category_tabs[None].refresh_apps(apps)
            
            # 切换到"全部"标签页
            self.tab_widget.setCurrentIndex(0)
    
    def _scan_apps(self):
        """扫描系统应用"""
        InfoBar.info(
            title="功能开发中",
            content="扫描功能正在开发中",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )


# ==================== 插件入口 ====================
class Plugin(PluginInterface):
    """应用启动插件"""
    
    PLUGIN_ID = "app_launcher"
    PLUGIN_NAME = "应用启动"
    PLUGIN_ICON = FIF.APPLICATION
    PLUGIN_PRIORITY = 6
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return AppLauncherWidget(self.core, parent)
    
    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        self._widget.load_data()