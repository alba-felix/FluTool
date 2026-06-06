from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen
from qfluentwidgets import isDarkTheme
from qfluentwidgets.common.icon import drawIcon

# ── 常量 ──────────────────────────────────────────────────────────────
_ITEM_HEIGHT = 36
_ITEM_WIDTH = 180
_MARGIN = 6
_SPACING = 2
_MAX_MENU_HEIGHT = 400
_MENU_WIDTH = 200
_EDGE_PADDING = 10


class NoteMenuItem(QWidget):
    """笔记弹出菜单的单个条目"""
    clicked = pyqtSignal(str)

    def __init__(self, routeKey: str, icon, text: str, parent=None):
        super().__init__(parent)
        self.routeKey = routeKey
        self._icon = icon
        self._text = text
        self._isHover = False
        self.setFixedHeight(_ITEM_HEIGHT)
        self.setFixedWidth(_ITEM_WIDTH)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)

        c = 255 if isDarkTheme() else 0

        if self._isHover:
            hover_color = QColor(255, 255, 255, 10) if isDarkTheme() else QColor(0, 0, 0, 10)
            painter.setBrush(hover_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(4, 2, -4, -2), 4, 4)

        drawIcon(self._icon, painter, QRect(12, 10, 16, 16))

        painter.setPen(QColor(c, c, c))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(
            QRect(36, 0, self.width() - 36, self.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._text,
        )

    def enterEvent(self, e):
        self._isHover = True
        self.update()

    def leaveEvent(self, e):
        self._isHover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.pos()):
            self.clicked.emit(self.routeKey)


class NoteMenu(QWidget):
    """笔记弹出菜单容器，带屏幕边界溢出保护"""
    itemClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[NoteMenuItem] = []
        self._setup_ui()
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        layout.setSpacing(_SPACING)
        layout.setAlignment(Qt.AlignTop)

    def clearItems(self):
        for item in self._items:
            self.layout().removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def addItem(self, routeKey: str, icon, text: str):
        item = NoteMenuItem(routeKey, icon, text, self)
        item.clicked.connect(self._on_item_clicked)
        self._items.append(item)
        self.layout().addWidget(item)

    def setItems(self, items: list):
        self.clearItems()
        for item_data in items:
            self.addItem(item_data['routeKey'], item_data['icon'], item_data['text'])
        self._recalc_size()

    def _recalc_size(self):
        if not self._items:
            self.setFixedSize(_MENU_WIDTH, _ITEM_HEIGHT + _MARGIN * 2)
            return
        count = len(self._items)
        total_height = (
            _MARGIN * 2
            + count * _ITEM_HEIGHT
            + (count - 1) * _SPACING
        )
        self.setFixedSize(_MENU_WIDTH, min(total_height, _MAX_MENU_HEIGHT))

    def _on_item_clicked(self, routeKey: str):
        self.itemClicked.emit(routeKey)
        self.hide()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        if isDarkTheme():
            bg_color = QColor(45, 45, 45)
            border_color = QColor(255, 255, 255, 20)
        else:
            bg_color = QColor(252, 252, 252)
            border_color = QColor(0, 0, 0, 20)

        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 8, 8)

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -3, -3), 8, 8)

    def exec_(self, pos: QPoint):
        self._ensure_valid_size()
        self._clamp_to_screen(pos)
        self.move(pos)
        self.show()
        self.activateWindow()

    def _ensure_valid_size(self):
        if self.width() <= 0 or self.height() <= 0:
            self._recalc_size()

    def _clamp_to_screen(self, pos: QPoint):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w, h = self.width(), self.height()
        px, py = pos.x(), pos.y()
        if px + w > geo.right():
            px = geo.right() - w - _EDGE_PADDING
        if py + h > geo.bottom():
            py = geo.bottom() - h - _EDGE_PADDING
        if px < geo.left():
            px = geo.left() + _EDGE_PADDING
        if py < geo.top():
            py = geo.top() + _EDGE_PADDING
        pos.setX(px)
        pos.setY(py)