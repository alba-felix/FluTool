"""机器码生成模块 - 基于硬件信息生成唯一机器标识"""

import hashlib
import platform
import uuid
from typing import List


def _get_cpu_info() -> str:
    """获取 CPU 信息"""
    try:
        import wmi
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            return f"{cpu.ProcessorId}{cpu.Name}{cpu.Manufacturer}"
    except Exception:
        pass
    return platform.processor() or ""


def _get_mac_addresses() -> str:
    """获取 MAC 地址"""
    try:
        mac = uuid.getnode()
        if mac is not None:
            return hex(mac)
    except Exception:
        pass
    return ""


def _get_computer_name() -> str:
    """获取计算机名"""
    return platform.node() or ""


def _get_volume_serial() -> str:
    """获取系统盘卷序列号"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        volume_name_buffer = ctypes.create_unicode_buffer(256)
        file_system_name_buffer = ctypes.create_unicode_buffer(256)
        serial_number = ctypes.c_ulong()
        kernel32.GetVolumeInformationW(
            "C:\\",
            volume_name_buffer,
            ctypes.sizeof(volume_name_buffer),
            ctypes.byref(serial_number),
            None,
            None,
            file_system_name_buffer,
            ctypes.sizeof(file_system_name_buffer),
        )
        return str(serial_number.value)
    except Exception:
        return ""


def _get_hardware_components() -> List[str]:
    """获取所有硬件信息组件列表"""
    components = [
        _get_cpu_info(),
        _get_mac_addresses(),
        _get_computer_name(),
        _get_volume_serial(),
    ]
    return [c for c in components if c]


def generate_machine_code() -> str:
    """生成唯一机器码

    基于 CPU、MAC 地址、计算机名、卷序列号生成。
    同一台机器每次生成的代码相同，重装系统后 MAC 和 CPU ID 不变则保持一致。

    Returns:
        SHA-256 哈希后的 64 位十六进制机器码
    """
    components = _get_hardware_components()
    raw = "|".join(components)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_machine_short_code(length: int = 16) -> str:
    """生成缩短后的机器码，适合 UI 展示"""
    full = generate_machine_code()
    return full[:length].upper()