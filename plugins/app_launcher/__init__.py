"""
应用启动插件
提供应用程序快捷启动功能，支持分类、拖拽、图标提取
支持多种文件类型：exe、py、bat、cmd、ps1、vbs、文件夹等
"""
import os
import sys
import json
import html
import difflib
import subprocess
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from enum import Enum

from PyQt5.QtCore import Qt, QSize, QFileInfo, QTimer, pyqtSignal, QRect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QFileDialog, QFileIconProvider, QScrollArea,
    QTabWidget, QTabBar, QMenu, QAction, QLabel, QFrame, QSizePolicy
)
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QPainter, QColor, QBrush, QPen, QImage
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, CardWidget, StrongBodyLabel,
    TransparentToolButton, BodyLabel, IconWidget, CaptionLabel,
    MessageBox, setCustomStyleSheet, MessageBoxBase,
    StyleSheetBase, Theme, qconfig, isDarkTheme, PrimaryPushButton,
    ScrollArea, SmoothScrollArea, SubtitleLabel, ComboBox, TextEdit, CheckBox
)
from qfluentwidgets.common.icon import drawIcon

from core import PluginInterface, get_app_data_path, SearchResult
from storage import DatabaseManager
from ui.common import InputDialog
from ui.custom_icon import CustomFluentIcon as CFIF


CARD_WIDTH = 120
CARD_HEIGHT = 35
ICON_SIZE = 24
LIST_CARD_HEIGHT = 64
GRID_VIEW = "grid"
LIST_VIEW = "list"
DEFAULT_ICON_SIZE = 24
CATEGORY_PRESET_COLORS = [
    ("默认", ""),
    ("青色", "#009faa"),
    ("蓝色", "#0078d4"),
    ("绿色", "#16a34a"),
    ("橙色", "#ea580c"),
    ("红色", "#dc2626"),
    ("紫色", "#9333ea"),
]
CATEGORY_ICON_MAP = {
    "": None,
    "FOLDER": FIF.FOLDER,
    "APPLICATION": FIF.APPLICATION,
    "DOCUMENT": FIF.DOCUMENT,
    "CODE": FIF.CODE,
    "SETTING": FIF.SETTING,
    "HOME": FIF.HOME,
    "FAVORITE": CFIF.BOOKMARK_TAG,
    "TAG": FIF.TAG,
}


def get_non_transparent_rect(pixmap: QPixmap) -> QRect:
    """计算图像中非透明像素的最小包围矩形"""
    if pixmap.isNull():
        return QRect()

    image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
    width = image.width()
    height = image.height()
    if width <= 0 or height <= 0:
        return QRect()

    min_x, min_y = width, height
    max_x, max_y = -1, -1

    for y in range(height):
        for x in range(width):
            if image.pixelColor(x, y).alpha() == 0:
                continue
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return QRect()
    return QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def get_category_icon(icon_name: str):
    """根据名称获取分类图标"""
    return CATEGORY_ICON_MAP.get(icon_name or "", None)


def get_category_icon_options() -> List[Tuple[str, str]]:
    """获取分类图标选项"""
    return [
        ("默认", ""),
        ("文件夹", "FOLDER"),
        ("应用", "APPLICATION"),
        ("文档", "DOCUMENT"),
        ("代码", "CODE"),
        ("设置", "SETTING"),
        ("首页", "HOME"),
        ("收藏", "FAVORITE"),
        ("标签", "TAG"),
    ]


def normalize_search_text(text: str) -> str:
    """标准化搜索文本"""
    return ''.join(str(text or '').lower().split())


def to_pinyin_text(text: str) -> str:
    """将文本转换为拼音串，依赖缺失时自动降级"""
    normalized_text = normalize_search_text(text)
    if not normalized_text:
        return ""

    try:
        from pypinyin import lazy_pinyin
        return ''.join(lazy_pinyin(text)).lower()
    except Exception:
        return normalized_text


def highlight_text(text: str, keyword: str) -> str:
    """高亮文本中的匹配内容"""
    safe_text = html.escape(text or "")
    normalized_keyword = normalize_search_text(keyword)
    if not normalized_keyword:
        return safe_text

    source_text = text or ""
    lowered_source = source_text.lower()
    lowered_keyword = keyword.lower()
    start_index = lowered_source.find(lowered_keyword)
    if start_index < 0:
        return f"<span style='font-weight: 600; color: #009faa;'>{safe_text}</span>"

    end_index = start_index + len(keyword)
    before_text = html.escape(source_text[:start_index])
    middle_text = html.escape(source_text[start_index:end_index])
    after_text = html.escape(source_text[end_index:])
    return (
        f"{before_text}"
        f"<span style='background-color: rgba(0, 159, 170, 0.22); color: #009faa; font-weight: 700;'>{middle_text}</span>"
        f"{after_text}"
    )


def score_search_match(query: str, app_data: Dict[str, Any]) -> Tuple[float, str]:
    """计算应用搜索匹配分数"""
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return 0.0, "none"

    fields = [
        ("name", app_data.get("name", "")),
        ("target_path", app_data.get("target_path", "")),
        ("notes", app_data.get("notes", "")),
    ]
    best_score = 0.0
    best_mode = "none"

    for field_name, value in fields:
        normalized_value = normalize_search_text(value)
        if not normalized_value:
            continue

        if normalized_query in normalized_value:
            base_score = 120.0 if field_name == "name" else 100.0
            compact_penalty = len(normalized_value) * 0.01
            score_value = base_score - compact_penalty
            if score_value > best_score:
                best_score = score_value
                best_mode = "direct"

        pinyin_value = to_pinyin_text(value)
        if pinyin_value and normalized_query in pinyin_value:
            score_value = 92.0 if field_name == "name" else 80.0
            if score_value > best_score:
                best_score = score_value
                best_mode = "pinyin"

        similarity = difflib.SequenceMatcher(None, normalized_query, normalized_value).ratio()
        if similarity >= 0.45:
            score_value = similarity * (78.0 if field_name == "name" else 66.0)
            if score_value > best_score:
                best_score = score_value
                best_mode = "fuzzy"

    return best_score, best_mode


