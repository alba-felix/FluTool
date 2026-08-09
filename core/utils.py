import sys
from pathlib import Path
import os


APP_NAME = "FluTool"


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径
    
    开发环境：返回项目根目录下的路径
    打包后：返回 PyInstaller 解压目录下的路径
    
    Args:
        relative_path: 相对路径，如 "data/data.db"
        
    Returns:
        绝对路径
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    
    return base_path / relative_path


def get_app_data_path(relative_path: str) -> Path:
    """
    获取应用数据路径（可读写）

    打包后：返回程序所在目录下的路径
    开发环境：返回项目根目录下的路径

    Args:
        relative_path: 相对路径，如 "data/data.db"

    Returns:
        绝对路径
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent

    return base_path / relative_path


def get_local_app_data_dir() -> Path:
    """
    获取应用数据目录

    Returns:
        程序所在目录下的 FluTool 路径
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def set_auto_start(enabled: bool) -> None:
    """设置开机自启（Windows 注册表）"""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "FluTool"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE) as key:
            if enabled:
                if getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}" --minimized'
                else:
                    exe_path = f'"{Path(__file__).resolve().parent.parent / "main.py"}" --minimized'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"[utils] Auto-start setup failed: {e}")


def set_explorer_context_menu(enabled: bool) -> None:
    """
    设置资源管理器右键菜单（文件夹背景右键）

    Args:
        enabled: True 添加菜单项，False 移除菜单项
    """
    try:
        import winreg
        menu_name = "FluTool 文件夹备注"
        key_path = r"Directory\Background\shell"
        full_key = f"{key_path}\\{menu_name}"

        if getattr(sys, 'frozen', False):
            exe_path = f'"{sys.executable}" --filecomment "%V"'
        else:
            main_py = Path(__file__).resolve().parent.parent / "main.py"
            exe_path = f'"{sys.executable}" "{main_py}" --filecomment "%V"'

        # 图标：优先 logo.ico，其次资源目录的 icon.ico，缺失时省略图标项
        icon_path = Path(__file__).resolve().parent.parent / "logo.ico"
        if not icon_path.exists():
            icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
        icon = str(icon_path) if icon_path.exists() else None

        # CreateKey 会在路径不存在时自动创建（部分精简系统缺少该键）
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            if enabled:
                sub_key = winreg.CreateKey(key, menu_name)
                winreg.SetValueEx(sub_key, "MUIVerb", 0, winreg.REG_SZ, menu_name)
                if icon:
                    winreg.SetValueEx(sub_key, "Icon", 0, winreg.REG_SZ, icon)
                cmd_key = winreg.CreateKey(sub_key, "command")
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(cmd_key)
                winreg.CloseKey(sub_key)
            else:
                try:
                    winreg.DeleteKey(key, f"{menu_name}\\command")
                    winreg.DeleteKey(key, menu_name)
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"[utils] Explorer context menu setup failed: {e}")


def is_explorer_context_menu_enabled() -> bool:
    """检查资源管理器右键菜单是否已启用"""
    try:
        import winreg
        menu_name = "FluTool 文件夹备注"
        key_path = r"Directory\Background\shell"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
            try:
                winreg.OpenKey(key, menu_name)
                return True
            except FileNotFoundError:
                return False
    except Exception:
        return False
