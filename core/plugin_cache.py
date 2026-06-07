"""Plugin scan cache - persists scan results to avoid filesystem re-scan on startup."""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .utils import get_app_data_path

CACHE_FILE = "cache/plugin_scan_cache.json"
CACHE_VERSION = 1


def _cache_path() -> Path:
    return get_app_data_path(CACHE_FILE)


MANIFEST_FILENAMES = ("plugin.py", "plugin.json")


def _hash_manifest(plugin_dir: Path) -> str:
    hasher = hashlib.sha256()
    found = False
    for filename in MANIFEST_FILENAMES:
        manifest = plugin_dir / filename
        if manifest.exists():
            hasher.update(manifest.read_bytes())
            found = True
    return hasher.hexdigest() if found else ""


def restore_scan_cache(scan_base: Optional[Path] = None) -> Optional[Tuple[List[str], Dict[str, Path], Dict[str, str]]]:
    """从缓存恢复扫描结果，缓存无效则返回 None
    
    Args:
        scan_base: 当前请求的扫描路径。若提供且与缓存 base 不一致则视为无效。
    """
    cache_file = _cache_path()
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
        return None

    plugins: List[dict] = data.get("plugins", [])
    if not plugins:
        return None

    base = Path(data.get("base_path", ""))
    if not base or not base.exists():
        return None

    # 如果指定了 scan_base，必须与缓存 base 一致
    if scan_base is not None and Path(scan_base).resolve() != base.resolve():
        return None

    has_changed = False
    plugin_ids: List[str] = []
    plugin_dirs: Dict[str, Path] = {}
    plugin_modules: Dict[str, str] = {}

    for p in plugins:
        pid = p.get("id", "")
        if not pid:
            continue

        dir_name = p.get("dir", pid)
        plugin_path = base / dir_name
        cached_hash = p.get("hash", "")
        current_hash = _hash_manifest(plugin_path)

        if current_hash != cached_hash:
            has_changed = True
            continue

        plugin_ids.append(pid)
        plugin_dirs[pid] = plugin_path
        plugin_modules[pid] = p.get("module", f"plugins.{dir_name}")

    if has_changed:
        return None

    plugin_ids.sort(key=lambda pid: _priority_from_cache(plugins, pid))
    return plugin_ids, plugin_dirs, plugin_modules


def _priority_from_cache(plugins: List[dict], plugin_id: str) -> float:
    for p in plugins:
        if p.get("id") == plugin_id:
            return float(p.get("priority", 999))
    return 999.0


def save_scan_cache(
    plugin_ids: List[str],
    plugin_dirs: Dict[str, Path],
    plugin_modules: Dict[str, str],
    scan_base: Path,
) -> None:
    """保存扫描结果到缓存"""
    if not plugin_ids or not scan_base.exists():
        return

    try:
        base = str(scan_base.resolve())
    except (OSError, ValueError):
        base = str(scan_base)

    plugins: List[Dict[str, Any]] = []
    for pid in plugin_ids:
        pdir = plugin_dirs.get(pid)
        if not pdir:
            continue
        plugin_path = Path(pdir)
        plugins.append({
            "id": pid,
            "dir": plugin_path.name,
            "module": plugin_modules.get(pid, f"plugins.{plugin_path.name}"),
            "priority": _read_priority(plugin_path),
            "hash": _hash_manifest(plugin_path),
        })

    data = {
        "version": CACHE_VERSION,
        "cached_at": time.time(),
        "base_path": base,
        "plugins": plugins,
    }

    cache_file = _cache_path()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _read_priority(plugin_dir: Path) -> float:
    for filename in MANIFEST_FILENAMES:
        manifest_file = plugin_dir / filename
        if not manifest_file.exists():
            continue
        try:
            text = manifest_file.read_text("utf-8")
            if filename.endswith(".py"):
                import ast
                tree = ast.parse(text)
                for node in tree.body:
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "PLUGIN_MANIFEST":
                                manifest = ast.literal_eval(node.value)
                                if isinstance(manifest, dict):
                                    return float(manifest.get("priority", 999))
            else:
                manifest = json.loads(text)
                return float(manifest.get("priority", 999))
        except Exception:
            pass
    return 999.0


def clear_cache() -> None:
    cache_file = _cache_path()
    if cache_file.exists():
        cache_file.unlink()
