from PyQt5.QtCore import pyqtSignal, QEasingCurve, QPoint, QRect, QSize, Qt, QTimer, QVariantAnimation
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (QAbstractButton, QAction, QApplication, QHBoxLayout, QLabel, QMenu, QSystemTrayIcon,
                             QVBoxLayout, QWidget, QFrame, QScrollArea)
from qfluentwidgets import (BodyLabel, CaptionLabel, FluentIcon as FIF, FluentStyleSheet, HyperlinkLabel, InfoBar,
                           InfoBarPosition, isDarkTheme,
                           NavigationWidget, setCustomStyleSheet, setTheme, SmoothScrollArea, StrongBodyLabel, Theme,
                           TransparentToolButton, SubtitleLabel, qconfig, MessageBox)
from qfluentwidgets.common.font import setFont
from qfluentwidgets.common.icon import drawIcon, toQIcon
from qfluentwidgets.window.stacked_widget import StackedWidget
from qframelesswindow import FramelessMainWindow, StandardTitleBar

from core import get_resource_path
from .more_menu import MoreMenu
from .settings_interface import SettingsInterface
from .global_search_dialog import GlobalSearchDialog
from .plugin_docs_interface import PluginDocsInterface
from .about_interfaces import AboutInterface, CheckUpdateInterface, FeedbackInterface
from .plugin_host import PluginHost


class ScrollableNavButton(NavigationWidget):
	"""可滚动导航按钮"""
	
	clicked = pyqtSignal(bool)
	
	def __init__(self, icon, text: str, parent=None):
		super().__init__(True, parent)
		self._icon = icon
		self._text = text
		self._expandWidth = 150
		setFont(self)
		self.setToolTip(text)
	
	def text(self):
		return self._text
	
	def setText(self, text: str):
		self._text = text
		self.update()
	
	def icon(self):
		return toQIcon(self._icon)
	
	def setIcon(self, icon):
		self._icon = icon
		self.update()
	
	def setExpandWidth(self, width: int):
		self._expandWidth = width
		if not self.isCompacted:
			self.setFixedWidth(width)
	
	def setCompacted(self, isCompacted: bool):
		if isCompacted == self.isCompacted:
			return
		self.isCompacted = isCompacted
		if isCompacted:
			self.setFixedSize(48, 36)
		else:
			self.setFixedSize(self._expandWidth, 36)
		self.update()
	
	def paintEvent(self, e):
		painter = QPainter(self)
		painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
		painter.setPen(Qt.NoPen)
		
		if self.isPressed:
			painter.setOpacity(0.7)
		if not self.isEnabled():
			painter.setOpacity(0.4)
		
		c = 255 if isDarkTheme() else 0
		
		if self.isSelected:
			painter.setBrush(QColor(c, c, c, 6 if self.isEnter else 10))
			painter.drawRoundedRect(self.rect(), 5, 5)
			painter.setBrush(QColor(0, 153, 255) if not isDarkTheme() else QColor(0, 153, 255))
			painter.drawRoundedRect(0, 10, 3, 16, 1.5, 1.5)
		elif self.isEnter and self.isEnabled():
			painter.setBrush(QColor(c, c, c, 10))
			painter.drawRoundedRect(self.rect(), 5, 5)
		
		drawIcon(self._icon, painter, QRect(12, 10, 16, 16))
		
		if not self.isCompacted:
			painter.setFont(self.font())
			painter.setPen(self.textColor())
			painter.drawText(QRect(40, 0, self.width() - 48, self.height()), Qt.AlignVCenter, self._text)
	
	def mouseReleaseEvent(self, e):
		super().mouseReleaseEvent(e)
		self.clicked.emit(True)


class ScrollButton(QAbstractButton):
	"""滚动按钮"""
	
	clicked = pyqtSignal()
	
	def __init__(self, direction: str, parent=None):
		super().__init__(parent)
		self._direction = direction
		self.setFixedSize(48, 36)
		self.setCursor(Qt.PointingHandCursor)
		self._isHover = False
		self._isPressed = False
	
	def paintEvent(self, e):
		painter = QPainter(self)
		painter.setRenderHints(QPainter.Antialiasing)
		
		c = 255 if isDarkTheme() else 0
		if self._isHover:
			painter.setBrush(QColor(c, c, c, 20))
		else:
			painter.setBrush(QColor(c, c, c, 10))
		painter.setPen(Qt.NoPen)
		painter.drawRoundedRect(self.rect(), 4, 4)
		
		if self._direction == "up":
			icon = FIF.CARE_UP_SOLID
		else:
			icon = FIF.MORE
		drawIcon(icon, painter, QRect(16, 4, 16, 16))
	
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
	
	def enterEvent(self, e):
		self._isHover = True
		self.update()
	
	def leaveEvent(self, e):
		self._isHover = False
		self.update()


