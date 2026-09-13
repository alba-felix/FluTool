"""主板与固件页面"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF
from ui import CustomFluentIcon

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_datetime,
)


class MotherboardFirmwarePage(TabPageInterface):
    page_id = "motherboard_firmware"
    page_name = "主板与固件"
    page_icon = CustomFluentIcon.CONTROL_PANEL

    @classmethod
    def create(cls, parent=None, core=None):
        return _MotherboardFirmwareWidget(parent, core=core)


class _MotherboardFirmwareWidget(BaseHardwarePage):
    page_id = "motherboard_firmware"
    page_name = "主板与固件"
    page_title = "主板与固件"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        mb_rows = wmi_query(
            wmi,
            "SELECT Manufacturer, Product, Version, SerialNumber, "
            "Model, Status FROM Win32_BaseBoard",
        )
        if mb_rows:
            m = mb_rows[0]
            groups.append({
                "title": "主板",
                "rows": [
                    ("制造商", m.get("Manufacturer")),
                    ("型号", m.get("Product")),
                    ("版本", m.get("Version")),
                    ("序列号", m.get("SerialNumber")),
                    ("状态", m.get("Status")),
                ],
            })

        bios_rows = wmi_query(
            wmi,
            "SELECT Manufacturer, Name, Version, SerialNumber, "
            "SMBIOSBIOSVersion, ReleaseDate, PrimaryBIOS, Status "
            "FROM Win32_BIOS",
        )
        if bios_rows:
            b = bios_rows[0]
            groups.append({
                "title": "固件 / BIOS",
                "rows": [
                    ("厂商", b.get("Manufacturer")),
                    ("名称", b.get("Name")),
                    ("版本", b.get("Version")),
                    ("SMBIOS 版本", b.get("SMBIOSBIOSVersion")),
                    ("序列号", b.get("SerialNumber")),
                    ("发布日期", fmt_datetime(b.get("ReleaseDate"))),
                    ("主 BIOS", "是" if str(b.get("PrimaryBIOS")) == "True" else "否"),
                    ("状态", b.get("Status")),
                ],
            })

        return {"groups": groups}
