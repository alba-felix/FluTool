"""开发工具插件 - 底层模板"""

from typing import Dict, Any, List, Type
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QApplication, QStackedWidget,
    QFrame
)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QCursor
from qfluentwidgets import (
    isDarkTheme, FluentIcon as FIF,
    PushButton, TransparentToolButton, qconfig
)

from core import PluginInterface
from plugins.text_tools.page_interface import TabPageInterface
from .cron_tool import CronToolPage
from .deepseek_tool import DeepSeekToolPage


class OverflowPopup(QWidget):
    """溢出标签页弹出窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._click_callback = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedWidth(300)
        self.setMaximumHeight(600)
        
        self._main_frame = QFrame(self)
        self._main_frame.setObjectName("overflowMainFrame")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_frame)
        
        frame_layout = QVBoxLayout(self._main_frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(2)
        
        scroll_area = QScrollArea(self._main_frame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        frame_layout.addWidget(scroll_area)
        
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        scroll_area.setWidget(self._list_widget)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_style()

    def _apply_style(self) -> None:
        if isDarkTheme():
            self._main_frame.setStyleSheet("""
                QFrame#overflowMainFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self._main_frame.setStyleSheet("""
                QFrame#overflowMainFrame {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """)

    def show_tabs(self, tabs: List[Dict[str, Any]], on_click_callback) -> None:
        self._click_callback = on_click_callback
        
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for tab in tabs:
            btn = PushButton(tab['text'], self._list_widget)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, t=tab: self._on_tab_click(t))
            self._list_layout.addWidget(btn)
        
        self.adjustSize()

    def _on_tab_click(self, tab: Dict[str, Any]) -> None:
        self.hide()
        if self._click_callback:
            self._click_callback(tab)

    def show_at(self, global_pos: QPoint, max_height: int) -> None:
        self.setMaximumHeight(min(max_height, 600))
        self.adjustSize()
        
        x = global_pos.x() - self.width()
        y = global_pos.y()
        
        screen = QApplication.screenAt(global_pos)
        if screen:
            screen_rect = screen.availableGeometry()
            if x < screen_rect.left():
                x = screen_rect.left()
            if y + self.height() > screen_rect.bottom():
                y = screen_rect.bottom() - self.height()
        
        self.move(x, y)
        self.show()
        self.setFocus()


class CustomTabBar(QWidget):
    """自定义标签页栏"""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: List[Dict[str, Any]] = []
        self._current_index = 0
        self._visible_count = 0
        self._overflow_popup: Optional[OverflowPopup] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(46)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        self._tab_container = QWidget(self)
        self._tab_layout = QHBoxLayout(self._tab_container)
        self._tab_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_layout.setSpacing(2)
        self._tab_layout.addStretch()
        layout.addWidget(self._tab_container, 1)
        
        self._overflow_btn = TransparentToolButton(FIF.MORE, self)
        self._overflow_btn.setFixedSize(36, 36)
        self._overflow_btn.setToolTip("更多标签页")
        self._overflow_btn.clicked.connect(self._show_overflow)
        self._overflow_btn.hide()
        layout.addWidget(self._overflow_btn)

    def addTab(self, page_id: str, text: str) -> int:
        """添加标签页，返回页面索引"""
        page_index = len(self._tabs)
        self._tabs.append({
            'page_id': page_id,
            'text': text,
            'widget_index': page_index,
            'button': None
        })
        self._update_visible_tabs()
        return page_index

    def _update_visible_tabs(self) -> None:
        while self._tab_layout.count() > 1:
            item = self._tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        total_width = 0
        tab_buttons = []
        
        for i, tab in enumerate(self._tabs):
            btn = PushButton(tab['text'], self)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(64)
            btn.setMaximumWidth(150)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_click(idx))
            
            if i == self._current_index:
                btn.setChecked(True)
            
            self._tab_layout.insertWidget(i, btn)
            btn.adjustSize()
            
            tab_width = btn.width() + 2
            total_width += tab_width
            tab_buttons.append((i, tab, btn, tab_width))
        
        available_width = self.width() - 50
        need_overflow = total_width > available_width
        
        if need_overflow:
            current_width = 0
            self._visible_count = 0
            
            for i, tab, btn, tab_width in tab_buttons:
                if current_width + tab_width <= available_width - 50:
                    current_width += tab_width
                    self._visible_count += 1
                    tab['button'] = btn
                else:
                    self._tab_layout.removeWidget(btn)
                    btn.deleteLater()
                    tab['button'] = None
        else:
            self._visible_count = len(self._tabs)
            for i, tab, btn, _ in tab_buttons:
                tab['button'] = btn
        
        if len(self._tabs) > self._visible_count:
            self._overflow_btn.show()
        else:
            self._overflow_btn.hide()

    def _on_tab_click(self, index: int) -> None:
        self.setCurrentIndex(index)

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._current_index = index
            for i, tab in enumerate(self._tabs):
                if tab['button']:
                    tab['button'].setChecked(i == index)
            widget_index = self._tabs[index]['widget_index']
            self.currentChanged.emit(widget_index)

    def _show_overflow(self) -> None:
        hidden_tabs = self._tabs[self._visible_count:]
        if not hidden_tabs:
            return
        
        if self._overflow_popup is None:
            self._overflow_popup = OverflowPopup()
        
        main_window = self.window()
        max_height = main_window.height() - 100 if main_window else 400
        btn_pos = self._overflow_btn.mapToGlobal(QPoint(0, self._overflow_btn.height()))
        
        self._overflow_popup.show_tabs(hidden_tabs, self._on_overflow_tab_click)
        self._overflow_popup.show_at(btn_pos, max_height)

    def _on_overflow_tab_click(self, tab: Dict[str, Any]) -> None:
        clicked_index = self._tabs.index(tab)
        
        if self._visible_count > 0 and clicked_index >= self._visible_count:
            last_visible_index = self._visible_count - 1
            self._tabs[clicked_index], self._tabs[last_visible_index] = \
                self._tabs[last_visible_index], self._tabs[clicked_index]
            self._current_index = last_visible_index
        else:
            self._current_index = clicked_index
        
        self._update_visible_tabs()
        widget_index = self._tabs[self._current_index]['widget_index']
        self.currentChanged.emit(widget_index)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_visible_tabs)


