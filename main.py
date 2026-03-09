import sys
import time
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QIcon, QColor
from qfluentwidgets import setThemeColor, setTheme, Theme, FluentIcon as FIF
from core.utils import get_resource_path


project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

_start_time = None


class SingleInstance:
    """单实例检测"""
    
    def __init__(self, app_name: str = "FluTool"):
        self.app_name = app_name
        self._shared_memory = None
    
    def is_running(self) -> bool:
        """检测是否已有实例运行"""
        from PyQt5.QtCore import QSharedMemory
        self._shared_memory = QSharedMemory(self.app_name)
        if self._shared_memory.attach():
            return True
        self._shared_memory.create(1)
        return False


def create_splash():
    """创建启动画面"""
    splash = QSplashScreen()
    splash.setStyleSheet("""
        QSplashScreen {
            background-color: #1e1e1e;
        }
    """)
    splash.showMessage(
        "正在启动 FluTool...",
        Qt.AlignCenter | Qt.AlignBottom,
        QColor("#ffffff")
    )
    return splash


def main():
    global _start_time
    _start_time = time.time()
    
    single_instance = SingleInstance()
    if single_instance.is_running():
        print("FluTool 已在运行")
        return 0
    
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    setThemeColor("#0078d4")
    setTheme(Theme.DARK)
    splash = create_splash()
    splash.show()
    app.processEvents()
    from core.app_core import AppCore
    core = AppCore()
    core.initialize()
    splash.showMessage("加载界面...", Qt.AlignCenter | Qt.AlignBottom, QColor("#ffffff"))
    app.processEvents()
    from ui.main_window import MainWindow
    window = MainWindow(core)
    logo_path = get_resource_path("logo.ico")
    if logo_path.exists():
        window.setWindowIcon(QIcon(str(logo_path)))
    # 打包后插件路径
    if getattr(sys, 'frozen', False):
        plugin_path = None
        discovered = core.plugin_manager.scan_builtin_plugins()
    else:
        plugin_path = project_root / "plugins"
        discovered = core.plugin_manager.scan_plugins(str(plugin_path))
    for plugin_id in discovered:
        plugin = core.plugin_manager.load_plugin(plugin_id)
        if plugin:
            window.register_plugin(plugin_id, plugin.get_icon() or FIF.DOCUMENT, plugin.get_name())
    window.show()
    splash.finish(window)
    splash.deleteLater()
    # 记录启动完成时间（首页已显示）
    if _start_time:
        elapsed = (time.time() - _start_time) * 1000
        core.logger.info(f"应用启动完成，总耗时: {elapsed:.0f}ms")
    result = app.exec_()
    core.shutdown()
    return result


if __name__ == "__main__":
    sys.exit(main())