class MenuButton(QWidget):
	"""菜单按钮"""
	
	clicked = pyqtSignal()
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self._expandWidth = 150
		self._isCompacted = True
		self._isHover = False
		self._isPressed = False
		self.setFixedSize(48, 36)
		self.setCursor(Qt.PointingHandCursor)
		setFont(self)
	
	@property
	def isCompacted(self):
		return self._isCompacted
	
	def setExpandWidth(self, width: int):
		self._expandWidth = width
		if not self._isCompacted:
			self.setFixedWidth(width)
	
	def setCompacted(self, isCompacted: bool):
		if isCompacted == self._isCompacted:
			return
		self._isCompacted = isCompacted
		if isCompacted:
			self.setFixedSize(48, 36)
		else:
			self.setFixedSize(self._expandWidth, 36)
		self.update()
	
	def paintEvent(self, e):
		painter = QPainter(self)
		painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
		painter.setPen(Qt.NoPen)
		
		if self._isPressed:
			painter.setOpacity(0.7)
		
		c = 255 if isDarkTheme() else 0
		if self._isHover:
			painter.setBrush(QColor(c, c, c, 10))
			painter.drawRoundedRect(self.rect(), 5, 5)
		
		drawIcon(FIF.MENU, painter, QRect(12, 10, 16, 16))
		
		if not self._isCompacted:
			painter.setFont(self.font())
			painter.setPen(QColor(c, c, c))
			painter.drawText(QRect(40, 0, self.width() - 48, self.height()), Qt.AlignVCenter, "菜单")
	
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


class ScrollableNavigationPanel(QWidget):
	"""可滚动导航面板"""
	
	displayModeChanged = pyqtSignal(bool)
	moreClicked = pyqtSignal()
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self._isExpanded = False
		self._expandWidth = 150
		self._items = {}
		self._overflow_items = []
		self._currentKey = None
		self._maxVisibleItems = 8
		
		self.vBoxLayout = QVBoxLayout(self)
		self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
		self.vBoxLayout.setSpacing(0)
		
		self._menu_btn = MenuButton(self)
		self._menu_btn.clicked.connect(lambda: self.toggle())
		
		self._up_btn = ScrollButton("up", self)
		# self._down_btn = ScrollButton("down", self)
		self._more_btn = ScrollButton("more", self)
		self._up_btn.hide()
		# self._down_btn.hide()
		self._more_btn.hide()
		
		self._scroll_area = SmoothScrollArea(self)
		self._scroll_area.setWidgetResizable(True)
		self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self._scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
		
		self._scroll_widget = QWidget()
		self._scroll_layout = QVBoxLayout(self._scroll_widget)
		self._scroll_layout.setContentsMargins(4, 4, 4, 4)
		self._scroll_layout.setSpacing(4)
		self._scroll_layout.setAlignment(Qt.AlignTop)
		self._scroll_widget.setStyleSheet("background: transparent;")
		
		self._bottom_widget = QWidget()
		self._bottom_layout = QVBoxLayout(self._bottom_widget)
		self._bottom_layout.setContentsMargins(4, 4, 4, 4)
		self._bottom_layout.setSpacing(4)
		self._bottom_layout.setAlignment(Qt.AlignBottom)
		
		self._scroll_area.setWidget(self._scroll_widget)
		
		self.vBoxLayout.addWidget(self._menu_btn)
		self.vBoxLayout.addWidget(self._up_btn)
		self.vBoxLayout.addWidget(self._scroll_area, 1)
		self.vBoxLayout.addWidget(self._bottom_widget)
		# self.vBoxLayout.addWidget(self._down_btn)
		self.vBoxLayout.addWidget(self._more_btn)
		
		self._up_btn.clicked.connect(self._scroll_up)
		# self._down_btn.clicked.connect(self._scroll_down)
		self._more_btn.clicked.connect(self._on_more_clicked)
		
		self.setFixedWidth(48)
		self.setAttribute(Qt.WA_StyledBackground)
		FluentStyleSheet.NAVIGATION_INTERFACE.apply(self)
		
		self._ani = QVariantAnimation(self)
		self._ani.setDuration(150)
		self._ani.setEasingCurve(QEasingCurve.OutQuad)
		self._ani.valueChanged.connect(self._on_ani_value_changed)
		self._ani.finished.connect(self._on_ani_finished)
	
	def _on_ani_value_changed(self, value):
		if self._ani.state() == QVariantAnimation.Running:
			self.setFixedWidth(int(value))
	
	def _on_ani_finished(self):
		self.displayModeChanged.emit(self._isExpanded)
	
	def _update_parent_layout(self):
		pass
	
	def _on_more_clicked(self):
		self.moreClicked.emit()
	
	def getOverflowItems(self):
		return self._overflow_items
	
	def addItem(self, routeKey: str, icon, text: str, onClick=None, position=None):
		if routeKey in self._items:
			return
		
		btn = ScrollableNavButton(icon, text, self._scroll_widget)
		btn.setExpandWidth(self._expandWidth)
		btn.clicked.connect(lambda: self._on_item_clicked(routeKey))
		if onClick:
			btn.clicked.connect(onClick)
		
		self._items[routeKey] = btn
		
		if position:
			self._bottom_layout.addWidget(btn, 0, Qt.AlignTop)
		else:
			self._scroll_layout.addWidget(btn, 0, Qt.AlignTop)
		
		self._check_overflow()
		return btn
	
	def removeItem(self, routeKey: str):
		if routeKey not in self._items:
			return
		btn = self._items.pop(routeKey)
		self._scroll_layout.removeWidget(btn)
		self._bottom_layout.removeWidget(btn)
		btn.deleteLater()
		self._overflow_items = [item for item in self._overflow_items if item['routeKey'] != routeKey]
		self._check_overflow()
	
	def setCurrentItem(self, routeKey: str):
		if routeKey not in self._items:
			return
		if self._currentKey and self._currentKey in self._items:
			self._items[self._currentKey].setSelected(False)
		self._currentKey = routeKey
		self._items[routeKey].setSelected(True)
	
	def currentItem(self):
		return self._items.get(self._currentKey)
	
	def _on_item_clicked(self, routeKey: str):
		self.setCurrentItem(routeKey)
	
	def expand(self, useAni=True):
		self._isExpanded = True
		target_width = self._expandWidth
		if useAni:
			self._animate_width(target_width)
		else:
			self.setFixedWidth(target_width)
		self._menu_btn.setCompacted(False)
		for btn in self._items.values():
			btn.setCompacted(False)
		self.displayModeChanged.emit(True)
	
	def collapse(self, useAni=True):
		self._isExpanded = False
		if useAni:
			self._animate_width(48)
		else:
			self.setFixedWidth(48)
		self._menu_btn.setCompacted(True)
		for btn in self._items.values():
			btn.setCompacted(True)
		self.displayModeChanged.emit(False)
	
	def toggle(self):
		if self._isExpanded:
			self.collapse()
		else:
			self.expand()
	
	def isExpanded(self):
		return self._isExpanded
	
	def setExpandWidth(self, width: int):
		self._expandWidth = width
		self._menu_btn.setExpandWidth(width)
		for btn in self._items.values():
			btn.setExpandWidth(width)
		if self._isExpanded:
			self.setFixedWidth(width)
	
	def _animate_width(self, target_width: int):
		self._ani.stop()
		self._ani.setStartValue(self.width())
		self._ani.setEndValue(target_width)
		self._ani.start()
	
	def _scroll_up(self):
		bar = self._scroll_area.verticalScrollBar()
		bar.setValue(bar.value() - 100)
	
	# def _scroll_down(self):#暂时不要了
	#     bar = self._scroll_area.verticalScrollBar()
	#     bar.setValue(bar.value() + 100)
	
	def _check_overflow(self):
		# 延迟检查，确保布局完成后再计算
		QTimer.singleShot(0, self._update_overflow)
	
	def _update_overflow(self):
		widget_height = self._scroll_widget.height()
		viewport_height = self._scroll_area.viewport().height()
		
		# 如果高度还未计算，稍后重试
		if viewport_height <= 0:
			QTimer.singleShot(50, self._update_overflow)
			return
		
		if widget_height > viewport_height:
			bar = self._scroll_area.verticalScrollBar()
			self._up_btn.setVisible(bar.value() > 0)
			# self._down_btn.setVisible(bar.value() < bar.maximum())
			self._more_btn.show()
		else:
			self._up_btn.hide()
			# self._down_btn.hide()
			self._more_btn.hide()
		
		self._update_overflow_items()
	
	def _update_overflow_items(self):
		self._overflow_items.clear()
		
		available_height = self._scroll_area.viewport().height()
		
		if available_height <= 0:
			return
		
		accumulated_height = 0
		margin = self._scroll_layout.contentsMargins()
		
		for key, btn in self._items.items():
			btn_height = btn.height()
			spacing = self._scroll_layout.spacing()
			
			if accumulated_height + btn_height > available_height:
				self._overflow_items.append({
					'routeKey': key,
					'icon': btn._icon,
					'text': btn._text
				})
			else:
				accumulated_height += btn_height + spacing
	
	def resizeEvent(self, e):
		super().resizeEvent(e)
		self._check_overflow()
	
	def showEvent(self, e):
		super().showEvent(e)
		# 窗口显示时检查溢出
		QTimer.singleShot(100, self._check_overflow)
	
	def wheelEvent(self, e):
		delta = e.angleDelta().y()
		if delta == 0:
			return
		
		keys = list(self._items.keys())
		if not keys:
			return
		
		if self._currentKey is None:
			self.setCurrentItem(keys[0])
			return
		
		current_idx = keys.index(self._currentKey) if self._currentKey in keys else 0
		
		if delta > 0:
			new_idx = max(0, current_idx - 1)
		else:
			new_idx = min(len(keys) - 1, current_idx + 1)
		
		if new_idx != current_idx:
			new_key = keys[new_idx]
			self.setCurrentItem(new_key)
			btn = self._items[new_key]
			btn.clicked.emit(True)
		
		e.accept()


