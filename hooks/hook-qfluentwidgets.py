"""PyInstaller hook for QFluentWidgets."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 收集所有子模块
hiddenimports = collect_submodules("qfluentwidgets")

# 收集资源文件（特别是 _rc 目录中的图标资源）
datas = collect_data_files("qfluentwidgets", include_py_files=True)