def get_python_executable() -> str:
    """
    获取项目 Python 解释器路径
    开发环境：使用 .venv 中的解释器
    打包环境：使用系统 Python 或打包的解释器
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
        python_exe = base_path / "python.exe"
        if python_exe.exists():
            return str(python_exe)
        python_exe = base_path / "Scripts" / "python.exe"
        if python_exe.exists():
            return str(python_exe)
        return "python"
    else:
        venv_python = Path(sys.prefix) / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable


def get_plugins_sourcecode_dir() -> Path:
    """
    获取 plugins_sourcecode 目录路径
    开发环境：项目根目录下的 plugins_sourcecode
    打包环境：_internal 目录下的 plugins_sourcecode
    """
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path.cwd()
    return base / "plugins_sourcecode"


def get_menu_style() -> str:
    """获取菜单样式"""
    if isDarkTheme():
        return """
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #ffffff;
                padding: 6px 30px 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3d3d3d;
            }
            QMenu::item:pressed {
                background-color: #009faa;
            }
        """
    else:
        return """
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #333333;
                padding: 6px 30px 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #f0f0f0;
            }
            QMenu::item:pressed {
                background-color: #009faa;
                color: #ffffff;
            }
        """


class CustomTabBar(QTabBar):
    """自定义标签栏，为第一个标签添加特殊样式"""
    
    category_context_menu_requested = pyqtSignal(int, object)
    
    DARK_FIRST_TAB_COLORS = {
        'selected_bg': '#009faa',
        'selected_text': '#ffffff',
        'hovered_bg': '#234e50',
        'hovered_text': '#4dd0e1',
        'normal_bg': '#1a3a3c',
        'normal_text': '#4dd0e1',
    }
    
    LIGHT_FIRST_TAB_COLORS = {
        'selected_bg': '#009faa',
        'selected_text': '#ffffff',
        'hovered_bg': '#d4eaec',
        'hovered_text': '#00787f',
        'normal_bg': '#e8f4f5',
        'normal_text': '#00787f',
    }
    
    DARK_NORMAL_TAB_COLORS = {
        'selected_text': '#009faa',
        'normal_text': '#ffffff',
        'hover_bg': (255, 255, 255, 25),
    }
    
    LIGHT_NORMAL_TAB_COLORS = {
        'selected_text': '#009faa',
        'normal_text': '#333333',
        'hover_bg': (0, 0, 0, 12),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_index = -1
        self._category_meta = {}
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_category_meta(self, tab_index: int, meta: Dict[str, Any]) -> None:
        """设置分类标签元数据"""
        self._category_meta[tab_index] = meta or {}
        self.update()

    def clear_category_meta(self) -> None:
        """清理分类标签元数据"""
        self._category_meta.clear()
        self.update()
    
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
        colors = self.DARK_FIRST_TAB_COLORS if isDarkTheme() else self.LIGHT_FIRST_TAB_COLORS
        
        if is_selected:
            bg_color = QColor(colors['selected_bg'])
            text_color = QColor(colors['selected_text'])
        elif is_hovered:
            bg_color = QColor(colors['hovered_bg'])
            text_color = QColor(colors['hovered_text'])
        else:
            bg_color = QColor(colors['normal_bg'])
            text_color = QColor(colors['normal_text'])
        
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
        colors = self.DARK_NORMAL_TAB_COLORS if isDarkTheme() else self.LIGHT_NORMAL_TAB_COLORS
        
        text_color = QColor(colors['selected_text']) if is_selected else QColor(colors['normal_text'])
        hover_bg = QColor(*colors['hover_bg'])
        
        if is_hovered and not is_selected:
            painter.setBrush(QBrush(hover_bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 4, 4)
        
        painter.setPen(QPen(text_color))
        font = self.font()
        font.setPointSize(10)
        font.setWeight(50)
        painter.setFont(font)
        
        tab_index = self._find_tab_index(rect)
        self._draw_tab_content(painter, rect, tab_index, text_color)
        
        if is_selected:
            accent_color = QColor(self._get_tab_color(tab_index) or "#009faa")
            pen = QPen(accent_color, 2)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            y = rect.bottom() - 1
            painter.drawLine(rect.left() + 10, y, rect.right() - 10, y)

    def _draw_tab_content(self, painter, rect: QRect, tab_index: int, text_color: QColor) -> None:
        """绘制标签文字、图标和颜色标记"""
        meta = self._category_meta.get(tab_index, {})
        tab_text = self.tabText(tab_index)
        text_rect = rect.adjusted(10, 0, -10, 0)
        current_left = text_rect.left()

        icon_name = meta.get("icon_name", "")
        icon = get_category_icon(icon_name)
        if icon is not None:
            icon_rect = QRect(current_left, rect.center().y() - 8, 16, 16)
            drawIcon(icon, painter, icon_rect)
            current_left = icon_rect.right() + 6

        color_value = meta.get("color", "")
        if color_value:
            dot_rect = QRect(current_left, rect.center().y() - 4, 8, 8)
            painter.setBrush(QBrush(QColor(color_value)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(dot_rect)
            current_left = dot_rect.right() + 6
            painter.setPen(QPen(text_color))

        text_rect.setLeft(current_left)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignHCenter, tab_text)

    def _get_tab_color(self, tab_index: int) -> str:
        """获取标签颜色"""
        meta = self._category_meta.get(tab_index, {})
        return meta.get("color", "")
    
    def _find_tab_index(self, rect) -> int:
        """根据 rect 查找标签索引"""
        for i in range(self.count()):
            if self.tabRect(i) == rect:
                return i
        return 0


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


# ==================== 编辑对话框 ====================
class AppEditDialog(MessageBoxBase):
    """应用编辑对话框"""
    
    def __init__(self, app_data: Dict[str, Any], categories: List[Dict], parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.categories = categories
        
        self.titleLabel = SubtitleLabel("编辑应用", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        # 应用名称
        self.name_label = BodyLabel("应用名称:", self)
        self.viewLayout.addWidget(self.name_label)
        self.name_edit = LineEdit(self)
        self.name_edit.setText(app_data.get('name', ''))
        self.name_edit.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.name_edit)
        
        # 目标路径
        self.path_label = BodyLabel("目标路径:", self)
        self.viewLayout.addWidget(self.path_label)
        path_layout = QHBoxLayout()
        self.path_edit = LineEdit(self)
        self.path_edit.setText(app_data.get('target_path', ''))
        self.path_edit.setClearButtonEnabled(True)
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = PushButton("浏览", self)
        self.browse_btn.setFixedWidth(60)
        self.browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.browse_btn)
        self.viewLayout.addLayout(path_layout)
        
        # 启动参数
        self.args_label = BodyLabel("启动参数:", self)
        self.viewLayout.addWidget(self.args_label)
        self.args_edit = LineEdit(self)
        self.args_edit.setText(app_data.get('arguments', ''))
        self.args_edit.setClearButtonEnabled(True)
        self.args_edit.setPlaceholderText("可选")
        self.viewLayout.addWidget(self.args_edit)

        # 备注信息
        self.notes_label = BodyLabel("备注:", self)
        self.viewLayout.addWidget(self.notes_label)
        self.notes_edit = TextEdit(self)
        self.notes_edit.setPlaceholderText("可选，可填写用途说明等")
        self.notes_edit.setFixedHeight(80)
        self.notes_edit.setPlainText(app_data.get('notes', ''))
        self.viewLayout.addWidget(self.notes_edit)
        
        # 所属分类
        self.category_label = BodyLabel("所属分类:", self)
        self.viewLayout.addWidget(self.category_label)
        self.category_combo = ComboBox(self)
        self.category_combo.addItem("全部")
        current_category_id = app_data.get('category_id')
        for idx, cat in enumerate(categories):
            self.category_combo.addItem(cat['name'])
            if cat['id'] == current_category_id:
                self.category_combo.setCurrentIndex(idx + 1)
        self.viewLayout.addWidget(self.category_combo)
        
        self.widget.setMinimumWidth(450)
        self.name_edit.setFocus()
    
    def _browse_path(self):
        """浏览文件路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用", self.path_edit.text(),
            "所有支持的文件 (*.exe *.py *.bat *.cmd *.ps1 *.vbs);;"
            "可执行文件 (*.exe);;"
            "Python 脚本 (*.py);;"
            "批处理文件 (*.bat *.cmd);;"
            "PowerShell 脚本 (*.ps1);;"
            "VBScript (*.vbs);;"
            "所有文件 (*.*)"
        )
        if file_path:
            self.path_edit.setText(file_path)
            if not self.name_edit.text():
                self.name_edit.setText(os.path.splitext(os.path.basename(file_path))[0])
    
    def get_data(self) -> Dict[str, Any]:
        """获取编辑后的数据"""
        category_idx = self.category_combo.currentIndex()
        category_id = None if category_idx == 0 else self.categories[category_idx - 1]['id']
        
        return {
            'name': self.name_edit.text().strip(),
            'target_path': self.path_edit.text().strip(),
            'arguments': self.args_edit.text().strip(),
            'category_id': category_id,
            'notes': self.notes_edit.toPlainText().strip(),
        }
    
    def validate(self) -> bool:
        """验证输入"""
        return bool(self.name_edit.text().strip() and self.path_edit.text().strip())


