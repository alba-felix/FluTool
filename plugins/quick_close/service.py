"""一键关闭的配置存储与进程关闭服务。"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator, List, Optional, Set

from core import get_app_data_path

CONFIG_RELATIVE_PATH = "data/quick_close.json"
GRACE_SECONDS = 2.0
WM_CLOSE = 0x0010
CREATE_NO_WINDOW = 0x08000000

# 系统关键进程与应用自身，任何情况下都不关闭
DEFAULT_WHITELIST = [
    "explorer.exe",
    "winlogon.exe",
    "csrss.exe",
    "services.exe",
    "lsass.exe",
    "smss.exe",
    "wininit.exe",
    "dwm.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "ctfmon.exe",
    "system",
    "registry",
    # 打包后的 FluTool 主程序
    "flutool.exe",
]
_DEFAULT_WHITELIST_CASEFOLD = {item.casefold() for item in DEFAULT_WHITELIST}


@dataclass(frozen=True)
class ProcessInfo:
    """进程快照条目。"""

    pid: int
    image: str
    path: str = ""
    memory: int = 0
    cpu: float = 0.0


@dataclass
class CloseResult:
    """一次关闭执行的分组结果。"""

    closed: List[str] = field(default_factory=list)
    forced: List[str] = field(default_factory=list)
    not_running: List[str] = field(default_factory=list)
    protected: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)

    @property
    def closed_count(self) -> int:
        return len(self.closed) + len(self.forced)

    def summary(self) -> str:
        """生成适合 InfoBar 展示的摘要。"""
        parts = []
        if self.closed:
            parts.append(f"已关闭 {len(self.closed)} 个")
        if self.forced:
            parts.append(f"强制结束 {len(self.forced)} 个")
        if self.not_running:
            parts.append(f"未运行 {len(self.not_running)} 个")
        if self.protected:
            parts.append(f"白名单跳过 {len(self.protected)} 个")
        if self.failed:
            parts.append(f"失败 {len(self.failed)} 个")
        return "，".join(parts) or "没有可关闭的目标"


def is_path_entry(value: str) -> bool:
    """判断配置项是完整路径还是进程名。"""
    return "\\" in value or "/" in value


def normalize_entry(value: str) -> str:
    """规范化配置项，用于去重和进程匹配。"""
    text = str(value or "").strip().strip('"')
    if not text:
        return ""
    if is_path_entry(text):
        expanded = os.path.expandvars(text)
        return os.path.normcase(os.path.normpath(expanded))
    return text.casefold()


def display_label(value: str) -> str:
    """把配置项转成简短展示名。"""
    text = str(value or "").strip().strip('"')
    if not text:
        return ""
    return os.path.basename(os.path.normpath(text)) if is_path_entry(text) else text


def matches_process(process: ProcessInfo, entry: str) -> bool:
    """判断进程是否命中配置项。"""
    normalized = normalize_entry(entry)
    if not normalized:
        return False
    if is_path_entry(str(entry)):
        if not process.path:
            return False
        return os.path.normcase(os.path.normpath(process.path)) == normalized
    return process.image.casefold() == normalized


_SYSTEM_ROOT_CASEFOLD = os.path.normcase(
    os.path.normpath(os.environ.get("SystemRoot") or r"C:\Windows")
)


def is_system_process(process: ProcessInfo) -> bool:
    """判断进程是否位于 Windows 系统目录。"""
    if not process.path:
        return False
    normalized = os.path.normcase(os.path.normpath(process.path))
    return normalized.startswith(_SYSTEM_ROOT_CASEFOLD + os.sep)


def is_protected(process: ProcessInfo, whitelist: Iterable[str]) -> bool:
    """判断进程是否命中系统进程、默认白名单或用户白名单。"""
    if process.image.casefold() in _DEFAULT_WHITELIST_CASEFOLD:
        return True
    if is_system_process(process):
        return True
    return any(matches_process(process, entry) for entry in whitelist)


def is_default_whitelist_entry(value: str) -> bool:
    """判断配置项是否与内置系统白名单重复（仅按进程名匹配）。"""
    text = str(value or "").strip().strip('"')
    if not text or is_path_entry(text):
        return False
    return text.casefold() in _DEFAULT_WHITELIST_CASEFOLD


class QuickCloseStore:
    """读写 data/quick_close.json。"""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path is not None else get_app_data_path(CONFIG_RELATIVE_PATH)

    def _default_config(self) -> dict:
        # 系统关键进程保护内置在 DEFAULT_WHITELIST，这里只保存用户自定义白名单
        return {"targets": [], "whitelist": []}

    def load(self) -> dict:
        """读取配置；文件不存在时创建模板，损坏时备份后重建。"""
        if not self.path.exists():
            data = self._default_config()
            self.save(data)
            return data

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            broken = self.path.with_name(f"{self.path.name}.broken")
            try:
                os.replace(self.path, broken)
            except OSError:
                pass
            data = self._default_config()
            self.save(data)
            return data

        if not isinstance(raw, dict):
            raw = {}
        targets = [
            str(item).strip() for item in raw.get("targets", [])
            if isinstance(item, str) and str(item).strip()
        ]
        raw_whitelist = [
            str(item).strip() for item in raw.get("whitelist", [])
            if isinstance(item, str) and str(item).strip()
        ]
        # 内置系统进程不再写进 JSON，读取时顺手清理旧配置里的重复项
        whitelist = [
            item for item in raw_whitelist
            if not is_default_whitelist_entry(item)
        ]
        data = {"targets": targets, "whitelist": whitelist}
        if len(whitelist) != len(raw_whitelist):
            try:
                self.save(data)
            except OSError:
                pass
        return data

    def save(self, data: dict) -> None:
        """原子写入配置文件。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f"{self.path.name}.tmp")
        temp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp_path, self.path)

    def add_targets(self, entries: Iterable[str]) -> int:
        """合并新目标，按规范化值去重，返回新增数量。"""
        data = self.load()
        existing = {normalize_entry(item) for item in data["targets"]}
        added = 0
        for entry in entries:
            text = str(entry or "").strip().strip('"')
            normalized = normalize_entry(text)
            if not normalized or normalized in existing:
                continue
            data["targets"].append(text)
            existing.add(normalized)
            added += 1
        if added:
            self.save(data)
        return added


