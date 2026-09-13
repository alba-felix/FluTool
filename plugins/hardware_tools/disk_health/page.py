"""磁盘与健康页面"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF
from ui import CustomFluentIcon

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_size,
)


class DiskHealthPage(TabPageInterface):
    page_id = "disk_health"
    page_name = "磁盘与健康"
    page_icon = CustomFluentIcon.DISK

    @classmethod
    def create(cls, parent=None, core=None):
        return _DiskHealthWidget(parent, core=core)


class _DiskHealthWidget(BaseHardwarePage):
    page_id = "disk_health"
    page_name = "磁盘与健康"
    page_title = "磁盘与健康"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        disk_rows = wmi_query(
            wmi,
            "SELECT Model, Manufacturer, InterfaceType, MediaType, "
            "Size, Partitions, SerialNumber, FirmwareRevision, Status "
            "FROM Win32_DiskDrive",
        )
        for i, d in enumerate(disk_rows, 1):
            groups.append({
                "title": f"物理磁盘 #{i}" if len(disk_rows) > 1 else "物理磁盘",
                "rows": [
                    ("型号", d.get("Model")),
                    ("厂商", d.get("Manufacturer")),
                    ("接口类型", d.get("InterfaceType")),
                    ("介质类型", d.get("MediaType")),
                    ("容量", fmt_size(d.get("Size"))),
                    ("分区数", d.get("Partitions")),
                    ("固件版本", d.get("FirmwareRevision")),
                    ("序列号", d.get("SerialNumber")),
                    ("状态", d.get("Status")),
                ],
            })

        vol_rows = wmi_query(
            wmi,
            "SELECT DeviceID, VolumeName, FileSystem, Size, FreeSpace "
            "FROM Win32_LogicalDisk WHERE DriveType = 3",
        )
        for v in vol_rows:
            try:
                size = float(v.get("Size") or 0)
                free = float(v.get("FreeSpace") or 0)
                used_pct = f"{((size - free) / size * 100):.1f}%" if size else "N/A"
            except (TypeError, ValueError):
                used_pct = "N/A"
            groups.append({
                "title": f"卷 {v.get('DeviceID')}",
                "rows": [
                    ("卷标", v.get("VolumeName")),
                    ("文件系统", v.get("FileSystem")),
                    ("总容量", fmt_size(v.get("Size"))),
                    ("可用空间", fmt_size(v.get("FreeSpace"))),
                    ("已用比例", used_pct),
                ],
            })

        return {"groups": groups}
