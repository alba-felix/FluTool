import sys
import time
import traceback
from pathlib import Path
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtGui import QIcon, QColor
from qfluentwidgets import setThemeColor, setTheme, Theme, FluentIcon as FIF
from core.utils import get_resource_path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

_start_time = None
_server_name = "FluTool_Server"


def _fix_uac_drag_drop():
    """修复管理员权限下无法从资源管理器拖放文件的问题

    Windows UAC 安全机制阻止高完整性进程（管理员）接收中完整性进程（资源管理器）
    的拖放数据。通过 ChangeWindowMessageFilter 修改进程级消息过滤来解除此限制。
    """
    try:
        import ctypes

        user32 = ctypes.windll.user32
        ChangeWindowMessageFilter = user32.ChangeWindowMessageFilter
        ChangeWindowMessageFilter.argtypes = [ctypes.c_uint, ctypes.c_uint]
        ChangeWindowMessageFilter.restype = ctypes.c_bool

        MSGFLT_ADD = 1
        for msg in (0x0233, 0x004A, 0x0049):
            ChangeWindowMessageFilter(msg, MSGFLT_ADD)
    except Exception:
        pass


class SingleInstance(QObject):
    """单实例检测与激活"""

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

        try:
            from PyQt5.QtCore import QSharedMemory
            self._shared_memory = QSharedMemory(self.app_name)
            if self._shared_memory.attach():
                return True
            self._shared_memory.create(1)
            return False
        except Exception as e:
            print(f"[SingleInstance] Error checking instance: {e}")
            return False

    def activate_existing_instance(self) -> bool:
        """尝试激活已有实例"""
        if not self._is_frozen:
            return False

        try:
            self._socket = QLocalSocket()
            self._socket.connectToServer(_server_name)
            if self._socket.waitForConnected(50):
                self._socket.write(b"activate")
                self._socket.flush()
                self._socket.waitForBytesWritten(50)
                self._socket.disconnectFromServer()
                return True
        except Exception as e:
            print(f"[SingleInstance] Error activating instance: {e}")
        return False

    def start_server(self, on_activate_callback=None) -> bool:
        """启动本地服务器接收激活请求"""
        if not self._is_frozen:
            return True

        try:
            self._server = QLocalServer(self)
            if on_activate_callback:
                self._server.newConnection.connect(on_activate_callback)
            if not self._server.listen(_server_name):
                print(f"[SingleInstance] Cannot start server: {self._server.errorString()}")
                return False
            return True
        except Exception as e:
            print(f"[SingleInstance] Error starting server: {e}")
            return False

    def stop_server(self) -> None:
        """停止本地服务器"""
        if self._server:
            try:
                self._server.close()
            except Exception as e:
                print(f"[SingleInstance] Error stopping server: {e}")


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


def show_error_and_exit(title: str, message: str, exit_code: int = 1) -> int:
    """显示错误消息并退出"""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, title, message)
    except Exception:
        print(f"[ERROR] {title}: {message}")
    return exit_code


