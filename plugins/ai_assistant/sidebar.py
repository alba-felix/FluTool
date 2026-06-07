"""AI 助手侧边栏组件"""

from PyQt5.QtCore import Qt, QRect, QVariantAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidgetItem
from qfluentwidgets import (
    FluentIcon as FIF,
    ListWidget,
    isDarkTheme,
    ToolButton,
    LineEdit,
    PushButton,
)


class SidebarToggleButton(QWidget):
    """侧边栏切换按钮"""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._isCompacted = True
        self._isHover = False
        self._isPressed = False
        self.setFixedSize(48, 36)
        self.setCursor(Qt.PointingHandCursor)

    def setCompacted(self, isCompacted: bool):
        if isCompacted == self._isCompacted:
            return
        self._isCompacted = isCompacted
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.setPen(Qt.NoPen)

        if self._isPressed:
            painter.setOpacity(0.7)

        c = 255 if isDarkTheme() else 0
        if self._isHover:
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        from qfluentwidgets.common.icon import drawIcon
        drawIcon(FIF.MENU, painter, QRect(16, 10, 16, 16))

        if not self._isCompacted:
            painter.setPen(QColor(c, c, c))
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(QRect(44, 0, self.width() - 52, self.height()), Qt.AlignVCenter, "收起")

    def enterEvent(self, e):
        self._isHover = True
        self.update()

    def leaveEvent(self, e):
        self._isHover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._isPressed = True
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._isPressed = False
            self.update()
            if self.rect().contains(e.pos()):
                self.clicked.emit()


class AISidebar(QWidget):
    """AI 助手侧边栏"""

    COMPACTED_WIDTH = 48
    EXPAND_WIDTH = 260

    search_requested = pyqtSignal(str)
    clear_search_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._isExpanded = False
        self.setAttribute(Qt.WA_StyledBackground)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self._toggle_btn = SidebarToggleButton(self)
        self._toggle_btn.clicked.connect(self.toggle)
        self.vBoxLayout.addWidget(self._toggle_btn, 0, Qt.AlignTop | Qt.AlignLeft)

        # 顶部工具栏容器（新建会话 + 搜索）
        self._top_toolbar = QWidget(self)
        self._top_toolbar_layout = QHBoxLayout(self._top_toolbar)
        self._top_toolbar_layout.setContentsMargins(8, 8, 8, 8)
        self._top_toolbar_layout.setSpacing(8)

        self._new_chat_btn = PushButton("新建会话", self)
        self._new_chat_btn.setIcon(FIF.ADD_TO)
        self._new_chat_btn.setFixedHeight(32)
        self._new_chat_btn.clicked.connect(self._on_new_chat)
        self._top_toolbar_layout.addWidget(self._new_chat_btn)

        self._search_edit = LineEdit(self)
        self._search_edit.setPlaceholderText("搜索对话...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.returnPressed.connect(self._on_search)
        self._search_edit.textChanged.connect(self._on_search_text_changed)
        self._top_toolbar_layout.addWidget(self._search_edit, 1)

        self._clear_search_btn = ToolButton(FIF.CANCEL, self)
        self._clear_search_btn.setToolTip("清除搜索")
        self._clear_search_btn.setFixedSize(28, 28)
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        self._clear_search_btn.setVisible(False)
        self._top_toolbar_layout.addWidget(self._clear_search_btn)

        self.vBoxLayout.addWidget(self._top_toolbar)

        self._new_chat_callback = None

        self.history_list = ListWidget(self)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.history_list.setTextElideMode(Qt.ElideRight)
        self.vBoxLayout.addWidget(self.history_list, 1)

        self._ani = QVariantAnimation(self)
        self._ani.setDuration(150)
        self._ani.setEasingCurve(QEasingCurve.OutQuad)
        self._ani.valueChanged.connect(self._on_ani_value_changed)

        self.setFixedWidth(self.COMPACTED_WIDTH)
        self._update_compacted_state()

    def _on_search(self):
        keyword = self._search_edit.text().strip()
        if keyword:
            self.search_requested.emit(keyword)
            self._clear_search_btn.setVisible(True)
        else:
            self.clear_search_requested.emit()
            self._clear_search_btn.setVisible(False)

    def _on_search_text_changed(self, text: str):
        if not text.strip():
            self.clear_search_requested.emit()
            self._clear_search_btn.setVisible(False)
        else:
            self._clear_search_btn.setVisible(True)

    def _on_clear_search(self):
        self._search_edit.clear()
        self.clear_search_requested.emit()
        self._clear_search_btn.setVisible(False)

    def _on_ani_value_changed(self, value):
        self.setFixedWidth(int(value))

    def _update_compacted_state(self):
        compacted = not self._isExpanded
        self._toggle_btn.setCompacted(compacted)
        self._top_toolbar.setVisible(self._isExpanded)
        self.history_list.setVisible(self._isExpanded)

    def toggle(self):
        if self._isExpanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self._isExpanded = True
        self._animate_width(self.EXPAND_WIDTH)
        self._update_compacted_state()

    def collapse(self):
        self._isExpanded = False
        self._animate_width(self.COMPACTED_WIDTH)
        self._update_compacted_state()

    def _animate_width(self, target: int):
        self._ani.stop()
        self._ani.setStartValue(self.width())
        self._ani.setEndValue(target)
        self._ani.start()

    def isExpanded(self) -> bool:
        return self._isExpanded

    def setNewChatCallback(self, callback):
        self._new_chat_callback = callback

    def _on_new_chat(self):
        if self._new_chat_callback:
            self._new_chat_callback()