class BatchMoveDialog(MessageBoxBase):
    """批量移动分类对话框"""

    def __init__(self, categories: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("批量移动分类", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.category_label = BodyLabel("目标分类:", self)
        self.viewLayout.addWidget(self.category_label)
        self.category_combo = ComboBox(self)
        self.category_combo.addItem("全部")
        for category in categories:
            self.category_combo.addItem(category.get("name", "未命名分类"))
        self.viewLayout.addWidget(self.category_combo)
        self.widget.setMinimumWidth(360)

    def get_category_id(self, categories: List[Dict[str, Any]]) -> Optional[int]:
        """获取选中的分类 ID"""
        current_index = self.category_combo.currentIndex()
        if current_index <= 0:
            return None
        return categories[current_index - 1].get("id")


class BatchEditDialog(MessageBoxBase):
    """批量修改属性对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("批量修改属性", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.args_label = BodyLabel("统一启动参数:", self)
        self.viewLayout.addWidget(self.args_label)
        self.args_edit = LineEdit(self)
        self.args_edit.setPlaceholderText("留空表示不修改")
        self.viewLayout.addWidget(self.args_edit)

        self.notes_label = BodyLabel("统一备注:", self)
        self.viewLayout.addWidget(self.notes_label)
        self.notes_edit = TextEdit(self)
        self.notes_edit.setPlaceholderText("留空表示不修改")
        self.notes_edit.setFixedHeight(80)
        self.viewLayout.addWidget(self.notes_edit)

        self.favorite_label = BodyLabel("收藏状态:", self)
        self.viewLayout.addWidget(self.favorite_label)
        self.favorite_combo = ComboBox(self)
        self.favorite_combo.addItems(["不修改", "设为收藏", "取消收藏"])
        self.viewLayout.addWidget(self.favorite_combo)

        self.widget.setMinimumWidth(420)

    def get_updates(self) -> Dict[str, Any]:
        """获取批量更新字段"""
        updates = {}
        arguments = self.args_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()
        if arguments:
            updates["arguments"] = arguments
        if notes:
            updates["notes"] = notes

        favorite_index = self.favorite_combo.currentIndex()
        if favorite_index == 1:
            updates["is_favorite"] = 1
        elif favorite_index == 2:
            updates["is_favorite"] = 0
        return updates


class CategoryEditDialog(MessageBoxBase):
    """分类编辑对话框"""

    def __init__(self, title: str, category_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.category_data = category_data or {}

        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.name_label = BodyLabel("分类名称:", self)
        self.viewLayout.addWidget(self.name_label)
        self.name_edit = LineEdit(self)
        self.name_edit.setText(self.category_data.get("name", ""))
        self.name_edit.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.name_edit)

        self.icon_label = BodyLabel("分类图标:", self)
        self.viewLayout.addWidget(self.icon_label)
        self.icon_combo = ComboBox(self)
        icon_options = get_category_icon_options()
        for label, _ in icon_options:
            self.icon_combo.addItem(label)
        current_icon_name = self.category_data.get("icon_name", "")
        current_icon_index = next((index for index, (_, value) in enumerate(icon_options) if value == current_icon_name), 0)
        self.icon_combo.setCurrentIndex(current_icon_index)
        self.viewLayout.addWidget(self.icon_combo)

        self.color_label = BodyLabel("分类颜色:", self)
        self.viewLayout.addWidget(self.color_label)
        self.color_combo = ComboBox(self)
        for label, _ in CATEGORY_PRESET_COLORS:
            self.color_combo.addItem(label)
        current_color = self.category_data.get("color", "")
        current_color_index = next((index for index, (_, value) in enumerate(CATEGORY_PRESET_COLORS) if value == current_color), 0)
        self.color_combo.setCurrentIndex(current_color_index)
        self.viewLayout.addWidget(self.color_combo)

        self.widget.setMinimumWidth(420)
        self.name_edit.setFocus()

    def get_data(self) -> Dict[str, Any]:
        """获取分类数据"""
        icon_name = get_category_icon_options()[self.icon_combo.currentIndex()][1]
        color = CATEGORY_PRESET_COLORS[self.color_combo.currentIndex()][1]
        return {
            "name": self.name_edit.text().strip(),
            "icon_name": icon_name,
            "color": color,
        }


# ==================== 卡片组件 ====================
class AppCard(CardWidget):
    """应用卡片组件"""
    
    app_clicked = pyqtSignal(dict)
    app_deleted = pyqtSignal(dict)
    app_edited = pyqtSignal(dict)
    app_favorited = pyqtSignal(dict)
    selection_changed = pyqtSignal(int, bool)
    
    DARK_COLORS = {
        'text': '#ffffff',
        'hover_bg': (255, 255, 255, 20),
    }
    
    LIGHT_COLORS = {
        'text': '#333333',
        'hover_bg': (0, 0, 0, 10),
    }
    
    def __init__(
        self,
        app_data: Dict[str, Any],
        view_mode: str = GRID_VIEW,
        icon_size: int = DEFAULT_ICON_SIZE,
        batch_mode: bool = False,
        selected: bool = False,
        search_keyword: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.app_data = app_data
        self.view_mode = view_mode
        self.icon_size = icon_size
        self.batch_mode = batch_mode
        self.search_keyword = search_keyword
        self._is_hover = False
        self._is_selected = selected
        self._name_label = None
        self._subtitle_label = None
        self._select_checkbox = None
        self._icon_label = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setBorderRadius(8)
        self.setStyleSheet("CardWidget { background: transparent; border: none; }")
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(8, 6, 8, 6)
        self.main_layout.setSpacing(8)

        self._select_checkbox = CheckBox(self)
        self._select_checkbox.setChecked(self._is_selected)
        self._select_checkbox.toggled.connect(self._on_checkbox_toggled)
        self.main_layout.addWidget(self._select_checkbox)

        self._icon_label = self._load_icon()
        self.main_layout.addWidget(self._icon_label)

        text_container = QWidget(self)
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self._name_label = QLabel(self)
        self._name_label.setWordWrap(False)
        self._name_label.setTextFormat(Qt.RichText)
        self._name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        text_layout.addWidget(self._name_label)

        self._subtitle_label = QLabel(self)
        self._subtitle_label.setWordWrap(False)
        self._subtitle_label.setTextFormat(Qt.RichText)
        self._subtitle_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        text_layout.addWidget(self._subtitle_label)

        self.main_layout.addWidget(text_container, 1)
        self._apply_view_mode()
        self._update_display_text()
        self._update_text_color()
        self._update_checkbox_visibility()
    
    def _update_text_color(self):
        """更新文字颜色"""
        if self._name_label is None or self._subtitle_label is None:
            return
        colors = self.DARK_COLORS if isDarkTheme() else self.LIGHT_COLORS
        self._name_label.setStyleSheet(f"background: transparent; color: {colors['text']};")
        subtitle_color = "#a0a0a0" if isDarkTheme() else "#666666"
        self._subtitle_label.setStyleSheet(f"background: transparent; color: {subtitle_color};")

    def _apply_view_mode(self):
        """应用视图模式"""
        if self.view_mode == LIST_VIEW:
            self.setMinimumHeight(LIST_CARD_HEIGHT)
            self.setMaximumHeight(LIST_CARD_HEIGHT)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._subtitle_label.show()
        else:
            grid_width = max(CARD_WIDTH, 120 + max(0, self.icon_size - DEFAULT_ICON_SIZE) * 2)
            grid_height = max(CARD_HEIGHT, 35 + max(0, self.icon_size - DEFAULT_ICON_SIZE))
            self.setFixedSize(grid_width, grid_height)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self._subtitle_label.hide()

    def _update_checkbox_visibility(self):
        """更新多选框显示状态"""
        if self._select_checkbox is None:
            return
        self._select_checkbox.setVisible(self.batch_mode)

    def _update_display_text(self):
        """更新显示文本"""
        display_name = self.app_data.get("_display_name_html") or highlight_text(
            self.app_data.get("name", "Unknown"), self.search_keyword
        )
        subtitle_parts = [self.app_data.get("target_path", "")]
        notes = self.app_data.get("notes", "").strip()
        if notes:
            subtitle_parts.append(notes)
        subtitle_text = " | ".join(filter(None, subtitle_parts))
        display_subtitle = self.app_data.get("_display_subtitle_html") or highlight_text(subtitle_text, self.search_keyword)
        self._name_label.setText(display_name)
        self._subtitle_label.setText(display_subtitle)
    
    @staticmethod
    def _crop_to_content(pixmap: QPixmap) -> QPixmap:
        """裁剪掉透明区域，只保留有效内容"""
        content_rect = get_non_transparent_rect(pixmap)
        if content_rect.isNull():
            return pixmap

        if content_rect.size() == pixmap.size():
            return pixmap

        return pixmap.copy(content_rect)
    
    def _load_icon(self) -> QLabel:
        """加载图标"""
        icon_label = QLabel()
        icon_label.setFixedSize(self.icon_size, self.icon_size)
        icon_label.setStyleSheet("background: transparent;")
        
        dpr = self.devicePixelRatioF()
        target_size = int(self.icon_size * dpr)
        
        icon_path = self.app_data.get('icon_path', '')
        if icon_path:
            abs_icon_path = get_app_data_path(icon_path)
            if abs_icon_path.exists():
                pixmap = QPixmap(str(abs_icon_path))
                if not pixmap.isNull():
                    # 先裁剪掉多余空白，再缩放
                    cropped_pixmap = self._crop_to_content(pixmap)
                    scaled_pixmap = cropped_pixmap.scaled(
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

    def _on_checkbox_toggled(self, checked: bool):
        """处理多选状态变化"""
        self._is_selected = checked
        self.update()
        app_id = self.app_data.get("id")
        if app_id is not None:
            self.selection_changed.emit(app_id, checked)
    
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

        if self._is_hover or self._is_selected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            colors = self.DARK_COLORS if isDarkTheme() else self.LIGHT_COLORS
            hover_bg = QColor(0, 159, 170, 48) if self._is_selected else QColor(*colors['hover_bg'])
            
            painter.setBrush(QBrush(hover_bg))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 8, 8)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.batch_mode:
                self._select_checkbox.setChecked(not self._select_checkbox.isChecked())
            else:
                self.app_clicked.emit(self.app_data)
        elif event.button() == Qt.RightButton:
            self._show_context_menu()
        super().mousePressEvent(event)
    
    def _show_context_menu(self):
        """显示右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet(get_menu_style())
        
        # 收藏/取消收藏
        is_favorite = self.app_data.get('is_favorite', 0)
        favorite_text = "取消收藏" if is_favorite else "收藏"
        favorite_action = QAction(favorite_text, self)
        favorite_action.triggered.connect(self._toggle_favorite)
        menu.addAction(favorite_action)
        
        menu.addSeparator()
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self._edit_app)
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.app_deleted.emit(self.app_data))
        menu.addAction(delete_action)
        
        menu.exec_(QCursor.pos())
    
    def _toggle_favorite(self):
        """切换收藏状态"""
        self.app_favorited.emit(self.app_data)
    
    def _edit_app(self):
        """编辑应用"""
        self.app_edited.emit(self.app_data)

    def set_view_mode(self, view_mode: str):
        """增量切换视图模式"""
        self.view_mode = view_mode
        self._apply_view_mode()
        self._subtitle_label.setVisible(view_mode == LIST_VIEW)
        self._update_checkbox_visibility()

    def set_icon_size(self, icon_size: int):
        """增量切换图标大小"""
        self.icon_size = icon_size
        if self._icon_label:
            self._icon_label.setFixedSize(icon_size, icon_size)
        self._apply_view_mode()

    def set_batch_mode(self, batch_mode: bool, selected: bool = False):
        """增量切换批量模式"""
        self._batch_mode = batch_mode
        self._is_selected = selected
        if self._select_checkbox:
            self._select_checkbox.setChecked(selected)
        self._update_checkbox_visibility()
        self.update()