class TabManager:
    """标签页管理器 - 管理所有标签页的注册和创建"""

    def __init__(self):
        self._pages: List[Type[TabPageInterface]] = []

    def register(self, page_class: Type[TabPageInterface]) -> None:
        """注册标签页"""
        self._pages.append(page_class)

    def get_pages(self) -> List[Type[TabPageInterface]]:
        """获取所有已注册的标签页"""
        return self._pages.copy()

    def create_all(self, parent=None) -> List[QWidget]:
        """创建所有标签页内容"""
        return [page.create(parent) for page in self._pages]


class DevToolsWidget(QWidget):
    """开发工具主界面"""

    PLUGIN_ID = "dev_tools"

    def __init__(self, core, tab_manager: TabManager, parent=None):
        super().__init__(parent)
        self.core = core
        self._tab_manager = tab_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setObjectName("devToolsView")
        self.setStyleSheet("QWidget#devToolsView { background-color: transparent; }")

        self.tab_bar = CustomTabBar(self)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_bar)

        # 标签页下方水平分隔线
        self._separator = QFrame(self)
        self._separator.setFrameShape(QFrame.HLine)
        self._separator.setFixedHeight(1)
        self._separator.setObjectName("tabSeparator")
        layout.addWidget(self._separator)

        # 创建滚动区域包裹 stacked_widget，启用双向滚动但不显示滚动条
        from PyQt5.QtWidgets import QScrollArea
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll_area.viewport().setStyleSheet("background: transparent; border: none;")

        # 创建容器放置 stacked_widget
        self._scroll_container = QWidget()
        self._scroll_container_layout = QVBoxLayout(self._scroll_container)
        self._scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_container_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget(self._scroll_container)
        self._scroll_container_layout.addWidget(self.stacked_widget)

        self._scroll_area.setWidget(self._scroll_container)
        layout.addWidget(self._scroll_area)

        self._init_tabs()
        self._apply_separator_style()
        
        # 监听主题变化
        qconfig.themeChangedFinished.connect(lambda: QTimer.singleShot(0, self._apply_separator_style))

    def _on_tab_changed(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)

    def _apply_separator_style(self) -> None:
        """应用分隔线样式"""
        if isDarkTheme():
            self._separator.setStyleSheet("QFrame#tabSeparator { background-color: #3d3d3d; border: none; }")
        else:
            self._separator.setStyleSheet("QFrame#tabSeparator { background-color: #e0e0e0; border: none; }")

    def _init_tabs(self) -> None:
        """初始化所有已注册的标签页"""
        pages = self._tab_manager.get_pages()
        widgets = self._tab_manager.create_all(self)
        
        for page_class, widget in zip(pages, widgets):
            self.tab_bar.addTab(page_class.page_id, page_class.page_name)
            widget.setStyleSheet("background-color: transparent;")
            self.stacked_widget.addWidget(widget)
        
        if widgets:
            self.stacked_widget.setCurrentIndex(0)


class Plugin(PluginInterface):
    """开发工具插件 - 底层模板"""

    PLUGIN_ID = "dev_tools"
    PLUGIN_NAME = "开发工具"
    PLUGIN_ICON = FIF.DEVELOPER_TOOLS
    PLUGIN_PRIORITY = 8.3

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

        self._tab_manager = TabManager()
        # 在这里注册开发工具的标签页
        self._tab_manager.register(CronToolPage)
        self._tab_manager.register(DeepSeekToolPage)

        self._widget = None

    def _create_widget(self, parent=None) -> QWidget:
        if self._widget is None:
            self._widget = DevToolsWidget(self.core, self._tab_manager, parent)
        return self._widget

    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        pass
