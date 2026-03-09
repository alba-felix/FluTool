from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon as FIF,
    Theme, setTheme, TransparentToolButton, setCustomStyleSheet,
    StrongBodyLabel, BodyLabel, CaptionLabel, HyperlinkLabel, MessageBox
)
from .settings_interface import SettingsInterface
from core.utils import get_resource_path


class PushFluentWindow(FluentWindow):
    """挤压式侧边栏窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_push_navigation()
        self._setup_title_bar()
        self._setup_tray()
    
    def _init_push_navigation(self) -> None:
        self.navigationInterface.setMinimumExpandWidth(0)
        self.navigationInterface.panel.setMinimumExpandWidth(0)
        self.navigationInterface.panel.expandWidth = 125

    def _setup_title_bar(self) -> None:
        self.titleBar.setFixedHeight(38)
        self.titleBar.titleLabel.hide()
        
        self.titleBar.closeBtn.hide()
        
        self._theme_btn = TransparentToolButton(FIF.CONSTRACT, self.titleBar)
        self._theme_btn.setFixedSize(32, 32)
        self._theme_btn.setIconSize(QSize(14, 14))
        self._theme_btn.setToolTip("<p>切换主题</p>")
        self._theme_btn.clicked.connect(self._toggle_theme)
        self.titleBar.hBoxLayout.insertWidget(2, self._theme_btn, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.titleBar.hBoxLayout.insertSpacing(3, 8)
        
        self._quit_btn = TransparentToolButton(FIF.POWER_BUTTON, self.titleBar)
        self._quit_btn.setFixedSize(46, 32)
        self._quit_btn.setIconSize(QSize(14, 14))
        self._quit_btn.setToolTip("<p>退出程序</p>")
        self._quit_btn.clicked.connect(self._on_real_close)
        self.titleBar.hBoxLayout.addWidget(self._quit_btn, 0, Qt.AlignRight | Qt.AlignVCenter)

    def _setup_tray(self) -> None:
        """设置系统托盘"""
        logo_path = get_resource_path("logo.ico")
        if logo_path.exists():
            tray_icon = QIcon(str(logo_path))
        else:
            tray_icon = QIcon()
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(tray_icon)
        self.tray_icon.setToolTip("FluTool")
        
        tray_menu = QMenu(self)
        
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_and_activate)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self._on_real_close)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def _on_tray_activated(self, reason) -> None:
        """托盘图标激活事件"""
        # Trigger: 左键单击 | DoubleClick: 左键双击
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_and_activate()
    
    def show_and_activate(self) -> None:
        """显示并激活窗口"""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.raise_()
    
    def _toggle_theme(self) -> None:
        from qfluentwidgets import qconfig
        if qconfig.theme == Theme.DARK:
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)
    
    def _on_real_close(self) -> None:
        """真正关闭应用（无弹窗直接关闭）"""
        self.real_close()
        QApplication.instance().quit()
        
    def resizeEvent(self, e) -> None:
        nav_width = self.navigationInterface.width()
        self.titleBar.move(nav_width, 0)
        self.titleBar.resize(self.width() - nav_width, self.titleBar.height())


class MainWindow(PushFluentWindow):
    """
    主窗口 - 支持插件懒加载
    
    使用容器布局模式：插件 widget 被添加到容器的布局中，
    避免直接操作 stackedWidget 导致导航关联断裂。
    """
    
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.setWindowTitle("FluTool")
        self.resize(1000, 700)
        self._center_window()
        
        self.stackedWidget.setAnimationEnabled(False)
        
        self._plugin_containers = {}
        self._plugin_widgets = {}
        self._plugin_initialized = {}
        
        self._setup_home_page()
        self._setup_settings_interface()
        self._apply_nav_expanded()
        self.stackedWidget.currentChanged.connect(self._on_page_changed)

    def _center_window(self) -> None:
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move((geo.width() - self.width()) // 2, (geo.height() - self.height()) // 2)

    def _setup_home_page(self) -> None:
        """设置首页（关于页面）"""
        home = QWidget()
        home.setObjectName("home")
        layout = QVBoxLayout(home)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        
        logo_path = get_resource_path("logo.ico")
        if logo_path.exists():
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(logo_pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        title = StrongBodyLabel("FluTool")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px;")
        layout.addWidget(title)
        
        version = CaptionLabel("版本 0.1.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)
        
        desc = BodyLabel("一款基于 PyQt5 的 Fluent Design 风格工具集")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        author_label = BodyLabel("作者:alba-felix ")
        author_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(author_label)
        
        github_container = QWidget()
        github_layout = QVBoxLayout(github_container)
        github_layout.setContentsMargins(0, 0, 0, 0)
        github_layout.setAlignment(Qt.AlignCenter)
        github_label = HyperlinkLabel("GitHub", "https://github.com")
        github_layout.addWidget(github_label)
        info_layout.addWidget(github_container)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        self.addSubInterface(home, FIF.HOME, "首页")

    def _setup_settings_interface(self) -> None:
        self.settings_interface = SettingsInterface(self.core)
        self.settings_interface.setObjectName("settings")
        self.addSubInterface(
            self.settings_interface, FIF.SETTING, "设置",
            position=NavigationItemPosition.BOTTOM
        )

    def _apply_nav_expanded(self) -> None:
        """应用导航栏展开配置"""
        if self.core.config.nav_expanded.value:
            self.navigationInterface.panel.expand()
        else:
            self.navigationInterface.panel.collapse()

    def register_plugin(self, plugin_id: str, icon, name: str) -> None:
        """
        注册插件导航项（延迟加载）
        创建容器 widget，实际插件 widget 在首次切换时创建
        """
        # 创建容器，使用布局以便后续添加插件 widget
        container = QWidget()
        container.setObjectName(f"container_{plugin_id}")
        container.setLayout(QVBoxLayout())
        container.layout().setContentsMargins(0, 0, 0, 0)
        
        self._plugin_containers[plugin_id] = container
        self._plugin_initialized[plugin_id] = False
        self.addSubInterface(container, icon, name)

    def load_first_plugin(self) -> None:
        """预加载第一个插件（可选）"""
        if not self._plugin_containers:
            return
        plugin_id = list(self._plugin_containers.keys())[0]
        self._init_plugin_widget(plugin_id)

    def _init_plugin_widget(self, plugin_id: str) -> bool:
        """
        工厂方法：创建插件界面并添加到容器
        
        Returns:
            是否成功创建
        """
        if self._plugin_initialized.get(plugin_id, False):
            return True
        
        plugin = self.core.plugin_manager.get_plugin(plugin_id)
        if not plugin:
            self.core.logger.error(f"Plugin not found: {plugin_id}")
            return False
        
        try:
            # 创建插件 widget
            widget = plugin.get_widget(self._plugin_containers[plugin_id])
            if widget is None:
                return False
            
            widget.setObjectName(plugin_id)
            
            # 添加到容器布局
            container = self._plugin_containers[plugin_id]
            container.layout().addWidget(widget)
            
            self._plugin_widgets[plugin_id] = widget
            self._plugin_initialized[plugin_id] = True
            
            self.core.logger.info(f"Plugin widget created: {plugin.get_name()}")
            return True
            
        except Exception as e:
            self.core.logger.error(f"Failed to create plugin widget {plugin_id}: {e}")
            return False

    def _on_page_changed(self, index: int) -> None:
        """页面切换事件 - 实现懒加载"""
        widget = self.stackedWidget.widget(index)
        if widget is None:
            return
        
        object_name = widget.objectName()
        
        # 检测是否是插件容器
        if object_name.startswith("container_"):
            plugin_id = object_name.replace("container_", "")
            
            if not self._plugin_initialized.get(plugin_id, False):
                # 延迟加载插件界面
                self._init_plugin_widget(plugin_id)
            
            # 异步加载数据
            QTimer.singleShot(50, lambda pid=plugin_id: self._load_plugin_data(pid))

    def _load_plugin_data(self, plugin_id: str) -> None:
        """异步加载插件数据"""
        plugin = self.core.plugin_manager.get_plugin(plugin_id)
        if plugin:
            try:
                plugin.load_data()
            except Exception as e:
                self.core.logger.error(f"Failed to load plugin data {plugin_id}: {e}")

    def add_plugin(self, plugin) -> None:
        """添加插件（立即加载界面）"""
        plugin_id = plugin.get_id()
        container = QWidget()
        container.setObjectName(f"container_{plugin_id}")
        container.setLayout(QVBoxLayout())
        container.layout().setContentsMargins(0, 0, 0, 0)
        
        qss = f"QWidget#{container.objectName()} {{ background-color: transparent; }}"
        setCustomStyleSheet(container, qss, qss)
        
        widget = plugin.get_widget(container)
        if widget:
            widget.setObjectName(plugin_id)
            container.layout().addWidget(widget)
            icon = plugin.get_icon() if plugin.get_icon() else FIF.DOCUMENT
            self.addSubInterface(container, icon, plugin.get_name())
            
            self._plugin_containers[plugin_id] = container
            self._plugin_widgets[plugin_id] = widget
            self._plugin_initialized[plugin_id] = True

    def close_plugin(self, plugin_id: str) -> None:
        """关闭并移除插件"""
        plugin = self.core.plugin_manager.get_plugin(plugin_id)
        if plugin:
            plugin.shutdown()
        
        container = self._plugin_containers.get(plugin_id)
        if container:
            self.stackedWidget.removeWidget(container)
            container.setParent(None)
        
        self._plugin_containers.pop(plugin_id, None)
        self._plugin_widgets.pop(plugin_id, None)
        self._plugin_initialized.pop(plugin_id, None)
        self.navigationInterface.removeItem(plugin_id)

    def closeEvent(self, event) -> None:
        """窗口关闭事件 - 最小化到托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "FluTool",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.Information,
            2000
        )
    
    def real_close(self) -> None:
        """真正关闭窗口"""
        for plugin_id in list(self._plugin_initialized.keys()):
            if self._plugin_initialized[plugin_id]:
                plugin = self.core.plugin_manager.get_plugin(plugin_id)
                if plugin:
                    plugin.shutdown()
        self.tray_icon.hide()
        super().close()
