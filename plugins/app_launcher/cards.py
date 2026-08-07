"""应用卡片组件"""
import os
from typing import Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal, QFileInfo
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBrush, QPen, QCursor, QTextDocument, QPalette
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QFileIconProvider, QAction,
)
from qfluentwidgets import (
    FluentIcon as FIF, CardWidget, IconWidget, CaptionLabel,
    CheckBox, isDarkTheme, RoundMenu,
)

from core import get_app_data_path

from . import (
    CARD_WIDTH, CARD_HEIGHT, ICON_SIZE, LIST_CARD_HEIGHT,
    GRID_VIEW, LIST_VIEW, DEFAULT_ICON_SIZE,
    get_non_transparent_rect, highlight_text,
)


class ElidedLabel(QLabel):
    """支持文本省略号的标签，弥补 PyQt5 QLabel 无 setTextElideMode 的不足"""

    def __init__(self, text: str = "", parent=None):
        # 兼容 QLabel(self) 与 QLabel(text, parent) 两种调用形式
        if isinstance(text, QWidget):
            parent = text
            text = ""
        super().__init__(text, parent)
        self._elide_mode = Qt.ElideNone
        self._plain_text = text

    def setTextElideMode(self, mode) -> None:
        """设置省略号模式，与 Qt 原生 API 对齐"""
        self._elide_mode = mode
        self.update()

    def setText(self, text: str) -> None:
        self._plain_text = text
        super().setText(text)
        self.update()

    def paintEvent(self, event) -> None:
        # 富文本较长时无法用字体度量精确截断；仅在数据为纯文本时空载路径处理
        if self._elide_mode == Qt.ElideNone or not self.text():
            return super().paintEvent(event)

        rect = self.contentsRect()
        if rect.width() <= 0:
            return super().paintEvent(event)

        plain = self._plain_text or self.text()
        # 富文本（HTML 高亮）会干扰字体度量，此时退回原生绘制
        if "<" in plain or "&" in plain:
            return super().paintEvent(event)

        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(plain)
        if text_width <= rect.width():
            return super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(self.palette().color(QPalette.WindowText))
        elided = fm.elidedText(plain, self._elide_mode, rect.width())
        painter.drawText(rect, self.alignment(), elided)
        painter.end()


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

        self._name_label = ElidedLabel(self)
        self._name_label.setWordWrap(False)
        self._name_label.setTextFormat(Qt.RichText)
        self._name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._name_label.setTextElideMode(Qt.ElideRight)
        text_layout.addWidget(self._name_label)

        self._subtitle_label = ElidedLabel(self)
        self._subtitle_label.setWordWrap(False)
        self._subtitle_label.setTextFormat(Qt.RichText)
        self._subtitle_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._subtitle_label.setTextElideMode(Qt.ElideRight)
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
        menu = RoundMenu(parent=self)

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
