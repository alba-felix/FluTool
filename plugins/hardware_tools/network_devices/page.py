"""网络与设备页面（网卡 / 蓝牙 / 音频 / USB / 摄像头）"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF
from ui import CustomFluentIcon

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_int,
)

_NET_STATUS = {
    0: "断开", 1: "连接中", 2: "已连接", 3: "断开中",
    4: "硬件不存在", 5: "硬件已禁用", 6: "硬件故障",
    7: "媒体断开", 8: "认证中", 9: "认证成功",
    10: "认证失败", 11: "地址无效", 12: "需要凭据",
}


class NetworkDevicesPage(TabPageInterface):
    page_id = "network_devices"
    page_name = "网络与设备"
    page_icon = CustomFluentIcon.NETFW

    @classmethod
    def create(cls, parent=None, core=None):
        return _NetworkDevicesWidget(parent, core=core)


class _NetworkDevicesWidget(BaseHardwarePage):
    page_id = "network_devices"
    page_name = "网络与设备"
    page_title = "网络与设备"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        nic_rows = wmi_query(
            wmi,
            "SELECT Name, AdapterType, MACAddress, NetConnectionID, "
            "NetConnectionStatus, Speed, Manufacturer FROM Win32_NetworkAdapter "
            "WHERE (PhysicalAdapter = TRUE) OR (NetConnectionStatus IS NOT NULL)",
        )
        if nic_rows:
            rows: List[Any] = []
            for n in nic_rows:
                status = _NET_STATUS.get(
                    n.get("NetConnectionStatus"),
                    fmt_str(n.get("NetConnectionStatus")),
                )
                speed = n.get("Speed")
                speed_str = fmt_int(speed, " bps") if speed else "N/A"
                rows.append((
                    n.get("Name"),
                    f"{fmt_str(n.get('AdapterType'))} | MAC: {fmt_str(n.get('MACAddress'))} | "
                    f"{status} | {speed_str}",
                ))
            groups.append({"title": "网络适配器", "rows": rows})

        bt_rows = wmi_query(
            wmi,
            "SELECT Name, Manufacturer, Status FROM Win32_PnPEntity "
            "WHERE Name LIKE '%Bluetooth%'",
        )
        if bt_rows:
            groups.append({
                "title": "蓝牙",
                "rows": [(b.get("Name"), fmt_str(b.get("Status"))) for b in bt_rows],
            })

        audio_rows = wmi_query(
            wmi,
            "SELECT Name, Manufacturer, Status FROM Win32_SoundDevice",
        )
        if audio_rows:
            groups.append({
                "title": "音频设备",
                "rows": [(a.get("Name"), fmt_str(a.get("Status"))) for a in audio_rows],
            })

        usb_rows = wmi_query(
            wmi,
            "SELECT Name, DeviceID, Status FROM Win32_USBHub",
        )
        if usb_rows:
            groups.append({
                "title": "USB 控制器",
                "rows": [(u.get("Name"), fmt_str(u.get("Status"))) for u in usb_rows],
            })

        cam_rows = wmi_query(
            wmi,
            "SELECT Name, Status FROM Win32_PnPEntity "
            "WHERE (PNPClass = 'Camera') OR (PNPClass = 'Image') "
            "OR (Name LIKE '%Camera%')",
        )
        if cam_rows:
            groups.append({
                "title": "摄像头",
                "rows": [(c.get("Name"), fmt_str(c.get("Status"))) for c in cam_rows],
            })

        return {"groups": groups}
