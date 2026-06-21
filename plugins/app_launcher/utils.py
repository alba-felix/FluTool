"""应用启动插件工具函数"""
import sys
from pathlib import Path


def get_python_executable() -> str:
    """
    获取项目 Python 解释器路径
    开发环境：使用 .venv 中的解释器
    打包环境：使用系统 Python 或打包的解释器
    """
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
        python_exe = base_path / "python.exe"
        if python_exe.exists():
            return str(python_exe)
        python_exe = base_path / "Scripts" / "python.exe"
        if python_exe.exists():
            return str(python_exe)
        return "python"
    else:
        venv_python = Path(sys.prefix) / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable


def get_plugins_sourcecode_dir() -> Path:
    """
    获取 plugins_sourcecode 目录路径
    开发环境：项目根目录下的 plugins_sourcecode
    打包环境：_internal 目录下的 plugins_sourcecode
    """
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path.cwd()
    return base / "plugins_sourcecode"