class AddAppCard(CardWidget):
    """添加应用卡片"""
    
    clicked = pyqtSignal()
    
    DARK_COLORS = {
        'text': '#808080',
        'border': '#505050',
        'hover_bg': (0, 159, 170, 30),
        'hover_border': (0, 159, 170),
    }
    
    LIGHT_COLORS = {
        'text': '#999999',
        'border': '#cccccc',
        'hover_bg': (0, 159, 170, 20),
        'hover_border': (0, 159, 170),
    }
    
    def __init__(self, view_mode: str = GRID_VIEW, icon_size: int = DEFAULT_ICON_SIZE, parent=None):
        super().__init__(parent)
        self.view_mode = view_mode
        self.icon_size = icon_size
        self._is_hover = False
        self._text_label = None
        self._setup_ui()
    
    def _setup_ui(self):
        self.setCursor(Qt.PointingHandCursor)
        self.setBorderRadius(8)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        self._icon_label = IconWidget(FIF.ADD, self)
        self._icon_label.setFixedSize(self.icon_size, self.icon_size)
        self._icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._icon_label)
        
        self._text_label = CaptionLabel("添加应用", self)
        self._text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._update_style()
        layout.addWidget(self._text_label, 1)
        self._apply_view_mode()

    def _apply_view_mode(self):
        """应用视图模式"""
        if self.view_mode == LIST_VIEW:
            self.setMinimumHeight(LIST_CARD_HEIGHT)
            self.setMaximumHeight(LIST_CARD_HEIGHT)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            grid_width = max(CARD_WIDTH, 120 + max(0, self.icon_size - DEFAULT_ICON_SIZE) * 2)
            grid_height = max(CARD_HEIGHT, 35 + max(0, self.icon_size - DEFAULT_ICON_SIZE))
            self.setFixedSize(grid_width, grid_height)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_view_mode(self, view_mode: str):
        """增量切换视图模式"""
        self.view_mode = view_mode
        self._apply_view_mode()

    def set_icon_size(self, icon_size: int):
        """增量切换图标大小"""
        self.icon_size = icon_size
        if self._icon_label:
            self._icon_label.setFixedSize(icon_size, icon_size)
        self._apply_view_mode()
    
    def _update_style(self):
        """更新样式"""
        colors = self.DARK_COLORS if isDarkTheme() else self.LIGHT_COLORS
        
        self.setStyleSheet(f"""
            CardWidget {{
                background: transparent;
                border: 1px dashed {colors['border']};
                border-radius: 8px;
            }}
        """)
        
        if self._text_label:
            self._text_label.setStyleSheet(f"background: transparent; color: {colors['text']};")
    
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
            
            colors = self.DARK_COLORS if isDarkTheme() else self.LIGHT_COLORS
            hover_bg = QColor(*colors['hover_bg'])
            hover_border = QColor(*colors['hover_border'])
            
            painter.setBrush(QBrush(hover_bg))
            painter.setPen(QPen(hover_border, 1))
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
    app_edited = pyqtSignal(dict)
    app_favorited = pyqtSignal(dict)
    add_app_clicked = pyqtSignal()
    app_selection_changed = pyqtSignal(int, bool)
    
    def __init__(self, category_id: Optional[int], parent=None):
        super().__init__(parent)
        self.category_id = category_id
        self._is_drag_over = False
        self._view_mode = GRID_VIEW
        self._icon_size = DEFAULT_ICON_SIZE
        self._batch_mode = False
        self._selected_ids: Set[int] = set()
        self._search_keyword = ""
        self._apps: List[Dict[str, Any]] = []
        self._rebuilding = False
        self._setup_ui()
        self._apply_style()
        
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # 启用拖拽
        self.setAcceptDrops(True)
    
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
        menu.setStyleSheet(get_menu_style())
        add_action = QAction("添加应用", self)
        add_action.triggered.connect(self.add_app_clicked.emit)
        menu.addAction(add_action)
        menu.exec_(self.mapToGlobal(pos))

    def set_display_options(
        self,
        view_mode: str,
        icon_size: int,
        batch_mode: bool,
        selected_ids: Set[int],
        search_keyword: str
    ) -> None:
        """设置显示参数"""
        self._view_mode = view_mode
        self._icon_size = icon_size
        self._batch_mode = batch_mode
        self._selected_ids = set(selected_ids)
        self._search_keyword = search_keyword
    
    def refresh_apps(self, apps: List[Dict[str, Any]]):
        """刷新应用列表（增量更新）"""
        self._apps = list(apps)
        self._rebuilding = True

        # 收集现有卡片
        existing_cards: Dict[int, AppCard] = {}
        add_card: Optional[AddAppCard] = None
        stale_widgets: List[QWidget] = []

        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, AppCard):
                    app_id = w.app_data.get("id")
                    if app_id is not None and app_id not in existing_cards:
                        existing_cards[app_id] = w
                    else:
                        stale_widgets.append(w)
                elif isinstance(w, AddAppCard):
                    add_card = w
                else:
                    stale_widgets.append(w)

        # 确定新列表中的 app_id 集合
        new_app_ids: Set[int] = set()
        for app_data in apps:
            app_id = app_data.get("id")
            if app_id is not None:
                new_app_ids.add(app_id)

        # 移除不再存在的卡片
        for app_id in list(existing_cards.keys()):
            if app_id not in new_app_ids:
                w = existing_cards.pop(app_id)
                self.grid_layout.removeWidget(w)
                w.setParent(None)

        for w in stale_widgets:
            self.grid_layout.removeWidget(w)
            w.setParent(None)

        # 清空布局，准备重新排列
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        # 增量更新或创建卡片
        for idx, app_data in enumerate(apps):
            app_id = app_data.get("id")
            card = existing_cards.get(app_id) if app_id is not None else None

            if card is not None:
                # 增量更新现有卡片
                card.app_data = app_data
                card.view_mode = self._view_mode
                card.icon_size = self._icon_size
                card.batch_mode = self._batch_mode
                card.search_keyword = self._search_keyword
                card._is_selected = app_id in self._selected_ids if app_id is not None else False

                if card._icon_label:
                    card._icon_label.setFixedSize(self._icon_size, self._icon_size)
                if card._select_checkbox:
                    card._select_checkbox.setChecked(card._is_selected)

                card._apply_view_mode()
                card._update_display_text()
                card._update_text_color()
                card._update_checkbox_visibility()
                card.update()
            else:
                # 创建新卡片
                card = AppCard(
                    app_data,
                    view_mode=self._view_mode,
                    icon_size=self._icon_size,
                    batch_mode=self._batch_mode,
                    selected=app_id in self._selected_ids if app_id is not None else False,
                    search_keyword=self._search_keyword,
                    parent=self.grid_container
                )
                card.app_clicked.connect(self.app_clicked.emit)
                card.app_deleted.connect(self.app_deleted.emit)
                card.app_edited.connect(self.app_edited.emit)
                card.app_favorited.connect(self.app_favorited.emit)
                card.selection_changed.connect(self.app_selection_changed.emit)

            self.grid_layout.addWidget(card, idx, 0)

        # 处理添加卡片
        if not self._batch_mode:
            if add_card is not None:
                add_card.set_view_mode(self._view_mode)
                add_card.set_icon_size(self._icon_size)
            else:
                add_card = AddAppCard(self._view_mode, self._icon_size, self.grid_container)
                add_card.clicked.connect(self.add_app_clicked.emit)
            self.grid_layout.addWidget(add_card, len(apps), 0)
        elif add_card is not None:
            self.grid_layout.removeWidget(add_card)
            add_card.setParent(None)

        self._rebuilding = False
        self._update_grid_columns()

    def resizeEvent(self, event):
        """调整大小时更新网格列数"""
        super().resizeEvent(event)
        self._update_grid_columns()

    def _update_grid_columns(self):
        """更新网格列数"""
        if self._rebuilding:
            return
        self._rebuilding = True

        if not hasattr(self, 'grid_layout') or not self.grid_layout:
            self._rebuilding = False
            return

        widgets = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widgets.append(item.widget())

        while self.grid_layout.count():
            self.grid_layout.takeAt(0)

        if self._view_mode == LIST_VIEW:
            cols = 1
        else:
            available_width = max(100, self.viewport().width() - 40)
            spacing = self.grid_layout.spacing()
            card_width = max(CARD_WIDTH, 120 + max(0, self._icon_size - DEFAULT_ICON_SIZE) * 2)
            cols = max(1, int((available_width + spacing) / (card_width + spacing)))

        for i, widget in enumerate(widgets):
            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(widget, row, col)

        self._rebuilding = False
    
    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_drag_over = True
            self.update()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self._is_drag_over = False
        self.update()
    
    def dropEvent(self, event):
        """拖拽放下事件"""
        self._is_drag_over = False
        self.update()

        urls = event.mimeData().urls()
        if not urls:
            return

        launcher_widget = self._find_launcher_widget()
        if launcher_widget is None:
            event.ignore()
            return

        target_category_id = self.category_id if isinstance(self.category_id, int) else None
        for url in urls:
            file_path = url.toLocalFile()
            if not os.path.exists(file_path):
                continue
            launcher_widget._add_app_with_path(file_path, target_category_id)

        event.acceptProposedAction()

    def _find_launcher_widget(self):
        """向上查找 AppLauncherWidget，避免被 QTabWidget 重设父对象后丢失引用"""
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "_add_app_with_path"):
                return parent
            parent = parent.parentWidget()
        return None
    
    def paintEvent(self, event):
        """绘制事件 - 添加拖拽视觉反馈"""
        super().paintEvent(event)
        
        if self._is_drag_over:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 绘制半透明覆盖层
            overlay_color = QColor(0, 159, 170, 30) if not isDarkTheme() else QColor(0, 159, 170, 50)
            painter.fillRect(self.rect(), overlay_color)
            
            # 绘制边框
            border_color = QColor(0, 159, 170, 150)
            pen = QPen(border_color, 3, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self.rect().adjusted(5, 5, -5, -5), 8, 8)


