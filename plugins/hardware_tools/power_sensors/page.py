"""电源与传感器页面（电池 / 温度 / 风扇）"""
from typing import Any, Dict, List

from qfluentwidgets import FluentIcon as FIF

from ..page_interface import TabPageInterface
from ..utils import (
    BaseHardwarePage, wmi_query, fmt_str, fmt_int,
)

_CHEMISTRY = {
    1: "其它", 2: "未知", 3: "铅酸", 4: "镍镉", 5: "镍氢",
    6: "锂离子", 7: "锂聚合物", 8: "智能电池", 9: "镍锌",
    10: "锂铁", 11: "钠离子",
}

_BATTERY_STATUS = {
    1: "放电", 2: "外接电源", 3: "充满/外接", 4: "低电量",
    5: "临界", 6: "充电", 7: "充电中且高", 8: "充电中且低",
    9: "充电中且临界", 10: "未定义", 11: "部分充电",
}


class PowerSensorsPage(TabPageInterface):
    page_id = "power_sensors"
    page_name = "电源与传感器"
    page_icon = FIF.POWER_BUTTON

    @classmethod
    def create(cls, parent=None, core=None):
        return _PowerSensorsWidget(parent, core=core)


class _PowerSensorsWidget(BaseHardwarePage):
    page_id = "power_sensors"
    page_name = "电源与传感器"
    page_title = "电源与传感器"

    def build_data(self, wmi: Any) -> Dict[str, Any]:
        groups: List[Dict[str, Any]] = []

        battery_rows = wmi_query(
            wmi,
            "SELECT Name, BatteryStatus, EstimatedChargeRemaining, "
            "EstimatedRunTime, DesignCapacity, FullChargeCapacity, "
            "Chemistry, Status, PowerManagementSupported "
            "FROM Win32_Battery",
        )
        if battery_rows:
            for i, b in enumerate(battery_rows, 1):
                chem = _CHEMISTRY.get(b.get("Chemistry"), fmt_str(b.get("Chemistry")))
                status = _BATTERY_STATUS.get(
                    b.get("BatteryStatus"), fmt_str(b.get("BatteryStatus"))
                )
                groups.append({
                    "title": f"电池 #{i}" if len(battery_rows) > 1 else "电池",
                    "rows": [
                        ("名称", b.get("Name")),
                        ("状态", status),
                        ("剩余电量", fmt_int(b.get("EstimatedChargeRemaining"), " %")),
                        ("预计续航", fmt_int(b.get("EstimatedRunTime"), " 分钟")),
                        ("设计容量", fmt_int(b.get("DesignCapacity"), " mWh")),
                        ("满电容量", fmt_int(b.get("FullChargeCapacity"), " mWh")),
                        ("化学类型", chem),
                        ("电源管理", "支持" if str(b.get("PowerManagementSupported")) == "True" else "不支持"),
                    ],
                })
        else:
            groups.append({
                "title": "电池",
                "rows": [("状态", "未检测到电池（可能为台式机）")],
            })

        temp_rows = wmi_query(
            wmi,
            "SELECT Name, CurrentReading, Status FROM Win32_TemperatureProbe",
        )
        if temp_rows:
            rows = []
            for t in temp_rows:
                reading = t.get("CurrentReading")
                temp_str = f"{fmt_int(reading, ' °C')}" if reading is not None else "N/A"
                rows.append((t.get("Name"), temp_str))
            groups.append({"title": "温度传感器", "rows": rows})
        else:
            groups.append({
                "title": "温度传感器",
                "rows": [("状态", "WMI 未提供温度数据")],
            })

        fan_rows = wmi_query(
            wmi,
            "SELECT Name, Status, VariableSpeed, DesiredSpeed FROM Win32_Fan",
        )
        if fan_rows:
            rows = [(f.get("Name"), fmt_str(f.get("Status"))) for f in fan_rows]
            groups.append({"title": "风扇", "rows": rows})
        else:
            groups.append({
                "title": "风扇",
                "rows": [("状态", "WMI 未提供风扇数据")],
            })

        return {"groups": groups}
