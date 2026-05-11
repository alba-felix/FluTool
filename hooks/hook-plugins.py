"""PyInstaller hook for FluTool builtin plugins."""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("plugins")