# ==================== 主组件 ====================
class AppLauncherWidget(QWidget):
    """应用启动组件"""
    
    PLUGIN_ID = "app_launcher"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self.category_tabs = {}  # 缓存标签页
        self.selected_app_ids: Set[int] = set()
        self.batch_mode = False
        self._current_sort_by = "sort_order"
        self._ignore_tab_move = False
        self._init_paths()
        self._load_view_preferences()
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
        self.icon_dir = get_app_data_path("data/app_icons")
        self.icon_dir.mkdir(parents=True, exist_ok=True)
        self.view_settings_path = get_app_data_path("data/app_launcher_view.json")

    def _load_view_preferences(self) -> None:
        """加载视图偏好"""
        self.view_mode = GRID_VIEW
        self.icon_size = DEFAULT_ICON_SIZE

        if not self.view_settings_path.exists():
            return

        try:
            data = json.loads(self.view_settings_path.read_text(encoding="utf-8"))
        except Exception:
            return

        self.view_mode = data.get("view_mode", GRID_VIEW)
        self.icon_size = int(data.get("icon_size", DEFAULT_ICON_SIZE) or DEFAULT_ICON_SIZE)

    def _save_view_preferences(self) -> None:
        """保存视图偏好"""
        try:
            self.view_settings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "view_mode": self.view_mode,
                "icon_size": self.icon_size,
            }
            self.view_settings_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            self.core.logger.warning(f"保存应用视图偏好失败: {e}")

    def _configure_tab_display(self, tab: CategoryTab) -> None:
        """向标签页同步显示参数"""
        tab.set_display_options(
            self.view_mode,
            self.icon_size,
            self.batch_mode,
            self.selected_app_ids,
            self.search_input.text().strip() if hasattr(self, "search_input") else "",
        )

    def _refresh_all_tabs(self) -> None:
        """刷新所有标签页内容"""
        for category_id, tab in self.category_tabs.items():
            if not isinstance(tab, CategoryTab):
                continue
            self._configure_tab_display(tab)
            tab.refresh_apps(self._get_display_apps(category_id))
        self._update_batch_controls()
        self._check_scroll_buttons()

    def _get_display_apps(self, category_id) -> List[Dict[str, Any]]:
        """获取指定标签页的显示数据"""
        if category_id == "recent":
            apps = self._get_recent_apps()
        elif category_id == "favorite":
            apps = self._get_favorite_apps()
        else:
            apps = self.db.get_apps(self.PLUGIN_ID, category_id if isinstance(category_id, int) else None)

        apps = self._sort_app_list(apps, self._current_sort_by)
        keyword = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        return self._search_apps_advanced(apps, keyword)

    def _sort_app_list(self, apps: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """排序应用列表"""
        app_items = list(apps)
        if sort_by == 'name':
            app_items.sort(key=lambda x: x.get('name', '').lower())
        elif sort_by == 'created_at':
            app_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort_by == 'updated_at':
            app_items.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        elif sort_by == 'launch_count':
            app_items.sort(key=lambda x: x.get('launch_count', 0), reverse=True)
        elif sort_by == 'last_launch_time':
            app_items.sort(key=lambda x: x.get('last_launch_time', ''), reverse=True)
        else:
            app_items.sort(key=lambda x: (x.get('sort_order', 0), x.get('id', 0)))
        return app_items

    def _search_apps_advanced(self, apps: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """执行增强搜索"""
        normalized_keyword = normalize_search_text(keyword)
        if not normalized_keyword:
            return list(apps)

        matched_apps = []
        for app in apps:
            score_value, match_mode = score_search_match(keyword, app)
            if score_value < 40:
                continue

            item = dict(app)
            item["_search_score"] = score_value
            item["_search_mode"] = match_mode
            item["_display_name_html"] = highlight_text(item.get("name", ""), keyword)
            subtitle_parts = [item.get("target_path", "")]
            notes = item.get("notes", "").strip()
            if notes:
                subtitle_parts.append(notes)
            item["_display_subtitle_html"] = highlight_text(" | ".join(filter(None, subtitle_parts)), keyword)
            matched_apps.append(item)

        matched_apps.sort(
            key=lambda item: (
                -item.get("_search_score", 0),
                -item.get("launch_count", 0),
                item.get("name", "").lower()
            )
        )
        return matched_apps

    def _get_selected_apps(self) -> List[Dict[str, Any]]:
        """获取已选中的应用"""
        if not self.selected_app_ids:
            return []

        apps = self.db.get_apps(self.PLUGIN_ID)
        return [app for app in apps if app.get("id") in self.selected_app_ids]

    def _on_card_selection_changed(self, app_id: int, selected: bool) -> None:
        """处理卡片选择变化"""
        if selected:
            self.selected_app_ids.add(app_id)
        else:
            self.selected_app_ids.discard(app_id)
        self._update_batch_controls()

    def _update_batch_controls(self) -> None:
        """更新批量操作按钮状态"""
        selected_count = len(self.selected_app_ids)
        if hasattr(self, "batch_btn"):
            self.batch_btn.setText(f"批量模式 ({selected_count})" if self.batch_mode else "批量模式")
        for attr_name in ("batch_delete_btn", "batch_move_btn", "batch_edit_btn", "batch_select_current_btn", "batch_clear_btn"):
            button = getattr(self, attr_name, None)
            if button is not None:
                button.setVisible(self.batch_mode)
        for attr_name in ("batch_delete_btn", "batch_move_btn", "batch_edit_btn", "batch_clear_btn"):
            button = getattr(self, attr_name, None)
            if button is not None:
                button.setEnabled(selected_count > 0)

    def _set_batch_mode(self, enabled: bool) -> None:
        """设置批量模式"""
        self.batch_mode = enabled
        if not enabled:
            self.selected_app_ids.clear()
        self._refresh_all_tabs()

    def _toggle_batch_mode(self) -> None:
        """切换批量模式"""
        self._set_batch_mode(not self.batch_mode)

    def _clear_selection(self) -> None:
        """清空当前选择"""
        self.selected_app_ids.clear()
        self._refresh_all_tabs()

    def _select_current_tab_apps(self) -> None:
        """全选当前页应用"""
        current_tab = self.tab_widget.currentWidget()
        if not isinstance(current_tab, CategoryTab):
            return

        current_ids = [app.get("id") for app in current_tab._apps if app.get("id") is not None]
        self.selected_app_ids.update(current_ids)
        self._refresh_all_tabs()
    
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
        
        # 排序按钮
        self.sort_btn = PushButton("排序", self)
        self.sort_btn.setIcon(FIF.ARROW_DOWN)
        self.sort_btn.setFixedWidth(80)
        self.sort_btn.clicked.connect(self._show_sort_menu)

        self.view_combo = ComboBox(self)
        self.view_combo.addItems(["网格视图", "列表视图"])
        self.view_combo.setCurrentIndex(0 if self.view_mode == GRID_VIEW else 1)
        self.view_combo.currentIndexChanged.connect(self._on_view_mode_changed)

        self.icon_size_combo = ComboBox(self)
        self.icon_size_combo.addItems(["小图标", "中图标", "大图标"])
        self.icon_size_combo.setCurrentIndex({20: 0, 24: 1, 32: 2}.get(self.icon_size, 1))
        self.icon_size_combo.currentIndexChanged.connect(self._on_icon_size_changed)

        self.batch_btn = PushButton("批量模式", self)
        self.batch_btn.setIcon(FIF.EDIT)
        self.batch_btn.clicked.connect(self._toggle_batch_mode)

        self.batch_select_current_btn = PushButton("全选当前页", self)
        self.batch_select_current_btn.clicked.connect(self._select_current_tab_apps)

        self.batch_clear_btn = PushButton("清空选择", self)
        self.batch_clear_btn.clicked.connect(self._clear_selection)

        self.batch_move_btn = PushButton("批量移动", self)
        self.batch_move_btn.clicked.connect(self._batch_move_selected)

        self.batch_edit_btn = PushButton("批量修改", self)
        self.batch_edit_btn.clicked.connect(self._batch_edit_selected)

        self.batch_delete_btn = PushButton("批量删除", self)
        self.batch_delete_btn.clicked.connect(self._batch_delete_selected)
        
        scan_btn = PushButton("扫描应用", self)
        scan_btn.setIcon(FIF.SEARCH)
        scan_btn.clicked.connect(self._scan_apps)
        
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.sort_btn)
        search_layout.addWidget(self.view_combo)
        search_layout.addWidget(self.icon_size_combo)
        search_layout.addWidget(self.batch_btn)
        search_layout.addWidget(self.batch_select_current_btn)
        search_layout.addWidget(self.batch_clear_btn)
        search_layout.addWidget(self.batch_move_btn)
        search_layout.addWidget(self.batch_edit_btn)
        search_layout.addWidget(self.batch_delete_btn)
        search_layout.addWidget(scan_btn)
        
        # 向上滚动按钮
        self._up_btn_container = QWidget()
        self._up_btn_container.setObjectName("scrollBtnContainer")
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
        custom_tab_bar.setMovable(True)
        custom_tab_bar.tabMoved.connect(self._on_category_tab_moved)
        self.tab_widget.setTabBar(custom_tab_bar)
        
        # 向下滚动按钮
        self._down_btn_container = QWidget()
        self._down_btn_container.setObjectName("scrollBtnContainer")
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
        self._update_batch_controls()
    
    def _apply_styles(self):
        """应用样式"""
        # 为整个组件设置背景
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#appLauncherWidget {
                    background-color: #1a1a1a;
                }
                QWidget#scrollBtnContainer {
                    background-color: transparent;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #1a1a1a;
                }
                QTabWidget::tab-bar {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#appLauncherWidget {
                    background-color: #f5f5f5;
                }
                QWidget#scrollBtnContainer {
                    background-color: transparent;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #f5f5f5;
                }
                QTabWidget::tab-bar {
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
        self._refresh_all_tabs()
    
    def load_data(self) -> None:
        """加载应用数据"""
        self._scan_plugins_sourcecode()
        self._load_categories()
    
    def _scan_plugins_sourcecode(self) -> None:
        """扫描 plugins_sourcecode 目录，自动添加 .py 文件到'源码工具'分类"""
        source_dir = get_plugins_sourcecode_dir()
        if not source_dir.exists():
            return
        
        # 获取或创建"源码工具"分类
        categories = self.db.get_categories(self.PLUGIN_ID)
        cat_id = None
        for cat in categories:
            if cat['name'] == "源码工具":
                cat_id = cat['id']
                break
        if cat_id is None:
            cat_id = self.db.add_category(self.PLUGIN_ID, "源码工具")
        
        # 获取已有应用的路径集合，避免重复添加
        existing_apps = self.db.get_apps(self.PLUGIN_ID, cat_id)
        existing_paths = {app.get('target_path', '') for app in existing_apps}
        
        # 扫描 .py 文件
        py_files = list(source_dir.glob("*.py"))
        added_count = 0
        for py_file in py_files:
            file_path = str(py_file)
            if file_path in existing_paths:
                continue
            
            name = py_file.stem.replace("_", " ").title()
            icon_path = self._extract_icon(file_path)
            
            self.db.add_app(
                plugin_id=self.PLUGIN_ID,
                name=name,
                target_path=file_path,
                category_id=cat_id,
                icon_path=icon_path
            )
            added_count += 1
        
        if added_count > 0:
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.info(f"已自动添加 {added_count} 个源码工具应用")
    
    def _load_categories(self):
        """加载分类"""
        current_tab_key = None
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            current_tab_key = self.tab_widget.tabBar().tabData(current_index)

        self.tab_widget.clear()
        self.category_tabs.clear()
        tab_bar = self.tab_widget.tabBar()
        if isinstance(tab_bar, CustomTabBar):
            tab_bar.clear_category_meta()

        categories = self.db.get_categories(self.PLUGIN_ID)
        
        # 创建"全部"标签页
        all_tab = CategoryTab(None, self)
        all_tab.app_clicked.connect(self._launch_app)
        all_tab.app_deleted.connect(self._delete_app)
        all_tab.app_edited.connect(self._edit_app)
        all_tab.app_favorited.connect(self._toggle_favorite)
        all_tab.add_app_clicked.connect(self._add_app)
        all_tab.app_selection_changed.connect(self._on_card_selection_changed)
        all_tab_index = self.tab_widget.addTab(all_tab, "全部")
        self.tab_widget.tabBar().setTabData(all_tab_index, None)
        self.category_tabs[None] = all_tab
        
        # 创建"最近使用"标签页
        recent_tab = CategoryTab('recent', self)
        recent_tab.app_clicked.connect(self._launch_app)
        recent_tab.app_deleted.connect(self._delete_app)
        recent_tab.app_edited.connect(self._edit_app)
        recent_tab.app_favorited.connect(self._toggle_favorite)
        recent_tab.add_app_clicked.connect(self._add_app)
        recent_tab.app_selection_changed.connect(self._on_card_selection_changed)
        recent_tab_index = self.tab_widget.addTab(recent_tab, "最近使用")
        self.tab_widget.tabBar().setTabData(recent_tab_index, 'recent')
        self.category_tabs['recent'] = recent_tab
        
        # 创建"收藏"标签页
        favorite_tab = CategoryTab('favorite', self)
        favorite_tab.app_clicked.connect(self._launch_app)
        favorite_tab.app_deleted.connect(self._delete_app)
        favorite_tab.app_edited.connect(self._edit_app)
        favorite_tab.app_favorited.connect(self._toggle_favorite)
        favorite_tab.add_app_clicked.connect(self._add_app)
        favorite_tab.app_selection_changed.connect(self._on_card_selection_changed)
        favorite_tab_index = self.tab_widget.addTab(favorite_tab, "收藏")
        self.tab_widget.tabBar().setTabData(favorite_tab_index, 'favorite')
        self.category_tabs['favorite'] = favorite_tab
        
        # 创建分类标签页
        for category in categories:
            tab = CategoryTab(category['id'], self)
            tab.app_clicked.connect(self._launch_app)
            tab.app_deleted.connect(self._delete_app)
            tab.app_edited.connect(self._edit_app)
            tab.app_favorited.connect(self._toggle_favorite)
            tab.add_app_clicked.connect(lambda cat_id=category['id']: self._add_app(cat_id))
            tab.app_selection_changed.connect(self._on_card_selection_changed)
            tab_index = self.tab_widget.addTab(tab, category['name'])
            self.tab_widget.tabBar().setTabData(tab_index, category['id'])
            if isinstance(tab_bar, CustomTabBar):
                tab_bar.set_category_meta(tab_index, category)
            self.category_tabs[category['id']] = tab
        
        # 添加分类按钮
        add_btn = TransparentToolButton(FIF.ADD, self)
        add_btn.setFixedSize(32, 32)
        add_btn.clicked.connect(self._add_category)
        self.tab_widget.setCornerWidget(add_btn)
        
        # 应用样式
        self._apply_styles()
        self._refresh_all_tabs()

        if current_tab_key in self.category_tabs:
            for index in range(self.tab_widget.count()):
                if self.tab_widget.tabBar().tabData(index) == current_tab_key:
                    self.tab_widget.setCurrentIndex(index)
                    break
    
    def _add_category(self):
        """添加分类"""
        dialog = CategoryEditDialog("添加分类", parent=self)
        if dialog.exec():
            data = dialog.get_data()
            name = data.get("name", "")
            if name:
                existing_categories = [cat.get("name") for cat in self.db.get_categories(self.PLUGIN_ID)]
                if name not in existing_categories:
                    category_id = self.db.add_category(self.PLUGIN_ID, name)
                    self.db.update_category(
                        self.PLUGIN_ID,
                        category_id,
                        icon_name=data.get("icon_name", ""),
                        color=data.get("color", "")
                    )
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
        menu = QMenu(self)
        menu.setStyleSheet(get_menu_style())
        
        edit_action = QAction("编辑分类", self)
        edit_action.triggered.connect(lambda: self._edit_category(category_id))
        menu.addAction(edit_action)

        move_left_action = QAction("左移分类", self)
        move_left_action.triggered.connect(lambda: self._move_category_tab(category_id, -1))
        menu.addAction(move_left_action)

        move_right_action = QAction("右移分类", self)
        move_right_action.triggered.connect(lambda: self._move_category_tab(category_id, 1))
        menu.addAction(move_right_action)
        
        delete_action = QAction("删除分类", self)
        delete_action.triggered.connect(lambda: self._delete_category(category_id))
        menu.addAction(delete_action)
        
        menu.exec_(pos)
    
    def _edit_category(self, category_id: int):
        """编辑分类"""
        categories = self.db.get_categories(self.PLUGIN_ID)
        current_category = self._find_category_by_id(category_id)
        if current_category is None:
            return

        dialog = CategoryEditDialog("编辑分类", current_category, self)
        if dialog.exec():
            data = dialog.get_data()
            new_name = data.get("name", "")
            if not new_name:
                return

            existing_categories = [
                cat.get("name") for cat in categories
                if cat.get("id") != category_id
            ]
            if new_name in existing_categories:
                InfoBar.warning(
                    title="警告",
                    content="该分类名称已存在！",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
                return

            self.db.update_category(
                self.PLUGIN_ID,
                category_id,
                name=new_name,
                icon_name=data.get("icon_name", ""),
                color=data.get("color", "")
            )
            self._load_categories()
            InfoBar.success(
                title="修改成功",
                content=f"分类已更新为 {new_name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _find_category_by_id(self, category_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 查找分类"""
        categories = self.db.get_categories(self.PLUGIN_ID)
        return next((category for category in categories if category.get("id") == category_id), None)

    def _on_category_tab_moved(self, from_index: int, to_index: int) -> None:
        """处理分类拖拽排序"""
        if self._ignore_tab_move:
            return

        if from_index < 3 or to_index < 3:
            self._ignore_tab_move = True
            self.tab_widget.tabBar().moveTab(to_index, from_index)
            self._ignore_tab_move = False
            return

        category_ids = []
        for index in range(3, self.tab_widget.count()):
            category_id = self.tab_widget.tabBar().tabData(index)
            if isinstance(category_id, int):
                category_ids.append(category_id)
        self.db.update_category_sort_orders(self.PLUGIN_ID, category_ids)
        self._load_categories()

    def _move_category_tab(self, category_id: int, step: int) -> None:
        """通过菜单移动分类顺序"""
        tab_bar = self.tab_widget.tabBar()
        current_index = next(
            (index for index in range(self.tab_widget.count()) if tab_bar.tabData(index) == category_id),
            -1
        )
        if current_index < 3:
            return

        target_index = current_index + step
        if target_index < 3 or target_index >= self.tab_widget.count():
            return

        self._ignore_tab_move = True
        tab_bar.moveTab(current_index, target_index)
        self._ignore_tab_move = False
        self._on_category_tab_moved(current_index, target_index)
    
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
                    abs_icon_path = get_app_data_path(icon_path)
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

    def _on_view_mode_changed(self, index: int) -> None:
        """切换视图模式"""
        self.view_mode = GRID_VIEW if index == 0 else LIST_VIEW
        self._save_view_preferences()
        self._refresh_all_tabs()

    def _on_icon_size_changed(self, index: int) -> None:
        """切换图标尺寸"""
        icon_size_map = {0: 20, 1: 24, 2: 32}
        self.icon_size = icon_size_map.get(index, DEFAULT_ICON_SIZE)
        self._save_view_preferences()
        self._refresh_all_tabs()

    def _batch_move_selected(self) -> None:
        """批量移动应用分类"""
        selected_apps = self._get_selected_apps()
        if not selected_apps:
            return

        categories = self.db.get_categories(self.PLUGIN_ID)
        dialog = BatchMoveDialog(categories, self)
        if not dialog.exec():
            return

        category_id = dialog.get_category_id(categories)
        updated_count = self.db.batch_update_apps(
            self.PLUGIN_ID,
            list(self.selected_app_ids),
            category_id=category_id
        )
        self._refresh_all_tabs()
        InfoBar.success(
            title="批量移动完成",
            content=f"已更新 {updated_count} 个应用的分类",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _batch_edit_selected(self) -> None:
        """批量修改应用属性"""
        if not self.selected_app_ids:
            return

        dialog = BatchEditDialog(self)
        if not dialog.exec():
            return

        updates = dialog.get_updates()
        if not updates:
            InfoBar.info(
                title="未修改",
                content="没有填写任何需要批量修改的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
            return

        updated_count = self.db.batch_update_apps(
            self.PLUGIN_ID,
            list(self.selected_app_ids),
            **updates
        )
        self._refresh_all_tabs()
        InfoBar.success(
            title="批量修改完成",
            content=f"已更新 {updated_count} 个应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _batch_delete_selected(self) -> None:
        """批量删除应用"""
        selected_apps = self._get_selected_apps()
        if not selected_apps:
            return

        box = MessageBox("批量删除", f"确定要删除选中的 {len(selected_apps)} 个应用吗？", self)
        if not box.exec():
            return

        for app in selected_apps:
            icon_path = app.get("icon_path", "")
            if not icon_path:
                continue
            abs_icon_path = get_app_data_path(icon_path)
            if not abs_icon_path.exists():
                continue
            try:
                abs_icon_path.unlink()
            except Exception as e:
                self.core.logger.warning(f"删除图标文件失败: {e}")

        deleted_count = self.db.batch_delete_apps(self.PLUGIN_ID, list(self.selected_app_ids))
        self.selected_app_ids.clear()
        self._refresh_all_tabs()
        InfoBar.success(
            title="批量删除完成",
            content=f"已删除 {deleted_count} 个应用",
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
            "所有支持的文件 (*.exe *.py *.bat *.cmd *.ps1 *.vbs);;"
            "可执行文件 (*.exe);;"
            "Python 脚本 (*.py);;"
            "批处理文件 (*.bat *.cmd);;"
            "PowerShell 脚本 (*.ps1);;"
            "VBScript (*.vbs);;"
            "所有文件 (*.*)"
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
    
    def _add_app_with_path(self, file_path: str, category_id: Optional[int] = None):
        """通过拖拽添加应用"""
        if not file_path or not os.path.exists(file_path):
            return
        
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
            
            # 获取图标最大可用尺寸
            max_size = 0
            for size in [16, 32, 48, 64, 128, 256]:
                if not file_icon.actualSize(QSize(size, size)).isNull():
                    max_size = size
            
            # 使用最大尺寸提取图标
            pixmap = file_icon.pixmap(max_size, max_size)
            if pixmap.isNull():
                return ""
            
            # 裁剪掉空白区域
            content_rect = get_non_transparent_rect(pixmap)
            if not content_rect.isNull() and pixmap.size() != content_rect.size():
                pixmap = pixmap.copy(content_rect)
            
            # 缩放到合理的保存尺寸(最大128)
            save_size = min(128, max(pixmap.width(), pixmap.height()))
            if pixmap.width() > save_size or pixmap.height() > save_size:
                pixmap = pixmap.scaled(
                    save_size, save_size,
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            
            if pixmap.save(str(icon_save_path), "PNG"):
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
            
            self._launch_by_type(target_path, arguments)
            
            # 记录启动次数和时间
            app_id = app_data.get('id')
            if app_id is not None:
                self._record_launch(app_id)
            
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
    
    def _get_recent_apps(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近使用的应用"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM app_launcher 
                    WHERE plugin_id = ? AND last_launch_time IS NOT NULL
                    ORDER BY last_launch_time DESC
                    LIMIT ?
                """, (self.PLUGIN_ID, limit))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.core.logger.error(f"获取最近使用应用失败: {e}")
            return []
    
    def _get_favorite_apps(self) -> List[Dict[str, Any]]:
        """获取收藏的应用"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM app_launcher 
                    WHERE plugin_id = ? AND is_favorite = 1
                    ORDER BY name
                """, (self.PLUGIN_ID,))
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.core.logger.error(f"获取收藏应用失败: {e}")
            return []
    
    def _record_launch(self, app_id: int):
        """记录应用启动"""
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    UPDATE app_launcher 
                    SET launch_count = launch_count + 1,
                        last_launch_time = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (app_id,))
                conn.commit()
        except Exception as e:
            self.core.logger.error(f"记录启动失败: {e}")
    
    def _launch_by_type(self, target_path: str, arguments: str = ''):
        """根据文件类型选择启动方式"""
        if os.path.isdir(target_path):
            os.startfile(target_path)
            return
        
        ext = os.path.splitext(target_path)[1].lower()
        
        if ext == '.py':
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}" --run-script "{target_path}"'
            else:
                python_exe = get_python_executable()
                cmd = f'"{python_exe}" "{target_path}"'
            if arguments:
                cmd += f' {arguments}'
            subprocess.Popen(cmd, shell=True)
        elif ext in ('.bat', '.cmd'):
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'"{target_path}"', shell=True)
        elif ext == '.ps1':
            if arguments:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}"', shell=True)
        elif ext == '.vbs':
            if arguments:
                subprocess.Popen(f'wscript "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'wscript "{target_path}"', shell=True)
        else:
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                os.startfile(target_path)
    
    def _toggle_favorite(self, app_data: Dict[str, Any]):
        """切换收藏状态"""
        app_id = app_data.get('id')
        if app_id is None:
            return
        
        is_favorite = app_data.get('is_favorite', 0)
        new_status = 0 if is_favorite else 1
        
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    UPDATE app_launcher 
                    SET is_favorite = ?
                    WHERE id = ?
                """, (new_status, app_id))
                conn.commit()
            
            self._refresh_all_tabs()
            
            action = "取消收藏" if is_favorite else "收藏"
            InfoBar.success(
                title="操作成功",
                content=f"已{action} {app_data.get('name', 'Unknown')}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
        except Exception as e:
            self.core.logger.error(f"切换收藏状态失败: {e}")
            InfoBar.error(
                title="操作失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _edit_app(self, app_data: Dict[str, Any]):
        """编辑应用"""
        categories = self.db.get_categories(self.PLUGIN_ID)
        dialog = AppEditDialog(app_data, categories, self)
        
        if dialog.exec():
            new_data = dialog.get_data()
            app_id = app_data.get('id')
            
            if app_id is not None:
                # 检查路径是否改变，如果改变则重新提取图标
                old_path = app_data.get('target_path', '')
                new_path = new_data['target_path']
                icon_path = app_data.get('icon_path', '')
                
                if old_path != new_path:
                    # 路径改变，重新提取图标
                    if icon_path:
                        abs_icon_path = get_app_data_path(icon_path)
                        if abs_icon_path.exists():
                            try:
                                abs_icon_path.unlink()
                            except Exception:
                                pass
                    icon_path = self._extract_icon(new_path)
                
                # 更新数据库
                self.db.update_app(
                    plugin_id=self.PLUGIN_ID,
                    app_id=app_id,
                    name=new_data['name'],
                    target_path=new_data['target_path'],
                    category_id=new_data['category_id'],
                    arguments=new_data['arguments'],
                    notes=new_data['notes'],
                    icon_path=icon_path
                )
                
                self._refresh_all_tabs()
                
                InfoBar.success(
                    title="修改成功",
                    content=f"已更新 {new_data['name']}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _delete_app(self, app_data: Dict[str, Any]):
        """删除应用"""
        box = MessageBox("删除应用", f"确定要删除 '{app_data.get('name', 'Unknown')}' 吗？", self)
        if box.exec():
            app_id = app_data.get('id')
            if app_id is not None:
                icon_path = app_data.get('icon_path', '')
                if icon_path:
                    abs_icon_path = get_app_data_path(icon_path)
                    if abs_icon_path.exists():
                        try:
                            abs_icon_path.unlink()
                        except Exception as e:
                            self.core.logger.warning(f"删除图标文件失败: {e}")
                
                self.db.delete_app(self.PLUGIN_ID, app_id)
                self.selected_app_ids.discard(app_id)
                self._refresh_all_tabs()
                
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

        self._refresh_all_tabs()
        if text:
            self.tab_widget.setCurrentIndex(0)
    
    def _show_sort_menu(self):
        """显示排序菜单"""
        menu = QMenu(self)
        menu.setStyleSheet(get_menu_style())
        
        # 按名称排序
        name_action = QAction("按名称排序", self)
        name_action.triggered.connect(lambda: self._sort_apps('name'))
        menu.addAction(name_action)
        
        # 按添加时间排序
        time_action = QAction("按添加时间排序", self)
        time_action.triggered.connect(lambda: self._sort_apps('created_at'))
        menu.addAction(time_action)
        
        # 按更新时间排序
        update_action = QAction("按更新时间排序", self)
        update_action.triggered.connect(lambda: self._sort_apps('updated_at'))
        menu.addAction(update_action)
        
        # 按使用频率排序
        frequency_action = QAction("按使用频率排序", self)
        frequency_action.triggered.connect(lambda: self._sort_apps('launch_count'))
        menu.addAction(frequency_action)
        
        # 按最近使用排序
        recent_action = QAction("按最近使用排序", self)
        recent_action.triggered.connect(lambda: self._sort_apps('last_launch_time'))
        menu.addAction(recent_action)
        
        menu.exec_(QCursor.pos())
    
    def _sort_apps(self, sort_by: str):
        """排序应用"""
        self._current_sort_by = sort_by
        self._refresh_all_tabs()
        
        InfoBar.success(
            title="排序完成",
            content=f"已按{sort_by}排序",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )
    
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
    PLUGIN_PRIORITY = 15

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

    def supports_search(self) -> bool:
        """支持全局搜索"""
        return True

    def search(self, query: str):
        """搜索应用"""
        db = DatabaseManager()
        results = []
        apps = db.search_apps(self.PLUGIN_ID, query)
        for app in apps[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=app['name'],
                description=app.get('target_path', ''),
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in app['name'].lower() else 0.5,
                action=lambda a=app: self._launch_app(a),
                metadata={'app_id': app['id']}
            )
            results.append(result)
        return results

    def _launch_app(self, app: Dict[str, Any]) -> None:
        """启动应用（全局搜索调用）"""
        target_path = app.get('target_path', '')
        if not target_path or not os.path.exists(target_path):
            return
        arguments = app.get('arguments', '') or ''
        
        if os.path.isdir(target_path):
            os.startfile(target_path)
            return
        
        ext = os.path.splitext(target_path)[1].lower()
        
        if ext == '.py':
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}" --run-script "{target_path}"'
            else:
                python_exe = get_python_executable()
                cmd = f'"{python_exe}" "{target_path}"'
            if arguments:
                cmd += f' {arguments}'
            subprocess.Popen(cmd, shell=True)
        elif ext in ('.bat', '.cmd'):
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'"{target_path}"', shell=True)
        elif ext == '.ps1':
            if arguments:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}"', shell=True)
        elif ext == '.vbs':
            if arguments:
                subprocess.Popen(f'wscript "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'wscript "{target_path}"', shell=True)
        else:
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                os.startfile(target_path)
