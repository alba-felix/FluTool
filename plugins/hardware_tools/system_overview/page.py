"""整机概览页面"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF
from ui import CustomFluentIcon

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_datetime,
)


class SystemOverviewPage(TabPageInterface):
    page_id = "system_overview"
    page_name = "整机概览"
    page_icon = CustomFluentIcon.COMPUTER

    @classmethod
    def create(cls, parent=None, core=None):
        return _SystemOverviewWidget(parent, core=core)


class _SystemOverviewWidget(BaseHardwarePage):
    page_id = "system_overview"
    page_name = "整机概览"
    page_title = "整机概览"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        os_rows = wmi_query(
            wmi,
            "SELECT Caption, Version, OSArchitecture, BuildNumber, "
            "RegisteredUser, SerialNumber, InstallDate, LastBootUpTime, "
            "TotalVisibleMemorySize, FreePhysicalMemory, Locale "
            "FROM Win32_OperatingSystem",
        )
        if os_rows:
            o = os_rows[0]
            total_mem = fmt_str(o.get("TotalVisibleMemorySize"))
            free_mem = fmt_str(o.get("FreePhysicalMemory"))
            try:
                used = (float(total_mem) - float(free_mem)) / 1024
                total_gb = float(total_mem) / 1024
                mem_str = f"{used:.1f} GB / {total_gb:.1f} GB"
            except (TypeError, ValueError):
                mem_str = "N/A"
            groups.append({
                "title": "操作系统",
                "rows": [
                    ("名称", o.get("Caption")),
                    ("版本", o.get("Version")),
                    ("架构", o.get("OSArchitecture")),
                    ("内部版本", o.get("BuildNumber")),
                    ("区域", o.get("Locale")),
                    ("注册用户", o.get("RegisteredUser")),
                    ("序列号", o.get("SerialNumber")),
                    ("安装时间", fmt_datetime(o.get("InstallDate"))),
                    ("上次启动", fmt_datetime(o.get("LastBootUpTime"))),
                    ("内存占用", mem_str),
                ],
            })

        cs_rows = wmi_query(
            wmi,
            "SELECT Manufacturer, Model, Name, SystemType, "
            "NumberOfProcessors, NumberOfLogicalProcessors, "
            "TotalPhysicalMemory, UserName, Domain, Workgroup "
            "FROM Win32_ComputerSystem",
        )
        if cs_rows:
            c = cs_rows[0]
            groups.append({
                "title": "计算机系统",
                "rows": [
                    ("制造商", c.get("Manufacturer")),
                    ("型号", c.get("Model")),
                    ("名称", c.get("Name")),
                    ("系统类型", c.get("SystemType")),
                    ("物理 CPU 数", c.get("NumberOfProcessors")),
                    ("逻辑处理器数", c.get("NumberOfLogicalProcessors")),
                    ("总物理内存", c.get("TotalPhysicalMemory")),
                    ("当前用户", c.get("UserName")),
                    ("域/工作组", c.get("Domain") or c.get("Workgroup")),
                ],
            })

        bios_rows = wmi_query(
            wmi,
            "SELECT Manufacturer, Name, Version, SerialNumber, "
            "SMBIOSBIOSVersion, ReleaseDate FROM Win32_BIOS",
        )
        if bios_rows:
            b = bios_rows[0]
            groups.append({
                "title": "BIOS",
                "rows": [
                    ("厂商", b.get("Manufacturer")),
                    ("名称", b.get("Name")),
                    ("版本", b.get("Version")),
                    ("SMBIOS 版本", b.get("SMBIOSBIOSVersion")),
                    ("序列号", b.get("SerialNumber")),
                    ("发布日期", fmt_datetime(b.get("ReleaseDate"))),
                ],
            })

        return {"groups": groups}
