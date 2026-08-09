"""全局快捷键管理器 - 线程安全"""
import threading
from typing import Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal

try:
    import keyboard as _kb

    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False


class HotkeyManager(QObject):
    hotkey_pressed = pyqtSignal()
    capture_done = pyqtSignal(str)

    def __init__(self, hotkey: str = "alt+space", parent=None):
        super().__init__(parent)
        self._hotkey = hotkey
        self._listening = False
        self._capturing = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ─── 全局监听 ───

    def start(self) -> None:
        if not _HAS_KEYBOARD or self._listening:
            return
        self._stop_event.clear()
        self._listening = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._listening = False
        self._stop_event.set()

    def set_hotkey(self, hotkey: str) -> None:
        was = self._listening
        if was:
            self.stop()
        self._hotkey = hotkey
        if was:
            import time
            time.sleep(0.05)
            self.start()

    def _run(self) -> None:
        _kb.add_hotkey(self._hotkey, self._on_trigger, suppress=False)
        while self._listening and not self._stop_event.is_set():
            self._stop_event.wait(0.1)
        try:
            _kb.remove_hotkey(self._hotkey)
        except Exception:
            pass

    def _on_trigger(self) -> None:
        if not self._capturing:
            self.hotkey_pressed.emit()

    # ─── 设置页捕获新快捷键 ───

    def start_capture(self) -> None:
        if not _HAS_KEYBOARD:
            return
        self._capturing = True
        self.stop()
        threading.Thread(target=self._capture_thread, daemon=True).start()

    def _capture_thread(self) -> None:
        ev = _kb.read_event(suppress=True)
        combo = ev.name
        if ev.event_type == _kb.KEY_DOWN:
            while True:
                ev2 = _kb.read_event(suppress=True)
                if ev2.event_type == _kb.KEY_UP:
                    break
                combo = f"{combo}+{ev2.name}"
        self._capturing = False
        self.capture_done.emit(combo)

    @staticmethod
    def is_available() -> bool:
        return _HAS_KEYBOARD
