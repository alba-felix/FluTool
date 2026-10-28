"""枚举当前顶层窗口，供窗口列表选择使用。"""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from typing import Iterator, List, Optional, Set

from .service import ProcessInfo, normalize_entry, process_map

if os.name == "nt":
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL


@dataclass(frozen=True)
class WindowInfo:
    """一个顶层窗口及其所属进程。"""

    hwnd: int
    pid: int
    title: str
    image: str
    path: str = ""
    visible: bool = True
    width: int = 0
    height: int = 0

    @property
    def entry(self) -> str:
        """写入 targets 的配置项，优先完整路径。"""
        return self.path or self.image

    @property
    def state(self) -> str:
        """窗口状态标签。"""
        if not self.visible:
            return "托盘/隐藏"
        if self.width <= 0 or self.height <= 0:
            return "已最小化"
        return "可见"


def _iter_top_windows() -> Iterator[int]:
    """遍历所有顶层窗口句柄，包含隐藏窗口。"""
    if os.name != "nt":
        return

    handles: List[int] = []

    def _callback(hwnd, _lparam):
        handles.append(int(hwnd))
        return True

    user32.EnumWindows(WNDENUMPROC(_callback), 0)
    yield from handles


def _window_title(hwnd: int) -> str:
    """读取窗口标题。"""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def _window_size(hwnd: int) -> tuple:
    """读取窗口宽高。"""
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return 0, 0
    return max(rect.right - rect.left, 0), max(rect.bottom - rect.top, 0)


def _window_rank(window: WindowInfo) -> tuple:
    """同一进程多个窗口时的代表性排序依据。"""
    return (window.visible, window.width * window.height, len(window.title))


def _collect_candidates(exclude_pids: Set[int]) -> List[tuple]:
    """收集窗口基础信息，跳过系统进程和排除进程。"""
    if os.name != "nt":
        return []

    candidates = []
    for hwnd in _iter_top_windows():
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_value = int(pid.value)
        if pid_value <= 4 or pid_value in exclude_pids:
            continue
        width, height = _window_size(hwnd)
        candidates.append((
            hwnd, pid_value, _window_title(hwnd),
            bool(user32.IsWindowVisible(hwnd)), width, height,
        ))
    return candidates


def list_windows(exclude_pids: Optional[Set[int]] = None) -> List[WindowInfo]:
    """枚举顶层窗口，按进程条目去重后返回。

    每个进程只保留一个代表性窗口：可见窗口优先，其次面积和标题更完整的。
    """
    if os.name != "nt":
        return []

    candidates = _collect_candidates(exclude_pids or set())
    if not candidates:
        return []

    processes = process_map({item[1] for item in candidates})
    best: dict[str, WindowInfo] = {}
    for hwnd, pid, title, visible, width, height in candidates:
        process = processes.get(pid)
        if process is None:
            continue
        window = WindowInfo(
            hwnd=hwnd, pid=pid, title=title, image=process.image,
            path=process.path, visible=visible, width=width, height=height,
        )
        key = normalize_entry(window.entry)
        current = best.get(key)
        if current is None or _window_rank(window) > _window_rank(current):
            best[key] = window

    return sorted(
        best.values(),
        key=lambda item: (not item.visible, item.title.casefold() or item.image.casefold()),
    )


def window_process(window: WindowInfo) -> ProcessInfo:
    """把窗口还原成关闭流程使用的进程信息。"""
    return ProcessInfo(pid=window.pid, image=window.image, path=window.path)
