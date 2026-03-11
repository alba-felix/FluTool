from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen
from qfluentwidgets import FluentIcon as FIF, isDarkTheme
from qfluentwidgets.common.icon import drawIcon


class MoreMenuItem(QWidget):
    """更多菜单项"""

    clicked = pyqtSignal(str)

    def __init__(self, routeKey: str, icon, text: str, parent=None):
        super().__init__(parent)
        self.routeKey = routeKey
        self._icon = icon
        self._text = text
        self._isHover = False
        self.setFixedHeight(40)
        self.setFixedWidth(140)
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
    """更多菜单 - 弹出式下拉菜单"""

    itemClicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []
        self._setup_ui()
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_StyledBackground)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(15)
        self._shadow.setColor(QColor(0, 0, 0, 80))
        self._shadow.setOffset(0, 3)
        self.setGraphicsEffect(self._shadow)

    def clearItems(self):
        for item in self._items:
            layout = self.layout()
            layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()

    def addItem(self, routeKey: str, icon, text: str):
        item = MoreMenuItem(routeKey, icon, text, self)
        item.clicked.connect(self._on_item_clicked)
        self._items.append(item)
        self.layout().addWidget(item)

    def setItems(self, items: list):
        self.clearItems()
        for item_data in items:
            self.addItem(item_data['routeKey'], item_data['icon'], item_data['text'])
        
        # 根据项目数量调整菜单大小
        if items:
            height = len(items) * 40 + 12
            self.setFixedHeight(min(height, 400))
            self.setFixedWidth(172)

    def _on_item_clicked(self, routeKey: str):
        self.itemClicked.emit(routeKey)
        self.hide()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        c = 255 if isDarkTheme() else 0
        painter.fillRect(self.rect(), QColor(255, 255, 255, 250) if not isDarkTheme() else QColor(32, 32, 32, 250))

        painter.setPen(QPen(QColor(c, c, c, 20), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)

    def showEvent(self, e):
        super().showEvent(e)

    def exec_(self, pos: QPoint):
        self.move(pos)
        self.show()
        self.activateWindow()
