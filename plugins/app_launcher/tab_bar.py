"""自定义标签栏组件"""
from typing import Dict, Any

from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
from PyQt5.QtWidgets import QTabBar
from qfluentwidgets import FluentIcon as FIF, isDarkTheme
from qfluentwidgets.common.icon import drawIcon

from ui.custom_icon import CustomFluentIcon as CFIF

from . import (
    CATEGORY_ICON_MAP,
    get_category_icon,
)


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