class FluentTitleBarButton(StandardTitleBar):
	"""Fluent 风格标题栏"""
	
	def __init__(self, parent):
		super().__init__(parent)
		self.setFixedHeight(38)
		self.hBoxLayout.setContentsMargins(16, 0, 0, 0)
		FluentStyleSheet.FLUENT_WINDOW.apply(self)
		# 隐藏标题栏图标
		if hasattr(self, 'iconLabel'):
			self.iconLabel.hide()


class PushFluentWindow(FramelessMainWindow):
	"""挤压式侧边栏窗口 - 基于 FramelessMainWindow"""
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self._init_window()
		self._init_navigation()
		self._setup_title_bar()
		self._setup_tray()
	
	def _init_window(self) -> None:
		self._lightBackgroundColor = QColor(240, 244, 249)
		self._darkBackgroundColor = QColor(32, 32, 32)
		self.setAttribute(Qt.WA_StyledBackground)
		FluentStyleSheet.FLUENT_WINDOW.apply(self)
	
	def _init_navigation(self) -> None:
		self._central_widget = QWidget(self)
		self.setCentralWidget(self._central_widget)

		self.hBoxLayout = QHBoxLayout(self._central_widget)
		self.hBoxLayout.setSpacing(0)
		self.hBoxLayout.setContentsMargins(0, 0, 0, 0)

		self.navigationInterface = ScrollableNavigationPanel(self._central_widget)
		self.navigationInterface.setExpandWidth(150)

		self.stackedWidget = StackedWidget(self._central_widget)
		self.stackedWidget.setAnimationEnabled(False)
		FluentStyleSheet.FLUENT_WINDOW.apply(self.stackedWidget)

		self._content_widget = QWidget(self)
		self._content_layout = QHBoxLayout(self._content_widget)
		self._content_layout.setContentsMargins(0, 38, 0, 0)
		self._content_layout.setSpacing(0)
		self._content_layout.addWidget(self.stackedWidget, 1)

		self.hBoxLayout.addWidget(self.navigationInterface)
		self.hBoxLayout.addWidget(self._content_widget, 1)

		self.stackedWidget.currentChanged.connect(self._on_current_interface_changed)
	
	def _setup_title_bar(self) -> None:
		self.setTitleBar(FluentTitleBarButton(self))
		self.titleBar.titleLabel.hide()
		self.titleBar.closeBtn.hide()
		self.titleBar.minBtn.hide()
		
		# 左侧间距
		self.titleBar.hBoxLayout.insertSpacing(2, 50)
		
		self._theme_btn = TransparentToolButton(FIF.CONSTRACT, self.titleBar)
		self._theme_btn.setFixedSize(32, 32)
		self._theme_btn.setIconSize(QSize(14, 14))
		self._theme_btn.setToolTip("<p>切换主题</p>")
		self._theme_btn.clicked.connect(self._toggle_theme)
		self.titleBar.hBoxLayout.insertWidget(3, self._theme_btn, 0, Qt.AlignLeft | Qt.AlignVCenter)
		self.titleBar.hBoxLayout.insertSpacing(4, 8)
		
		self._search_btn = TransparentToolButton(FIF.SEARCH, self.titleBar)
		self._search_btn.setFixedSize(32, 32)
		self._search_btn.setIconSize(QSize(14, 14))
		self._search_btn.setToolTip("<p>全局搜索</p>")
		self._search_btn.clicked.connect(self._on_global_search)
		self.titleBar.hBoxLayout.insertWidget(3, self._search_btn, 0, Qt.AlignLeft | Qt.AlignVCenter)
		self.titleBar.hBoxLayout.insertSpacing(4, 8)
		
		self._hide_btn = TransparentToolButton(FIF.MINIMIZE, self.titleBar)
		self._hide_btn.setFixedSize(46, 32)
		self._hide_btn.setIconSize(QSize(14, 14))
		self._hide_btn.setToolTip("<p>隐藏窗口</p>")
		self._hide_btn.clicked.connect(self._on_hide_window)
		self.titleBar.hBoxLayout.insertWidget(self.titleBar.hBoxLayout.indexOf(self.titleBar.maxBtn) + 1, self._hide_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
		
		self._quit_btn = TransparentToolButton(FIF.POWER_BUTTON, self.titleBar)
		self._quit_btn.setFixedSize(46, 32)
		self._quit_btn.setIconSize(QSize(14, 14))
		self._quit_btn.setToolTip("<p>退出程序</p>")
		self._quit_btn.clicked.connect(self._on_real_close)
		self.titleBar.hBoxLayout.insertWidget(self.titleBar.hBoxLayout.indexOf(self.titleBar.minBtn), self._quit_btn, 0, Qt.AlignRight | Qt.AlignVCenter)
	
	def _on_hide_window(self) -> None:
		if self.isVisible():
			self.hide()
			self.tray_icon.showMessage(
				"FluTool",
				"程序已最小化到系统托盘\n单击托盘图标或隐藏按钮恢复窗口",
				QSystemTrayIcon.Information,
				2000
			)
		else:
			self.show_and_activate()
	
	def _setup_tray(self) -> None:
		logo_path = get_resource_path("logo.ico")
		if logo_path.exists():
			tray_icon = QIcon(str(logo_path))
		else:
			tray_icon = QIcon()
		
		self.tray_icon = QSystemTrayIcon(self)
		self.tray_icon.setIcon(tray_icon)
		self.tray_icon.setToolTip("FluTool - 多功能工具箱")
		
		self._tray_menu = QMenu()
		self._apply_tray_menu_style()
		
		show_action = QAction("显示主窗口", self._tray_menu)
		show_action.triggered.connect(self.show_and_activate)
		self._tray_menu.addAction(show_action)
		
		self._tray_menu.addSeparator()
		
		color_picker_action = QAction("屏幕取色", self._tray_menu)
		color_picker_action.triggered.connect(self._start_screen_color_picker)
		self._tray_menu.addAction(color_picker_action)
		
		translate_action = QAction("翻译", self._tray_menu)
		translate_action.triggered.connect(self._show_translator_window)
		self._tray_menu.addAction(translate_action)
		
		self._tray_menu.addSeparator()
		
		quit_action = QAction("退出程序", self._tray_menu)
		quit_action.triggered.connect(self._on_real_close)
		self._tray_menu.addAction(quit_action)
		
		self.tray_icon.setContextMenu(self._tray_menu)
		self.tray_icon.activated.connect(self._on_tray_activated)
		self.tray_icon.messageClicked.connect(self.show_and_activate)
		self.tray_icon.show()
	
	def _apply_tray_menu_style(self) -> None:
		"""应用托盘菜单样式"""
		if isDarkTheme():
			self._tray_menu.setStyleSheet("""
				QMenu {
					background-color: #2d2d2d;
					border: 1px solid #3d3d3d;
					border-radius: 8px;
					padding: 4px;
				}
				QMenu::item {
					background-color: transparent;
					color: #ffffff;
					padding: 6px 24px 6px 12px;
					border-radius: 4px;
				}
				QMenu::item:selected {
					background-color: #3d3d3d;
				}
				QMenu::item:pressed {
					background-color: #009faa;
				}
				QMenu::separator {
					height: 1px;
					background-color: #3d3d3d;
					margin: 4px 8px;
				}
			""")
		else:
			self._tray_menu.setStyleSheet("""
				QMenu {
					background-color: #ffffff;
					border: 1px solid #e0e0e0;
					border-radius: 8px;
					padding: 4px;
				}
				QMenu::item {
					background-color: transparent;
					color: #333333;
					padding: 6px 24px 6px 12px;
					border-radius: 4px;
				}
				QMenu::item:selected {
					background-color: #f0f0f0;
				}
				QMenu::item:pressed {
					background-color: #009faa;
					color: #ffffff;
				}
				QMenu::separator {
					height: 1px;
					background-color: #e0e0e0;
					margin: 4px 8px;
				}
			""")
	
	def _start_screen_color_picker(self):
		"""从托盘启动屏幕取色"""
		if not self.core or not self.core.plugin_manager:
			self._show_tray_warning("核心服务未初始化")
			return
		
		plugin = self.core.plugin_manager.get_plugin("color_palette")
		if not plugin:
			self._show_tray_warning("调色板插件未加载")
			return
		
		try:
			if plugin._widget is None:
				plugin.get_widget()
			if plugin._widget:
				plugin._widget.start_color_picker()
		except Exception as e:
			self.core.logger.error(f"Failed to start color picker: {e}")
			self._show_tray_warning("启动取色器失败")
	
	def _show_tray_warning(self, message: str) -> None:
		"""显示托盘警告消息"""
		try:
			self.tray_icon.showMessage(
				"FluTool",
				message,
				QSystemTrayIcon.Warning,
				2000
			)
		except Exception:
			pass
	
	def _on_tray_activated(self, reason) -> None:
		if reason == QSystemTrayIcon.Trigger:
			if self.isVisible():
				self.hide()
			else:
				self.show_and_activate()
		elif reason == QSystemTrayIcon.MiddleClick:
			self._start_screen_color_picker()
	
	def show_and_activate(self) -> None:
		self.show()
		self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
		self.activateWindow()
		self.raise_()
	
	def _show_translator_window(self) -> None:
		"""显示翻译窗口"""
		try:
			from .translator_window import TranslatorWindow
			if not hasattr(self, '_translator_window') or self._translator_window is None:
				self._translator_window = TranslatorWindow()
			self._translator_window.show()
			self._translator_window.raise_()
			self._translator_window.activateWindow()
		except ImportError as e:
			self.core.logger.error(f"Failed to import TranslatorWindow: {e}")
		except Exception as e:
			self.core.logger.error(f"Failed to show translator window: {e}")
	
	def _toggle_theme(self) -> None:
		from qfluentwidgets import qconfig
		if getattr(self, "_theme_switching", False):
			return

		self._theme_switching = True
		self._theme_btn.setEnabled(False)
		target_theme = Theme.LIGHT if qconfig.theme == Theme.DARK else Theme.DARK
		target_name = "浅色" if target_theme == Theme.LIGHT else "深色"

		InfoBar.info(
			title="正在切换主题",
			content=f"正在应用{target_name}主题...",
			orient=Qt.Horizontal,
			isClosable=False,
			position=InfoBarPosition.TOP,
			duration=1200,
			parent=self
		)
		QTimer.singleShot(0, lambda theme=target_theme: self._apply_theme_change(theme))

	def _apply_theme_change(self, theme: Theme) -> None:
		"""延迟执行主题切换，让提示先完成绘制。"""
		from qfluentwidgets import qconfig
		try:
			qconfig.themeChangedFinished.connect(self._finish_theme_change)
			setTheme(theme)
		except Exception as e:
			self.core.logger.error(f"Failed to switch theme: {e}")
			self._finish_theme_change()

	def _finish_theme_change(self) -> None:
		from qfluentwidgets import qconfig
		try:
			qconfig.themeChangedFinished.disconnect(self._finish_theme_change)
		except TypeError:
			pass
		self._theme_switching = False
		self._theme_btn.setEnabled(True)
	
	def _on_global_search(self) -> None:
		if not self.core or not self.core.search_manager:
			return
		
		try:
			dialog = GlobalSearchDialog(self.core.search_manager, self)
			dialog.result_selected.connect(self._on_search_result_selected)
			dialog.show()
		except Exception as e:
			self.core.logger.error(f"Failed to show global search: {e}")

	def _on_search_result_selected(self, result) -> None:
		if result is None:
			return
		
		plugin_id = getattr(result, 'plugin_id', None)
		if not plugin_id:
			return
		
		if plugin_id in self._plugin_containers:
			self.switchTo(self._plugin_containers[plugin_id])
			action = getattr(result, 'action', None)
			if action and callable(action):
				try:
					action()
				except Exception as e:
					self.core.logger.error(f"Failed to execute search result action: {e}")
	
	def _on_real_close(self) -> None:
		self.real_close()
		QApplication.instance().quit()
	
	def addSubInterface(self, interface: QWidget, icon, text: str,
	                    position=None, parent=None, isTransparent=False):
		if not interface.objectName():
			raise ValueError("The object name of `interface` can't be empty string.")
		
		interface.setProperty("isStackedTransparent", isTransparent)
		self.stackedWidget.addWidget(interface)
		
		routeKey = interface.objectName()
		self.navigationInterface.addItem(
			routeKey=routeKey,
			icon=icon,
			text=text,
			onClick=lambda: self.switchTo(interface),
			position=position,
		)
		
		if self.stackedWidget.count() == 1:
			self.navigationInterface.setCurrentItem(routeKey)
		
		self._update_stacked_background()
	
	def removeInterface(self, interface, isDelete=False):
		self.navigationInterface.removeItem(interface.objectName())
		self.stackedWidget.removeWidget(interface)
		interface.hide()
		if isDelete:
			interface.deleteLater()
	
	def switchTo(self, interface: QWidget):
		self.stackedWidget.setCurrentWidget(interface, popOut=False)
	
	def _on_current_interface_changed(self, index: int):
		widget = self.stackedWidget.widget(index)
		if widget:
			self.navigationInterface.setCurrentItem(widget.objectName())
			self._update_stacked_background()
	
	def _update_stacked_background(self):
		widget = self.stackedWidget.currentWidget()
		if not widget:
			return
		isTransparent = widget.property("isStackedTransparent")
		if bool(self.stackedWidget.property("isTransparent")) == isTransparent:
			return
		self.stackedWidget.setProperty("isTransparent", isTransparent)
		self.stackedWidget.setStyle(QApplication.style())
	
	def paintEvent(self, e):
		super().paintEvent(e)
		painter = QPainter(self)
		painter.setPen(Qt.NoPen)
		painter.setBrush(self._darkBackgroundColor if isDarkTheme() else self._lightBackgroundColor)
		painter.drawRect(self.rect())
	
	def resizeEvent(self, e) -> None:
		nav_width = self.navigationInterface.width()
		self.titleBar.move(nav_width, 0)
		self.titleBar.resize(self.width() - nav_width, self.titleBar.height())
		self._content_widget.setGeometry(nav_width, 0, self.width() - nav_width, self.height())


class MainWindow(PushFluentWindow):
	"""
	主窗口 - 支持插件懒加载

	使用容器布局模式：插件 widget 被添加到容器的布局中，
	避免直接操作 stackedWidget 导致导航关联断裂。
	"""
	
	def __init__(self, core):
		super().__init__()
		if core is None:
			raise ValueError("Core instance cannot be None")
		self.core = core
		self.setWindowTitle("FluTool")
		self.resize(1100, 730)
		self._center_window()
		
		self._plugin_host = PluginHost(core)
		self._plugin_containers = self._plugin_host.plugin_containers
		self._plugin_widgets = self._plugin_host.plugin_widgets
		self._plugin_initialized = self._plugin_host.plugin_initialized
		
		try:
			self._setup_home_page()
			self._setup_more_menu_page()
			self._setup_settings_interface()
			self._apply_nav_expanded()
			self.navigationInterface.moreClicked.connect(self._on_more_clicked)
			self.stackedWidget.currentChanged.connect(self._on_page_changed)
		except Exception as e:
			core.logger.error(f"Failed to setup main window: {e}")
	
	def _center_window(self) -> None:
		screen = QApplication.primaryScreen()
		if screen:
			geo = screen.availableGeometry()
			self.move((geo.width() - self.width()) // 2, (geo.height() - self.height()) // 2)
	
	def _setup_home_page(self) -> None:
		home = QWidget()
		home.setObjectName("home")
		
		main_layout = QVBoxLayout(home)
		main_layout.setAlignment(Qt.AlignTop)
		main_layout.setSpacing(0)
		main_layout.setContentsMargins(0, 0, 0, 0)
		
		header_widget = QWidget()
		header_layout = QVBoxLayout(header_widget)
		header_layout.setContentsMargins(30, 30, 30, 20)
		header_layout.setSpacing(8)
		
		title_layout = QHBoxLayout()
		title_layout.setSpacing(12)
		
		logo_path = get_resource_path("logo.ico")
		if logo_path.exists():
			logo_label = QLabel()
			logo_pixmap = QPixmap(str(logo_path))
			logo_label.setPixmap(logo_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
			title_layout.addWidget(logo_label)
		
		title = StrongBodyLabel("FluTool")
		title_layout.addWidget(title)
		
		version = CaptionLabel("v0.1.0")
		title_layout.addWidget(version)
		title_layout.addStretch()
		
		header_layout.addLayout(title_layout)
		
		desc = SubtitleLabel("一款基于 PyQt5 的 Fluent Design 风格工具集")
		header_layout.addWidget(desc)
		
		main_layout.addWidget(header_widget)
		
		scroll = QScrollArea()
		scroll.setWidgetResizable(True)
		scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		scroll.setFrameShape(QScrollArea.NoFrame)
		scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
		scroll.viewport().setStyleSheet("background: transparent; border: none;")
		
		content_widget = QWidget()
		content_layout = QVBoxLayout(content_widget)
		content_layout.setContentsMargins(30, 10, 30, 30)
		content_layout.setSpacing(16)
		
		menu_items = [
			{"icon": FIF.INFO, "title": "关于", "desc": "查看应用信息、作者、许可证等", "action": self._show_about},
			{"icon": FIF.UPDATE, "title": "检查更新", "desc": "检查是否有新版本可用", "action": self._show_check_update},
			{"icon": FIF.DOCUMENT, "title": "使用文档", "desc": "查看功能说明和使用指南", "action": self._show_plugin_docs},
			{"icon": FIF.FEEDBACK, "title": "问题反馈", "desc": "报告 Bug 或提出建议", "action": self._show_feedback},
			{"icon": FIF.CODE, "title": "源代码", "desc": "访问 GitHub 仓库", "action": self._show_source_code},
		]
		
		for item in menu_items:
			card = self._create_menu_card(item["icon"], item["title"], item["desc"], item.get("action"))
			content_layout.addWidget(card)
		
		content_layout.addStretch()
		
		scroll.setWidget(content_widget)
		main_layout.addWidget(scroll, 1)
		
		self.addSubInterface(home, FIF.HOME, "首页")
	
	def _show_about(self) -> None:
		"""显示关于界面"""
		if not hasattr(self, '_about_interface'):
			self._about_interface = AboutInterface(self)
			self._about_interface.setObjectName("about")
			self._about_interface.backClicked.connect(self._on_interface_back)
			self.addSubInterface(self._about_interface, FIF.INFO, "关于")
		self.switchTo(self._about_interface)
	
	def _show_check_update(self) -> None:
		"""显示检查更新界面"""
		if not hasattr(self, '_check_update_interface'):
			self._check_update_interface = CheckUpdateInterface(self)
			self._check_update_interface.setObjectName("checkUpdate")
			self._check_update_interface.backClicked.connect(self._on_interface_back)
			self.addSubInterface(self._check_update_interface, FIF.UPDATE, "检查更新")
		self.switchTo(self._check_update_interface)
	
	def _show_feedback(self) -> None:
		"""显示问题反馈界面"""
		if not hasattr(self, '_feedback_interface'):
			self._feedback_interface = FeedbackInterface(self)
			self._feedback_interface.setObjectName("feedback")
			self._feedback_interface.backClicked.connect(self._on_interface_back)
			self.addSubInterface(self._feedback_interface, FIF.FEEDBACK, "问题反馈")
		self.switchTo(self._feedback_interface)
	
	def _show_source_code(self) -> None:
		"""显示源代码提示"""
		MessageBox("待开源", "FluTool 项目即将开源，敬请期待！\n\n开源后将在 GitHub 上发布源代码。", self).exec_()
	
	def _on_interface_back(self) -> None:
		"""从子界面返回首页"""
		home_widget = self.findChild(QWidget, "home")
		if home_widget:
			self.switchTo(home_widget)
	
	def _show_plugin_docs(self) -> None:
		"""显示插件使用文档"""
		if not hasattr(self, '_plugin_docs_interface'):
			self._plugin_docs_interface = PluginDocsInterface(self)
			self._plugin_docs_interface.setObjectName("pluginDocs")
			self._plugin_docs_interface.cardClicked.connect(self._on_plugin_doc_card_clicked)
			self._plugin_docs_interface.backClicked.connect(self._on_interface_back)
			self.addSubInterface(self._plugin_docs_interface, FIF.DOCUMENT, "使用文档")
		self.switchTo(self._plugin_docs_interface)
	
	def _on_plugin_doc_card_clicked(self, plugin_id: str) -> None:
		"""点击插件文档卡片跳转到对应插件"""
		if plugin_id in self._plugin_containers:
			self.switchTo(self._plugin_containers[plugin_id])
	
	def _create_menu_card(self, icon, title: str, desc: str, action=None) -> QWidget:
		"""创建菜单卡片"""
		card = QFrame()
		card.setObjectName("homeMenuCard")
		card.setFixedHeight(80)
		card.setCursor(Qt.PointingHandCursor)
		card._action = action
		card.mousePressEvent = lambda e: self._on_menu_card_clicked(e, action) if action else None
		
		layout = QHBoxLayout(card)
		layout.setContentsMargins(20, 15, 20, 15)
		layout.setSpacing(16)
		
		icon_btn = TransparentToolButton(icon, card)
		icon_btn.setFixedSize(48, 48)
		icon_btn.setIconSize(QSize(24, 24))
		layout.addWidget(icon_btn)
		
		text_widget = QWidget(card)
		text_layout = QVBoxLayout(text_widget)
		text_layout.setContentsMargins(0, 0, 0, 0)
		text_layout.setSpacing(4)
		
		title_label = BodyLabel(title)
		text_layout.addWidget(title_label)
		
		desc_label = CaptionLabel(desc)
		text_layout.addWidget(desc_label)
		
		layout.addWidget(text_widget, 1)
		
		arrow = TransparentToolButton(FIF.CHEVRON_RIGHT, card)
		arrow.setFixedSize(32, 32)
		arrow.setIconSize(QSize(14, 14))
		layout.addWidget(arrow)
		
		self._apply_menu_card_style(card, title_label, desc_label, arrow)
		qconfig.themeChangedFinished.connect(
			lambda: QTimer.singleShot(0, lambda: self._apply_menu_card_style(card, title_label, desc_label, arrow))
		)
		
		return card
	
	def _on_menu_card_clicked(self, event, action) -> None:
		"""菜单卡片点击事件"""
		if event.button() == Qt.LeftButton and action:
			action()
	
	def _apply_menu_card_style(self, card: QFrame, title_label: BodyLabel, desc_label: CaptionLabel, arrow: TransparentToolButton) -> None:
		"""应用菜单卡片样式"""
		dark = isDarkTheme()
		if dark:
			card.setStyleSheet("""
				QFrame#homeMenuCard {
					background-color: #2d2d2d;
					border-radius: 8px;
					border: 1px solid #3d3d3d;
				}
				QFrame#homeMenuCard:hover {
					background-color: #3d3d3d;
					border: 1px solid #5d5d5d;
				}
			""")
		else:
			card.setStyleSheet("""
				QFrame#homeMenuCard {
					background-color: #ffffff;
					border-radius: 8px;
					border: 1px solid #e0e0e0;
				}
				QFrame#homeMenuCard:hover {
					background-color: #f5f5f5;
					border: 1px solid #d0d0d0;
				}
			""")
	
	def _setup_settings_interface(self) -> None:
		self.settings_interface = SettingsInterface(self.core)
		self.settings_interface.setObjectName("settings")
		self.addSubInterface(
			self.settings_interface, FIF.SETTING, "设置",
			position="bottom"
		)
	
	def _setup_more_menu_page(self) -> None:
		self._more_menu = MoreMenu(self)
		self._more_menu.itemClicked.connect(self._on_more_item_clicked)
	
	def _on_more_clicked(self) -> None:
		overflow_items = self.navigationInterface.getOverflowItems()
		self._more_menu.clearItems()
		for item in overflow_items:
			self._more_menu.addItem(item['routeKey'], item['icon'], item['text'])
		
		# 设置项目后再计算位置
		self._more_menu.show()
		menu_height = self._more_menu.height()
		self._more_menu.hide()
		
		# 计算菜单位置 - 在更多按钮上方，与侧边栏底部对齐
		nav_global = self.navigationInterface.mapToGlobal(QPoint(0, 0))
		
		pos = QPoint(
			nav_global.x() + self.navigationInterface.width(),
			nav_global.y() + self.navigationInterface.height() - menu_height
		)
		self._more_menu.exec_(pos)
	
	def _on_more_item_clicked(self, routeKey: str) -> None:
		if routeKey.startswith("container_"):
			plugin_id = routeKey.replace("container_", "")
			if plugin_id in self._plugin_containers:
				self.switchTo(self._plugin_containers[plugin_id])
		elif routeKey == "home":
			self.switchTo(self.findChild(QWidget, "home"))
		elif routeKey == "settings":
			self.switchTo(self.settings_interface)
	
	def _apply_nav_expanded(self) -> None:
		if self.core.config.nav_expanded.value:
			self.navigationInterface.expand(useAni=False)
		else:
			self.navigationInterface.collapse(useAni=False)
	
	def register_plugin(self, plugin_id: str, icon, name: str) -> None:
		container = self._plugin_host.create_container(plugin_id)
		self.addSubInterface(container, icon, name)
	
	def load_first_plugin(self) -> None:
		if not self._plugin_containers:
			return
		plugin_id = list(self._plugin_containers.keys())[0]
		self._init_plugin_widget(plugin_id)
	
	def _init_plugin_widget(self, plugin_id: str) -> bool:
		return self._plugin_host.init_plugin_widget(plugin_id)
	
	def _on_page_changed(self, index: int) -> None:
		if index < 0:
			return
		
		widget = self.stackedWidget.widget(index)
		if widget is None:
			return
		
		object_name = widget.objectName()
		if not object_name:
			return
		
		if object_name.startswith("container_"):
			plugin_id = object_name.replace("container_", "")
			
			if not self._plugin_initialized.get(plugin_id, False):
				self._init_plugin_widget(plugin_id)
			
			QTimer.singleShot(50, lambda pid=plugin_id: self._load_plugin_data(pid))

	def _load_plugin_data(self, plugin_id: str) -> None:
		self._plugin_host.load_plugin_data(plugin_id)

	def suspend_plugin_io(self) -> None:
		"""暂停已加载插件交互，避免恢复期间继续写入。"""
		self._plugin_host.suspend_loaded_plugins()

	def resume_plugin_io(self) -> None:
		"""恢复已加载插件交互。"""
		self._plugin_host.resume_loaded_plugins()

	def reload_loaded_plugins(self) -> None:
		"""恢复后统一刷新所有已加载插件。"""
		self._plugin_host.reload_loaded_plugins()
	
	def add_plugin(self, plugin) -> None:
		plugin_id = plugin.get_id()
		container = self._plugin_host.attach_loaded_plugin(plugin)
		icon = plugin.get_icon() if plugin.get_icon() else FIF.DOCUMENT
		self.addSubInterface(container, icon, plugin.get_name())
	
	def close_plugin(self, plugin_id: str) -> None:
		if not plugin_id:
			return
		
		container = self._plugin_containers.get(plugin_id)
		if container:
			try:
				self.stackedWidget.removeWidget(container)
				container.setParent(None)
			except Exception as e:
				self.core.logger.error(f"Failed to remove container: {e}")
		
		self._plugin_host.shutdown_plugin(plugin_id)
		self.navigationInterface.removeItem(plugin_id)
	
	def closeEvent(self, event) -> None:
		event.ignore()
		self.hide()
		self.tray_icon.showMessage(
			"FluTool",
			"程序已最小化到系统托盘\n单击托盘图标恢复窗口",
			QSystemTrayIcon.Information,
			2000
		)
	
	def real_close(self) -> None:
		for plugin_id in list(self._plugin_initialized.keys()):
			if self._plugin_initialized[plugin_id]:
				plugin = self.core.plugin_manager.get_plugin(plugin_id)
				if plugin:
					try:
						plugin.shutdown()
					except Exception as e:
						self.core.logger.error(f"Plugin shutdown error: {e}")
		
		try:
			self.tray_icon.hide()
		except Exception as e:
			self.core.logger.error(f"Failed to hide tray icon: {e}")
		
		try:
			super().close()
		except Exception as e:
			self.core.logger.error(f"Failed to close window: {e}")
