import sys
import ctypes
from ctypes import wintypes
from typing import Optional

kernel32 = ctypes.windll.kernel32

PROCESS_POWER_THROTTLING_CURRENT_VERSION = 1
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1

ProcessPowerThrottling = 4

IDLE_PRIORITY_CLASS = 0x40
NORMAL_PRIORITY_CLASS = 0x20


class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.ULONG),
        ("ControlMask", wintypes.ULONG),
        ("StateMask", wintypes.ULONG),
    ]


def set_process_efficiency_mode(enabled: bool, logger=None) -> bool:
    """
    设置当前进程的效能模式
    
    Args:
        enabled: True 启用效能模式，False 禁用效能模式
        logger: 可选的日志记录器
    
    Returns:
        是否设置成功
    """
    if sys.platform != 'win32':
        if logger:
            logger.warning("Efficiency mode not supported on non-Windows platform")
        return False
    
    try:
        h_process = kernel32.GetCurrentProcess()
        
        power_throttling = PROCESS_POWER_THROTTLING_STATE()
        power_throttling.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
        power_throttling.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
        power_throttling.StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED if enabled else 0
        
        SetProcessInformation = kernel32.SetProcessInformation
        SetProcessInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.ULONG
        ]
        SetProcessInformation.restype = wintypes.BOOL
        
        result = SetProcessInformation(
            h_process,
            ProcessPowerThrottling,
            ctypes.byref(power_throttling),
            ctypes.sizeof(power_throttling)
        )
        
        if not result:
            error = ctypes.get_last_error()
            if logger:
                logger.error(f"SetProcessInformation failed with error: {error}")
            return False
        
        SetPriorityClass = kernel32.SetPriorityClass
        SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        SetPriorityClass.restype = wintypes.BOOL
        
        priority = IDLE_PRIORITY_CLASS if enabled else NORMAL_PRIORITY_CLASS
        result = SetPriorityClass(h_process, priority)
        
        if not result:
            error = ctypes.get_last_error()
            if logger:
                logger.error(f"SetPriorityClass failed with error: {error}")
            return False
        
        return True
    
    except Exception as e:
        if logger:
            logger.error(f"Exception in set_process_efficiency_mode: {e}")
        return False


def is_efficiency_mode_supported() -> bool:
    """
    检查系统是否支持效能模式
    
    Returns:
        是否支持效能模式
    """
    if sys.platform != 'win32':
        return False
    
    try:
        version = sys.getwindowsversion()
        return version.major >= 10 and version.build >= 21359
    except Exception:
        return False


def get_current_efficiency_mode() -> Optional[bool]:
    """
    获取当前进程的效能模式状态
    
    Returns:
        True 启用，False 禁用，None 无法获取
    """
    if sys.platform != 'win32':
        return None
    
    try:
        h_process = kernel32.GetCurrentProcess()
        
        power_throttling = PROCESS_POWER_THROTTLING_STATE()
        power_throttling.Version = PROCESS_POWER_THROTTLING_CURRENT_VERSION
        
        GetProcessInformation = kernel32.GetProcessInformation
        GetProcessInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.ULONG
        ]
        GetProcessInformation.restype = wintypes.BOOL
        
        result = GetProcessInformation(
            h_process,
            ProcessPowerThrottling,
            ctypes.byref(power_throttling),
            ctypes.sizeof(power_throttling)
        )
        
        if not result:
            return None
        
        return bool(power_throttling.StateMask & PROCESS_POWER_THROTTLING_EXECUTION_SPEED)
    
    except Exception:
        return None