# ------------------------------ Windows API ------------------------------

if os.name == "nt":
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND


def _process_path(pid: int) -> str:
    """查询进程完整路径，权限不足时返回空字符串。"""
    if os.name != "nt":
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
    finally:
        kernel32.CloseHandle(handle)
    return ""


def _process_memory(handle) -> int:
    """读取进程工作集占用，权限不足时返回 0。"""
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        return int(counters.WorkingSetSize)
    return 0


def _filetime_ticks(value) -> int:
    """把 FILETIME 转成 100ns 累计值。"""
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


def _cpu_ticks(handle) -> int:
    """读取进程累计内核态与用户态 CPU 时间（100ns）。"""
    created = wintypes.FILETIME()
    exited = wintypes.FILETIME()
    kernel = wintypes.FILETIME()
    user = wintypes.FILETIME()
    if not kernel32.GetProcessTimes(
        handle, ctypes.byref(created), ctypes.byref(exited),
        ctypes.byref(kernel), ctypes.byref(user),
    ):
        return 0
    return _filetime_ticks(kernel) + _filetime_ticks(user)


def _process_usage(pid: int) -> tuple:
    """一次性读取进程完整路径、工作集和累计 CPU 时间。"""
    if os.name != "nt" or pid <= 0:
        return "", 0, 0
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return "", 0, 0
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buffer))
        path = ""
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            path = buffer.value
        return path, _process_memory(handle), _cpu_ticks(handle)
    finally:
        kernel32.CloseHandle(handle)


def _process_cpu_ticks(pid: int) -> int:
    """仅读取进程累计 CPU 时间。"""
    if os.name != "nt" or pid <= 0:
        return 0
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return 0
    try:
        return _cpu_ticks(handle)
    finally:
        kernel32.CloseHandle(handle)


def _iter_process_entries() -> Iterator[tuple]:
    """遍历进程快照，产出 (pid, 映像名)。"""
    if os.name != "nt":
        return

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == INVALID_HANDLE_VALUE:
        return

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while has_entry:
            yield int(entry.th32ProcessID), entry.szExeFile
            has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)


def list_processes() -> List[ProcessInfo]:
    """获取当前进程快照。"""
    return [
        ProcessInfo(pid=pid, image=image, path=_process_path(pid) if pid else "")
        for pid, image in _iter_process_entries()
    ]


def sample_processes(interval: float = 0.4) -> List[ProcessInfo]:
    """采样进程列表，附带内存占用和 CPU 百分比。

    通过间隔读取累计 CPU 时间计算占用，interval 为采样窗口秒数。
    """
    if os.name != "nt":
        return list_processes()

    started = time.perf_counter()
    rows = []
    base_ticks = {}
    for pid, image in _iter_process_entries():
        path, memory, ticks = _process_usage(pid)
        rows.append((pid, image, path, memory))
        base_ticks[pid] = ticks

    time.sleep(interval)
    elapsed = max(time.perf_counter() - started, 0.001)
    divisor = elapsed * 10_000_000 * (os.cpu_count() or 1)

    processes = []
    for pid, image, path, memory in rows:
        delta = max(_process_cpu_ticks(pid) - base_ticks.get(pid, 0), 0)
        processes.append(ProcessInfo(
            pid=pid,
            image=image,
            path=path,
            memory=memory,
            cpu=round(delta / divisor * 100, 1),
        ))
    return processes


def get_process_info(pid: int) -> Optional[ProcessInfo]:
    """按 PID 读取单个进程的映像名和完整路径。"""
    if os.name != "nt" or pid <= 0:
        return None
    for current_pid, image in _iter_process_entries():
        if current_pid == pid:
            return ProcessInfo(pid=pid, image=image, path=_process_path(pid))
    return None


