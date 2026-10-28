"""桌面悬浮球：常驻快捷入口，点击唤醒主窗口。

占位实现：暂不挂业务功能。置顶 Tool 窗口（不占任务栏），
支持拖拽移动与位置记忆（QSettings），点击调用主窗口
show_and_activate() 恢复/置前。同进程内直接持引用调用，
无需跨窗口/跨进程通信。
"""

from PyQt5.QtCore import QPoint, QSettings, Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt5.QtWidgets import QApplication, QWidget

# 球体直径（逻辑像素）
_BALL_SIZE = 44
# 位移小于该值（曼哈顿长度）视为点击而非拖拽
_DRAG_THRESHOLD = 4
# 球体配色（跟随主题切换由后续增强实现，当前用固定主题蓝）
_BALL_COLOR = QColor("#0078d4")
_BALL_COLOR_HOVER = QColor("#2b96ea")
_BALL_BORDER = QColor(255, 255, 255, 60)


class FloatingBall(QWidget):
	"""桌面悬浮球：无边框置顶圆球，拖拽移动、点击唤醒主窗口

	属性：
		_main_window: 主窗口引用，点击时调用其 show_and_activate()
		_settings: QSettings，持久化球体位置
		_drag_offset: 按下点相对窗口左上角的偏移
		_moved: 本次按下后是否发生拖拽（区分点击与拖动）
		_hovered: 鼠标是否悬停（控制高亮）
	"""

	def __init__(self, main_window, parent=None):
		super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
		self._main_window = main_window
		self._settings = QSettings("FluTool", "FloatingBall")
		self._drag_offset = QPoint()
		self._moved = False
		self._hovered = False
		self.setFixedSize(_BALL_SIZE, _BALL_SIZE)
		self.setAttribute(Qt.WA_TranslucentBackground)
		self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
		self.setToolTip("FluTool - 点击唤醒主窗口")
		self._restore_position()
		self.show()

	def paintEvent(self, event):
		"""绘制圆形球体：径向渐变主色 + 边缘高光"""
		painter = QPainter(self)
		painter.setRenderHint(QPainter.Antialiasing)
		rect = self.rect().adjusted(2, 2, -2, -2)
		gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
		color = _BALL_COLOR_HOVER if self._hovered else _BALL_COLOR
		gradient.setColorAt(0, color.lighter(130))
		gradient.setColorAt(1, color)
		painter.setPen(QPen(_BALL_BORDER, 1))
		painter.setBrush(gradient)
		painter.drawEllipse(rect)
		painter.end()

	def enterEvent(self, event):
		self._hovered = True
		self.update()

	def leaveEvent(self, event):
		self._hovered = False
		self.update()

	def mousePressEvent(self, event):
		if event.button() == Qt.LeftButton:
			self._drag_offset = event.globalPos() - self.pos()
			self._moved = False

	def mouseMoveEvent(self, event):
		if not (event.buttons() & Qt.LeftButton):
			return
		if not self._moved:
			delta = event.globalPos() - (self.pos() + self._drag_offset)
			if delta.manhattanLength() <= _DRAG_THRESHOLD:
				return
			self._moved = True
		self.move(event.globalPos() - self._drag_offset)

	def mouseReleaseEvent(self, event):
		if event.button() != Qt.LeftButton:
			return
		if self._moved:
			self._save_position()
		else:
			self._activate_main_window()

	def _activate_main_window(self) -> None:
		"""点击球体：唤醒主窗口（恢复最小化/隐藏并置前）"""
		if self._main_window is not None:
			self._main_window.show_and_activate()

	def _restore_position(self) -> None:
		"""恢复上次位置；无记录或越界时落在屏幕右侧中部"""
		geo = QApplication.primaryScreen().availableGeometry()
		default_pos = QPoint(geo.right() - _BALL_SIZE - 8,
		                     geo.top() + geo.height() // 3)
		pos = self._settings.value("pos")
		if pos is not None:
			default_pos = QPoint(int(pos.x()), int(pos.y()))
		# 限制在屏幕可视区域内，防止分辨率变化后球体丢失
		default_pos.setX(max(geo.left(), min(default_pos.x(), geo.right() - _BALL_SIZE)))
		default_pos.setY(max(geo.top(), min(default_pos.y(), geo.bottom() - _BALL_SIZE)))
		self.move(default_pos)

	def _save_position(self) -> None:
		"""拖拽结束后保存当前位置"""
		self._settings.setValue("pos", self.pos())