def main():
    global _start_time
    _start_time = time.time()

    _fix_uac_drag_drop()
    
    # 单实例检测
    try:
        single_instance = SingleInstance()
        if single_instance.is_running():
            print("FluTool is already running, trying to activate...")
            if single_instance.activate_existing_instance():
                print("Activation request sent to existing instance")
            else:
                print("Cannot activate existing instance")
            return 0
    except Exception as e:
        print(f"[main] Single instance check failed: {e}")
        # 继续运行，不因单例检测失败而退出
    
    # 初始化应用
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception as e:
        print(f"[main] High DPI setup failed: {e}")
    
    try:
        app = QApplication(sys.argv)
    except Exception as e:
        return show_error_and_exit("启动失败", f"无法创建应用程序: {e}")
    
    try:
        setThemeColor("#0078d4")
        setTheme(Theme.DARK)
    except Exception as e:
        print(f"[main] Theme setup failed: {e}")
    
    splash = create_splash()
    splash.show()
    app.processEvents()
    
    # 初始化核心
    core = None
    try:
        splash.showMessage("初始化核心...", Qt.AlignCenter | Qt.AlignBottom, QColor("#ffffff"))
        app.processEvents()
        
        from core.app_core import AppCore
        core = AppCore()
        core.initialize()
    except Exception as e:
        splash.hide()
        traceback.print_exc()
        return show_error_and_exit("初始化失败", f"核心服务初始化失败:\n{e}")
    
    # 创建主窗口
    window = None
    try:
        splash.showMessage("加载界面...", Qt.AlignCenter | Qt.AlignBottom, QColor("#ffffff"))
        app.processEvents()
        
        from ui.main_window import MainWindow
        window = MainWindow(core)
        core.main_window = window
        
        logo_path = get_resource_path("logo.ico")
        if logo_path.exists():
            window.setWindowIcon(QIcon(str(logo_path)))
    except Exception as e:
        splash.hide()
        traceback.print_exc()
        return show_error_and_exit("界面加载失败", f"无法创建主窗口:\n{e}")
    
    # 设置单实例激活回调
    def on_socket_connection():
        if not single_instance._server:
            return
        try:
            socket = single_instance._server.nextPendingConnection()
            if socket:
                socket.readyRead.connect(lambda: _on_socket_read(socket))
        except Exception as e:
            print(f"[main] Socket connection error: {e}")
    
    def _on_socket_read(socket):
        try:
            data = socket.readAll().data()
            if data == b"activate" and window:
                window.show_and_activate()
                socket.write(b"activated")
                socket.flush()
        except Exception as e:
            print(f"[main] Socket read error: {e}")
        finally:
            if socket:
                socket.deleteLater()
    
    if not single_instance.start_server(on_socket_connection):
        print("[main] Warning: Single instance server not started")
    
    # 加载插件
    loaded_count = 0
    failed_count = 0
    try:
        if getattr(sys, 'frozen', False):
            plugin_path = None
            discovered = core.plugin_manager.scan_builtin_plugins()
        else:
            plugin_path = project_root / "plugins"
            discovered = core.plugin_manager.scan_plugins(str(plugin_path))
        
        for plugin_id in discovered:
            try:
                plugin = core.plugin_manager.load_plugin(plugin_id)
                if plugin:
                    icon = plugin.get_icon() or FIF.DOCUMENT
                    name = plugin.get_name() or plugin_id
                    window.register_plugin(plugin_id, icon, name)
                    loaded_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                core.logger.error(f"Failed to register plugin {plugin_id}: {e}")
        
        if failed_count > 0:
            core.logger.warning(f"{failed_count} plugin(s) failed to load")
    except Exception as e:
        core.logger.error(f"Plugin loading failed: {e}")
    
    # 显示窗口
    try:
        window.show()
        splash.finish(window)
    except Exception as e:
        splash.hide()
        core.logger.error(f"Failed to show window: {e}")
        return show_error_and_exit("启动失败", f"无法显示主窗口: {e}")
    finally:
        splash.deleteLater()
    
    # 记录启动时间
    if _start_time:
        elapsed = (time.time() - _start_time) * 1000
        core.logger.info(f"Application started in {elapsed:.0f}ms, {loaded_count} plugins loaded")
    
    # 运行事件循环
    try:
        result = app.exec_()
    except Exception as e:
        core.logger.error(f"Application error: {e}")
        result = 1
    finally:
        single_instance.stop_server()
        if core:
            core.shutdown()
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--run-script":
        script_path = sys.argv[2]
        try:
            import runpy
            runpy.run_path(script_path, run_name="__main__")
        except Exception as e:
            print(f"[FluTool Script Runner] Error: {e}")
            traceback.print_exc()
        sys.exit(0)
    sys.exit(main())
