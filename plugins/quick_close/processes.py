"""任务管理器式进程列表的分组与展示。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .service import ProcessInfo, normalize_entry


@dataclass(frozen=True)
class ProcessGroup:
    """同一条目标下的进程集合。"""

    entry: str
    image: str
    path: str
    memory: int
    cpu: float
    pids: tuple

    @property
    def count(self) -> int:
        return len(self.pids)

    @property
    def memory_text(self) -> str:
        return format_memory(self.memory)


def format_memory(value: int) -> str:
    """把字节数格式化为易读文本。"""
    if value <= 0:
        return "-"
    if value < 1024 * 1024:
        return f"{value / 1024:.0f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


def group_processes(processes: Iterable[ProcessInfo]) -> List[ProcessGroup]:
    """按目标条目合并同名进程，返回按进程名排序的分组。"""
    buckets: dict = {}
    for process in processes:
        if process.pid <= 4:
            continue
        key = normalize_entry(process.path or process.image)
        if not key:
            continue
        buckets.setdefault(key, []).append(process)

    groups = []
    for items in buckets.values():
        first = items[0]
        path = next((item.path for item in items if item.path), "")
        groups.append(ProcessGroup(
            entry=path or first.image,
            image=first.image,
            path=path,
            memory=sum(item.memory for item in items),
            cpu=round(sum(item.cpu for item in items), 1),
            pids=tuple(sorted(item.pid for item in items)),
        ))

    return sorted(groups, key=lambda item: (item.image.casefold(), item.pids[0]))
