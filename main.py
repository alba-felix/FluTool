import sys
import time
from pathlib import Path
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtGui import QIcon, QColor
from qfluentwidgets import setThemeColor, setTheme, Theme, FluentIcon as FIF
from core.utils import get_resource_path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

_start_time = None
_server_name = "FluTool_Server"


class SingleInstance(QObject):
    """单实例检测与激活

    开发模式：允许多实例运行，方便调试
    打包后：启用单例模式，防止重复启动
    """

    def __init__(self, app_name: str = "FluTool", parent=None):
        super().__init__(parent)
        self.app_name = app_name
        self._shared_memory = None
        self._socket = None
        self._server = None
        self._is_frozen = getattr(sys, 'frozen', False)

    def is_running(self) -> bool:
        """检测是否已有实例运行"""
        if not self._is_frozen:
            return False

        from PyQt5.QtCore import QSharedMemory
        self._shared_memory = QSharedMemory(self.app_name)
        if self._shared_memory.attach():
            return True
        self._shared_memory.create(1)
        return False

    def activate_existing_instance(self) -> bool:
        """尝试激活已有实例"""
        if not self._is_frozen:
            return False

        self._socket = QLocalSocket()
        self._socket.connectToServer(_server_name)
        if self._socket.waitForConnected(50):
            self._socket.write(b"activate")
            self._socket.flush()
            self._socket.waitForBytesWritten(50)
            self._socket.disconnectFromServer()
            return True
        return False

    def start_server(self, on_activate_callback=None) -> None:
        """启动本地服务器接收激活请求"""
        if not self._is_frozen:
            return

        self._server = QLocalServer(self)
        if on_activate_callback:
            self._server.newConnection.connect(on_activate_callback)
        if not self._server.listen(_server_name):
            print(f"无法启动本地服务器: {self._server.errorString()}")

    def stop_server(self) -> None:
        """停止本地服务器"""
        if self._server:
            self._server.close()


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
        print("FluTool 已在运行，尝试激活现有窗口...")
        if single_instance.activate_existing_instance():
            print("已发送激活请求到现有实例")
        else:
            print("无法激活现有实例")
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
    
    def on_socket_connection():
        socket = single_instance._server.nextPendingConnection()
        if socket:
            socket.readyRead.connect(lambda: _on_socket_read(socket))
    
    def _on_socket_read(socket):
        data = socket.readAll().data()
        if data == b"activate":
            window.show_and_activate()
            socket.write(b"activated")
            socket.flush()
            socket.deleteLater()
    
    single_instance.start_server(on_socket_connection)
    
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
    single_instance.stop_server()
    core.shutdown()
    return result


if __name__ == "__main__":
    sys.exit(main())
