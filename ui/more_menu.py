from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen
from qfluentwidgets import FluentIcon as FIF, isDarkTheme
from qfluentwidgets.common.icon import drawIcon

# ── 常量 ──────────────────────────────────────────────────────────────
_ITEM_HEIGHT = 40
_ITEM_WIDTH = 140
_MARGIN = 6
_SPACING = 4
_MAX_MENU_HEIGHT = 500
_MENU_WIDTH = 172
_EDGE_PADDING = 10


class MoreMenuItem(QWidget):
    """更多菜单项"""

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
            painter.setBrush(QColor(0, 153, 255, 20) if not isDarkTheme() else QColor(0, 153, 255, 30))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect().adjusted(4, 4, -4, -4), 6, 6)

        drawIcon(self._icon, painter, QRect(14, 12, 16, 16))

        painter.setPen(QColor(c, c, c))
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(QRect(38, 0, self.width() - 38, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self._text)

    def enterEvent(self, e):
        self._isHover = True
        self.update()

    def leaveEvent(self, e):
        self._isHover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.pos()):
            self.clicked.emit(self.routeKey)


class MoreMenu(QWidget):
    """更多菜单 - 弹出式下拉菜单，带屏幕溢出保护"""

    itemClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[MoreMenuItem] = []
        self._setup_ui()
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground)

    def _setup_ui(self):
        self._scroll_area = QScrollArea(self)
        # 关闭自动伸缩：scroll_area 视口固定为菜单高度，container 按内容高自然撑开，超出才滚动
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        # 滚动条保持可见，便于展示更多项目
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(_MARGIN, _MARGIN, _MARGIN, _MARGIN)
        self._layout.setSpacing(_SPACING)
        self._layout.setAlignment(Qt.AlignTop)

        self._scroll_area.setWidget(self._container)

        self._scroll_area.setGeometry(0, 0, _MENU_WIDTH, _MAX_MENU_HEIGHT)
        self.setFixedSize(_MENU_WIDTH, _MAX_MENU_HEIGHT)

    def clearItems(self):
        for item in self._items:
            self._layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        self._recalc_size()

    def addItem(self, routeKey: str, icon, text: str):
        item = MoreMenuItem(routeKey, icon, text, self._container)
        item.clicked.connect(self._on_item_clicked)
        self._items.append(item)
        self._layout.addWidget(item)
        self._recalc_size()

    def setItems(self, items: list):
        self.clearItems()
        for item_data in items:
            self.addItem(item_data['routeKey'], item_data['icon'], item_data['text'])
        self._recalc_size()

    def _recalc_size(self):
        """锁定为固定高度面板（不随条目数量收缩）"""
        menu_height = _MAX_MENU_HEIGHT if self._items else _ITEM_HEIGHT + _MARGIN * 2
        self.setFixedSize(_MENU_WIDTH, menu_height)
        self._scroll_area.setGeometry(0, 0, _MENU_WIDTH, menu_height)
        self._resize_container()

    def _resize_container(self):
        """widgetResizable(False) 下 QScrollArea 不会撑开容器，需按内容手动计算尺寸"""
        count = len(self._items)
        if count == 0:
            self._container.resize(_MENU_WIDTH, _ITEM_HEIGHT + _MARGIN * 2)
            return
        content_height = _MARGIN * 2 + count * _ITEM_HEIGHT + (count - 1) * _SPACING
        self._container.resize(_MENU_WIDTH, content_height)

    def _on_item_clicked(self, routeKey: str):
        self.itemClicked.emit(routeKey)
        self.hide()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        c = 255 if isDarkTheme() else 0

        # 完全不透明背景，避免触发 Windows 分层窗口（Layered Window）
        if isDarkTheme():
            painter.setBrush(QColor(32, 32, 32))
        else:
            painter.setBrush(QColor(252, 252, 252))
        painter.setPen(QPen(QColor(c, c, c, 20), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

    def exec_(self, pos: QPoint):
        """在指定位置弹出菜单，自动防屏幕溢出"""
        self._ensure_valid_size()
        self._clamp_to_screen(pos)
        self.move(pos)
        self.show()
        self.activateWindow()

    def _ensure_valid_size(self):
        """确保菜单在显示前具有有效尺寸"""
        if self.width() <= 0 or self.height() <= 0:
            self._recalc_size()

    def _clamp_to_screen(self, pos: QPoint):
        """将 pos 限制在屏幕可用区域内，防止溢出"""
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