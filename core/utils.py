import sys
from pathlib import Path


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
    
    打包后：返回 exe 所在目录下的路径
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
