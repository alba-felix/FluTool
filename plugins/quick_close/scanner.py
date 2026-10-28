"""扫描 Windows 已安装程序，解析主可执行文件路径。

扫描逻辑参考 install_app_monitor/kuai.py，但只保留注册表读取和 exe 推断，
不做图标提取与 HTML 报告，避免扫描阶段产生额外副作用。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List

try:
    import winreg
except ImportError:  # pragma: no cover - 非 Windows 环境
    winreg = None


UNINSTALL_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
MAX_EXE_FILES = 200
MAX_SCAN_DEPTH = 2

# 常见的非主程序 exe，降低误选概率
_EXCLUDED_EXE_KEYWORDS = (
    "unins", "uninstall", "setup", "update", "updater", "helper",
    "crash", "report", "repair", "redist", "dxsetup", "installer",
)
_EXCLUDED_DIR_NAMES = {
    "uninstall", "uninst", "update", "updater", "install", "setup",
    "redist", "resources", "plugins", "locales", "cache", "temp",
}
# 系统目录下的可执行文件不能作为应用主程序
_SYSTEM_EXE_NAMES = {
    "explorer.exe", "winlogon.exe", "csrss.exe", "services.exe",
    "lsass.exe", "smss.exe", "wininit.exe", "dwm.exe", "svchost.exe",
    "cmd.exe", "powershell.exe", "msiexec.exe", "rundll32.exe",
}
_NAME_SPLIT_PATTERN = re.compile(r"[\s\-_.()\[\],，、/\\]+")


def _windows_dir() -> Path | None:
    """返回 Windows 目录，用于排除系统路径。"""
    value = os.environ.get("WINDIR") or os.environ.get("SystemRoot")
    return Path(value).resolve() if value else None


def _is_system_path(path: Path) -> bool:
    """判断路径是否位于 Windows 目录内。"""
    windows_dir = _windows_dir()
    if windows_dir is None:
        return False
    try:
        resolved = path.resolve()
    except OSError:
        return False
    return resolved == windows_dir or windows_dir in resolved.parents


def _is_unusable_directory(directory: str) -> bool:
    """排除盘符根目录和 Windows/Program Files 等程序集根目录。"""
    path = Path(os.path.expandvars(directory.strip().strip('"')))
    try:
        resolved = path.resolve()
    except OSError:
        return True
    if resolved.parent == resolved:
        return True
    if _is_system_path(resolved):
        return True

    roots = []
    for name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        value = os.environ.get(name)
        if value:
            roots.append(Path(value).resolve())
    return resolved in roots


@dataclass(frozen=True)
class InstalledApp:
    """一个已安装程序的主程序信息。"""

    name: str
    exe: str


def _read_value(key, value_name: str):
    """读取注册表值，不存在时返回 None。"""
    try:
        return winreg.QueryValueEx(key, value_name)[0]
    except OSError:
        return None


def _is_truthy(value) -> bool:
    """判断注册表里的 0/1 或字符串开关。"""
    return str(value).strip().lower() in {"1", "true", "yes"}


def _display_name_tokens(name: str) -> List[str]:
    """拆分软件名称，用于和 exe 文件名做匹配。"""
    return [token.casefold() for token in _NAME_SPLIT_PATTERN.split(name) if len(token) >= 2]


def _score_executable(exe_path: str, software_name: str, file_size: int) -> int:
    """按名称重合度给候选 exe 打分，越低分的辅助程序越可能被排除。"""
    stem = Path(exe_path).stem.casefold()
    score = 0
    for token in _display_name_tokens(software_name):
        if token in stem:
            score += 4
    normalized_name = re.sub(r"[\s\-_.()\[\],，、/\\]+", "", software_name.casefold())
    if normalized_name and normalized_name in stem:
        score += 6
    if any(keyword in stem for keyword in _EXCLUDED_EXE_KEYWORDS):
        score -= 20
    # 同等匹配时优先较大的文件，通常才是主程序
    score += min(file_size // (1024 * 1024), 4)
    return score


def find_main_executable(directory: str, software_name: str = "") -> str:
    """在安装目录中推断主程序 exe。"""
    base = Path(os.path.expandvars(str(directory).strip().strip('"')))
    if not base.is_dir():
        return ""

    candidates: List[tuple] = []
    stack = [(base, 0)]
    scanned = 0
    while stack and scanned < MAX_EXE_FILES:
        current, depth = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_file() and entry.name.casefold().endswith(".exe"):
                    if entry.name.casefold() in _SYSTEM_EXE_NAMES:
                        continue
                    if any(keyword in entry.name.casefold() for keyword in _EXCLUDED_EXE_KEYWORDS):
                        continue
                    size = entry.stat().st_size
                    candidates.append((entry.path, size))
                    scanned += 1
                    if scanned >= MAX_EXE_FILES:
                        break
                elif entry.is_dir() and depth < MAX_SCAN_DEPTH:
                    if entry.name.casefold() in _EXCLUDED_DIR_NAMES:
                        continue
                    stack.append((Path(entry.path), depth + 1))
            except OSError:
                continue

    if not candidates:
        return ""

    best_path = max(
        candidates,
        key=lambda item: _score_executable(item[0], software_name, item[1]),
    )[0]
    return str(Path(best_path).resolve())


def _display_icon_candidates(display_icon: str) -> Iterator[str]:
    """从 DisplayIcon 中提取候选 exe 路径（去掉图标索引和引号）。"""
    if not display_icon:
        return
    text = os.path.expandvars(str(display_icon).strip())
    if text.startswith('"'):
        end = text.find('"', 1)
        if end > 1:
            text = text[1:end]
    elif "," in text:
        text = text.rsplit(",", 1)[0]
    text = text.strip().strip('"')
    if text:
        yield text


def _command_executable(command: str) -> str:
    """从卸载命令中提取可执行文件路径。"""
    if not command:
        return ""
    text = os.path.expandvars(str(command).strip())
    if text.startswith('"'):
        end = text.find('"', 1)
        return text[1:end] if end > 1 else ""

    # 未加引号但路径带空格时，以第一个 .exe 结尾作为路径边界
    match = re.match(r"^(.*?\.exe)(?:\s|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.split(" ", 1)[0]


def resolve_executable(
    software_name: str,
    display_icon: str = "",
    install_location: str = "",
    uninstall_string: str = "",
) -> str:
    """按 DisplayIcon → InstallLocation → UninstallString 的顺序解析主程序 exe。"""
    for candidate in _display_icon_candidates(display_icon):
        path = Path(candidate)
        if path.suffix.casefold() != ".exe" or not path.is_file():
            continue
        if path.name.casefold() in _SYSTEM_EXE_NAMES or _is_system_path(path):
            continue
        return str(path.resolve())

    install_dir = str(install_location).strip().strip('"')
    if install_dir and Path(os.path.expandvars(install_dir)).is_dir() \
            and not _is_unusable_directory(install_dir):
        exe = find_main_executable(install_dir, software_name)
        if exe:
            return exe

    uninstall_exe = _command_executable(uninstall_string)
    if uninstall_exe:
        parent = Path(uninstall_exe).parent
        # 避免在系统目录或盘符根目录里误找主程序
        if parent.name.casefold() not in {"system32", "syswow64", "windows"} \
                and not _is_unusable_directory(str(parent)):
            exe = find_main_executable(str(parent), software_name)
            if exe:
                return exe

    return ""


def _registry_views() -> List[int]:
    """返回可用的注册表 32/64 位视图标志。"""
    views = []
    for name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        if hasattr(winreg, name):
            views.append(getattr(winreg, name))
    return views or [0]


def _iter_uninstall_entries(root, view_flag: int) -> Iterator[InstalledApp]:
    """遍历一个注册表视图下的卸载条目。"""
    try:
        key = winreg.OpenKey(root, UNINSTALL_KEY, 0, winreg.KEY_READ | view_flag)
    except OSError:
        return

    with key:
        try:
            subkey_count = winreg.QueryInfoKey(key)[0]
        except OSError:
            return

        for index in range(subkey_count):
            try:
                subkey_name = winreg.EnumKey(key, index)
                with winreg.OpenKey(key, subkey_name) as subkey:
                    app = _read_uninstall_entry(subkey)
            except OSError:
                continue
            if app:
                yield app


def _read_uninstall_entry(subkey) -> InstalledApp | None:
    """读取单个卸载条目并解析主程序。"""
    display_name = str(_read_value(subkey, "DisplayName") or "").strip()
    if not display_name:
        return None

    if _is_truthy(_read_value(subkey, "SystemComponent")):
        return None
    if _is_truthy(_read_value(subkey, "NoDisplay")):
        return None
    if _read_value(subkey, "ParentKeyName"):
        return None
    release_type = str(_read_value(subkey, "ReleaseType") or "").casefold()
    if release_type in {"update", "hotfix", "security update"}:
        return None

    exe = resolve_executable(
        display_name,
        str(_read_value(subkey, "DisplayIcon") or ""),
        str(_read_value(subkey, "InstallLocation") or ""),
        str(_read_value(subkey, "UninstallString") or ""),
    )
    if not exe:
        return None
    return InstalledApp(name=display_name, exe=exe)


def scan_installed_apps() -> List[InstalledApp]:
    """扫描已安装程序，按 exe 路径去重后返回。"""
    if winreg is None:
        return []

    found: dict[str, InstalledApp] = {}
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view_flag in _registry_views():
            for app in _iter_uninstall_entries(root, view_flag):
                key = os.path.normcase(os.path.normpath(app.exe))
                found.setdefault(key, app)
    return sorted(found.values(), key=lambda item: item.name.casefold())


def filter_apps(apps: Iterable[InstalledApp], keyword: str) -> List[InstalledApp]:
    """按名称或路径过滤扫描结果，供选择对话框使用。"""
    query = keyword.strip().casefold()
    if not query:
        return list(apps)
    return [
        app for app in apps
        if query in app.name.casefold() or query in app.exe.casefold()
    ]
