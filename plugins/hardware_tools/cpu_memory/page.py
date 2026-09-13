"""CPU 与内存页面"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF
from ui import CustomFluentIcon

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_int, fmt_size,
)

_MEMORY_TYPE = {
    0: "未知", 1: "其它", 2: "DRAM", 3: "同步 DRAM",
    4: "缓存 DRAM", 5: "EDO", 6: "EDRAM", 7: "VRAM",
    8: "SRAM", 9: "RAM", 10: "ROM", 11: "Flash",
    12: "EEPROM", 13: "FEPROM", 14: "EPROM", 15: "CDRAM",
    16: "3DRAM", 17: "SDRAM", 18: "SGRAM", 19: "RDRAM",
    20: "DDR", 21: "DDR2", 22: "DDR2 FB-DIMM", 23: "DDR3",
    24: "FBD2", 25: "DDR4", 26: "DDR5", 27: "DDR6",
}


class CpuMemoryPage(TabPageInterface):
    page_id = "cpu_memory"
    page_name = "CPU 与内存"
    page_icon = CustomFluentIcon.SYSCONFIG

    @classmethod
    def create(cls, parent=None, core=None):
        return _CpuMemoryWidget(parent, core=core)


class _CpuMemoryWidget(BaseHardwarePage):
    page_id = "cpu_memory"
    page_name = "CPU 与内存"
    page_title = "CPU 与内存"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        cpu_rows = wmi_query(
            wmi,
            "SELECT Name, Manufacturer, MaxClockSpeed, CurrentClockSpeed, "
            "NumberOfCores, NumberOfLogicalProcessors, L2CacheSize, "
            "L3CacheSize, SocketDesignation, ProcessorId, "
            "VirtualizationFirmwareEnabled, LoadPercentage, "
            "DataWidth, AddressWidth, Status "
            "FROM Win32_Processor",
        )
        for i, c in enumerate(cpu_rows, 1):
            groups.append({
                "title": f"处理器 #{i}" if len(cpu_rows) > 1 else "处理器",
                "rows": [
                    ("名称", c.get("Name")),
                    ("厂商", c.get("Manufacturer")),
                    ("插槽", c.get("SocketDesignation")),
                    ("最大频率", fmt_int(c.get("MaxClockSpeed"), " MHz")),
                    ("当前频率", fmt_int(c.get("CurrentClockSpeed"), " MHz")),
                    ("物理核心", c.get("NumberOfCores")),
                    ("逻辑核心", c.get("NumberOfLogicalProcessors")),
                    ("L2 缓存", fmt_int(c.get("L2CacheSize"), " KB")),
                    ("L3 缓存", fmt_int(c.get("L3CacheSize"), " KB")),
                    ("位宽", fmt_int(c.get("DataWidth"), " 位")),
                    ("虚拟化", "支持" if str(c.get("VirtualizationFirmwareEnabled")) == "True" else "不支持"),
                    ("当前负载", fmt_int(c.get("LoadPercentage"), " %")),
                    ("状态", c.get("Status")),
                    ("处理器 ID", c.get("ProcessorId")),
                ],
            })

        mem_rows = wmi_query(
            wmi,
            "SELECT BankLabel, DeviceLocator, Capacity, Speed, "
            "Manufacturer, PartNumber, MemoryType FROM Win32_PhysicalMemory",
        )
        if mem_rows:
            total = 0
            for i, m in enumerate(mem_rows, 1):
                try:
                    total += int(m.get("Capacity") or 0)
                except (TypeError, ValueError):
                    pass
                mem_type = _MEMORY_TYPE.get(
                    m.get("MemoryType"), fmt_str(m.get("MemoryType"))
                )
                groups.append({
                    "title": f"内存条 #{i}" if len(mem_rows) > 1 else "内存",
                    "rows": [
                        ("位置", m.get("DeviceLocator") or m.get("BankLabel")),
                        ("容量", fmt_size(m.get("Capacity"))),
                        ("频率", fmt_int(m.get("Speed"), " MHz")),
                        ("类型", mem_type),
                        ("厂商", m.get("Manufacturer")),
                        ("部件号", m.get("PartNumber")),
                    ],
                })
            groups.append({
                "title": "内存合计",
                "rows": [
                    ("总容量", fmt_size(total)),
                    ("插槽数", str(len(mem_rows))),
                ],
            })
        else:
            cs = wmi_query(
                wmi,
                "SELECT TotalPhysicalMemory FROM Win32_ComputerSystem",
            )
            if cs:
                groups.append({
                    "title": "内存合计",
                    "rows": [("总容量", fmt_size(cs[0].get("TotalPhysicalMemory")))],
                })

        return {"groups": groups}
