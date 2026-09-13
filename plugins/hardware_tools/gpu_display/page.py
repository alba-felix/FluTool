"""显卡与显示器页面"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF
from ui import CustomFluentIcon

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_int, fmt_size,
)


class GpuDisplayPage(TabPageInterface):
    page_id = "gpu_display"
    page_name = "显卡与显示器"
    page_icon = CustomFluentIcon.DESK

    @classmethod
    def create(cls, parent=None, core=None):
        return _GpuDisplayWidget(parent, core=core)


class _GpuDisplayWidget(BaseHardwarePage):
    page_id = "gpu_display"
    page_name = "显卡与显示器"
    page_title = "显卡与显示器"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        gpu_rows = wmi_query(
            wmi,
            "SELECT Name, AdapterRAM, DriverVersion, DriverDate, "
            "VideoProcessor, VideoArchitecture, AdapterCompatibility, "
            "CurrentHorizontalResolution, CurrentVerticalResolution, "
            "CurrentRefreshRate, Status, InfFilename "
            "FROM Win32_VideoController",
        )
        for i, g in enumerate(gpu_rows, 1):
            groups.append({
                "title": f"显卡 #{i}" if len(gpu_rows) > 1 else "显卡",
                "rows": [
                    ("名称", g.get("Name")),
                    ("厂商", g.get("AdapterCompatibility")),
                    ("显存", fmt_size(g.get("AdapterRAM"))),
                    ("驱动版本", g.get("DriverVersion")),
                    ("驱动日期", fmt_str(g.get("DriverDate"))),
                    ("视频处理器", g.get("VideoProcessor")),
                    ("当前分辨率", f"{fmt_int(g.get('CurrentHorizontalResolution'))} x {fmt_int(g.get('CurrentVerticalResolution'))}"),
                    ("刷新率", fmt_int(g.get("CurrentRefreshRate"), " Hz")),
                    ("状态", g.get("Status")),
                ],
            })

        mon_rows = wmi_query(
            wmi,
            "SELECT Name, DeviceID, ScreenHeight, ScreenWidth, "
            "PixelsPerXLogicalInch, MonitorType FROM Win32_DesktopMonitor",
        )
        for i, m in enumerate(mon_rows, 1):
            groups.append({
                "title": f"显示器 #{i}" if len(mon_rows) > 1 else "显示器",
                "rows": [
                    ("名称", m.get("Name")),
                    ("设备 ID", m.get("DeviceID")),
                    ("物理分辨率", f"{fmt_int(m.get('ScreenWidth'))} x {fmt_int(m.get('ScreenHeight'))}"),
                    ("逻辑 DPI", fmt_int(m.get("PixelsPerXLogicalInch"))),
                    ("类型", m.get("MonitorType")),
                ],
            })

        pnp_rows = wmi_query(
            wmi,
            "SELECT Name, Status FROM Win32_PnPEntity WHERE PNPClass = 'Monitor'",
        )
        if pnp_rows:
            groups.append({
                "title": "显示器设备（PnP）",
                "rows": [(p.get("Name"), p.get("Status")) for p in pnp_rows],
            })

        return {"groups": groups}
