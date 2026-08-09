"""
剪切板底层监听器
使用 Win32 GetClipboardSequenceNumber 在独立线程中轮询剪贴板序列号，
不依赖窗口焦点和 Qt 消息循环，应用处于后台/最小化时依然可靠。
非 Windows 平台自动降级（supported=False），由调用方提供 Qt 定时器兜底。
"""
import ctypes
import sys
import threading
import time

from PyQt5.QtCore import QObject, pyqtSignal


class ClipboardMonitor(QObject):
    """基于系统剪贴板序列号的底层监听器。

    Windows 下通过 user32.GetClipboardSequenceNumber 获取全局单调递增的
    剪贴板版本号，任何程序写入剪贴板都会使该值变化。监听线程仅负责
    检测序列号变化并发出信号，内容读取仍由主线程完成，避免抢剪贴板锁。
    """

    sequence_changed = pyqtSignal()

    def __init__(self, poll_interval_ms: int = 300, parent=None):
        super().__init__(parent)
        self._interval = max(80, poll_interval_ms) / 1000.0
        self._thread: threading.Thread | None = None
        self._running = False
        self._last_seq = None

    @property
    def supported(self) -> bool:
        """当前平台是否支持底层监听（Windows 专用）"""
        return sys.platform == "win32"

    def start(self) -> bool:
        """启动序列号轮询线程"""
        if self._running or not self.supported:
            return False
        self._running = True
        self._last = self._read_sequence()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="ClipboardMonitor"
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """停止监听线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.5)
            self._thread = None

    def _read_sequence(self) -> int:
        """读取当前剪贴板序列号，失败返回 0"""
        try:
            user32 = ctypes.windll.user32
            func = getattr(user32, "GetClipboardSequenceNumber", None)
            if not func:
                return 0
            func.restype = ctypes.c_uint32
            return int(func())
        except Exception:
            return 0

    def _loop(self) -> None:
        """轮询主循环"""
        while self._running:
            seq = self._read_sequence()
            if seq != 0 and seq != self._last:
                self._last = seq
                self.sequence_changed.emit()
            time.sleep(self._interval)