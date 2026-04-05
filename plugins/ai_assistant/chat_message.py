"""
AI 助手对话消息组件
左右分布布局：AI在左，用户在右
"""
from typing import Optional

from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QScrollArea,
)
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFontMetrics
from qfluentwidgets import isDarkTheme, Theme


class MessageBubble(QWidget):
    """消息气泡组件"""

    def __init__(self, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self._setup_ui()
        self._connect_theme_signal()

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(8)

        if self.is_user:
            main_layout.addStretch()

        self._label = QLabel(self.text)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setCursor(Qt.IBeamCursor)
        self._label.setMaximumWidth(600)

        main_layout.addWidget(self._label)

        if not self.is_user:
            main_layout.addStretch()

        self._apply_style()

    def update_text(self, text: str):
        """更新消息文本（用于流式输出）"""
        self.text = text
        self._label.setText(text)
        # 滚动到底部
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(10, self._scroll_parent_to_bottom)

    def append_text(self, text: str):
        """追加文本（用于流式输出）"""
        self.text += text
        current = self._label.text()
        self._label.setText(current + text)
        # 滚动到底部
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(10, self._scroll_parent_to_bottom)

    def _scroll_parent_to_bottom(self):
        """滚动父容器到底部"""
        parent = self.parent()
        while parent:
            if isinstance(parent, ChatMessageList):
                parent._scroll_to_bottom()
                break
            parent = parent.parent()

    def _connect_theme_signal(self):
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        self._apply_style()

    def _apply_style(self):
        dark = isDarkTheme()

        if self.is_user:
            bg_color = "#0078d4"
            text_color = "#ffffff"
        else:
            if dark:
                bg_color = "#3d3d3d"
                text_color = "#ffffff"
            else:
                bg_color = "#f0f0f0"
                text_color = "#1f1f1f"

        self._label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 14px;
                line-height: 1.5;
            }}
        """)

    def disconnect(self):
        from qfluentwidgets import qconfig
        try:
            qconfig.themeChanged.disconnect(self._on_theme_changed)
        except Exception:
            pass


class ChatMessageContainer(QWidget):
    """消息容器（内部使用）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("chatMessageContainer")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

    def add_message(self, text: str, is_user: bool = False):
        """添加消息"""
        bubble = MessageBubble(text, is_user, self)
        self._layout.insertWidget(self._layout.count() - 1, bubble)

    def clear_messages(self):
        """清空消息"""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ChatMessageList(QWidget):
    """对话消息列表（带滚动）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()
        self._connect_theme_signal()

    def _setup_ui(self):
        self.setObjectName("chatMessageList")
        self.setAttribute(Qt.WA_StyledBackground, False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("chatScrollArea")
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        self._scroll_area.viewport().setAutoFillBackground(False)

        self._container = ChatMessageContainer(self)
        self._scroll_area.setWidget(self._container)

        main_layout.addWidget(self._scroll_area)

    def _connect_theme_signal(self):
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        self._apply_style()
        self._container.setStyleSheet("")
        for i in range(self._container._layout.count()):
            item = self._container._layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                item.widget()._apply_style()

    def _apply_style(self):
        dark = isDarkTheme()
        scroll_bg = "rgba(255,255,255,0.05)" if dark else "rgba(0,0,0,0.05)"
        scroll_handle = "rgba(255,255,255,0.2)" if dark else "rgba(0,0,0,0.2)"

        self.setStyleSheet(f"""
            #chatMessageList {{
                background: transparent;
                border: none;
            }}
            #chatScrollArea {{
                background: transparent;
                border: none;
            }}
            #chatMessageContainer {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {scroll_bg};
                width: 8px;
                border-radius: 4px;
                margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar:sub-page:vertical {{
                background: transparent;
            }}
        """)

    def add_message(self, text: str, is_user: bool = False) -> 'MessageBubble':
        """添加消息，返回消息气泡对象"""
        self._container.add_message(text, is_user)
        self._scroll_to_bottom()
        # 返回最后添加的消息气泡
        count = self._container._layout.count()
        if count > 1:
            item = self._container._layout.itemAt(count - 2)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                return item.widget()
        return None

    def get_last_message(self) -> Optional['MessageBubble']:
        """获取最后一条消息"""
        count = self._container._layout.count()
        if count > 1:
            item = self._container._layout.itemAt(count - 2)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                return item.widget()
        return None

    def clear_messages(self):
        """清空消息"""
        self._container.clear_messages()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