def process_map(pids: Iterable[int]) -> dict:
    """一次快照批量读取指定 PID 的进程信息。"""
    wanted = {int(pid) for pid in pids if int(pid) > 0}
    if os.name != "nt" or not wanted:
        return {}

    found: dict[int, ProcessInfo] = {}
    for pid, image in _iter_process_entries():
        if pid not in wanted:
            continue
        found[pid] = ProcessInfo(pid=pid, image=image, path=_process_path(pid))
        if len(found) == len(wanted):
            break
    return found


def foreground_process(exclude_pids: Optional[Set[int]] = None) -> Optional[ProcessInfo]:
    """读取当前前台窗口所属进程；属于自身或排除集合时返回 None。"""
    if os.name != "nt":
        return None
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    pid_value = int(pid.value)
    if pid_value <= 4:
        return None
    if exclude_pids and pid_value in exclude_pids:
        return None
    return get_process_info(pid_value)


def send_wm_close(pids: Set[int]) -> int:
    """向目标进程的所有顶层窗口发送 WM_CLOSE（含隐藏的托盘窗口）。"""
    if os.name != "nt" or not pids:
        return 0

    closed = 0

    def _callback(hwnd, _lparam):
        nonlocal closed
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            closed += 1
        return True

    callback = WNDENUMPROC(_callback)
    user32.EnumWindows(callback, 0)
    return closed


def terminate_process_tree(pid: int) -> bool:
    """强制结束进程树。"""
    try:
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


class QuickCloseService:
    """按配置关闭目标应用。"""

    def __init__(
        self,
        store: Optional[QuickCloseStore] = None,
        logger=None,
        process_provider: Optional[Callable[[], List[ProcessInfo]]] = None,
        close_sender: Optional[Callable[[Set[int]], int]] = None,
        terminator: Optional[Callable[[int], bool]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ):
        self.store = store or QuickCloseStore()
        self._logger = logger
        self._process_provider = process_provider or list_processes
        self._close_sender = close_sender or send_wm_close
        self._terminator = terminator or terminate_process_tree
        self._sleeper = sleeper or time.sleep
        self._clock = clock or time.monotonic

    def _log(self, message: str) -> None:
        if self._logger is not None:
            try:
                self._logger.info(message)
            except Exception:
                pass

    def _alive_pids(self, pids: Set[int]) -> Set[int]:
        return {process.pid for process in self._process_provider()} & pids

    def _wait_until_gone(self, pids: Set[int], timeout: float) -> None:
        """轮询等待目标进程退出，最多等待 timeout 秒。"""
        deadline = self._clock() + timeout
        while pids & self._alive_pids(pids):
            if self._clock() >= deadline:
                return
            self._sleeper(0.1)

    def _is_protected(self, process: ProcessInfo, entries: Iterable[str]) -> bool:
        return is_protected(process, entries)

    def close_targets(
        self,
        targets: Optional[Iterable[str]] = None,
        whitelist: Optional[Iterable[str]] = None,
    ) -> CloseResult:
        """关闭配置中的目标应用，返回分组结果。"""
        config = self.store.load()
        target_list = [
            str(item).strip() for item in (targets if targets is not None else config["targets"])
            if str(item).strip()
        ]
        whitelist_entries = list(
            whitelist if whitelist is not None else config["whitelist"]
        )
        result = CloseResult()
        if not target_list:
            return result

        processes = self._process_provider()
        target_matches: dict[str, List[ProcessInfo]] = {}
        for target in target_list:
            matches = [process for process in processes if matches_process(process, target)]
            if matches:
                target_matches[target] = matches
            else:
                result.not_running.append(display_label(target))

        pid_owner: dict[int, str] = {}
        protected_labels: Set[str] = set()
        for target, matches in target_matches.items():
            for process in matches:
                if (
                    process.pid == os.getpid()
                    or process.pid <= 4
                    or self._is_protected(process, whitelist_entries)
                ):
                    protected_labels.add(display_label(target))
                    continue
                pid_owner.setdefault(process.pid, target)

        result.protected = sorted(protected_labels)
        pids = set(pid_owner)
        if not pids:
            return result

        self._log(f"[quick_close] 关闭目标: {sorted(pid_owner)}")
        self._close_sender(pids)
        self._wait_until_gone(pids, GRACE_SECONDS)

        forced_pids: Set[int] = set()
        for pid in sorted(pids & self._alive_pids(pids)):
            if self._terminator(pid):
                forced_pids.add(pid)
        if forced_pids:
            self._wait_until_gone(forced_pids, 0.5)

        alive_pids = self._alive_pids(pids)
        for target, matches in target_matches.items():
            owned = {process.pid for process in matches if pid_owner.get(process.pid) == target}
            if not owned:
                continue
            if owned & alive_pids:
                result.failed.append(display_label(target))
            elif owned & forced_pids:
                result.forced.append(display_label(target))
            else:
                result.closed.append(display_label(target))
        return result
