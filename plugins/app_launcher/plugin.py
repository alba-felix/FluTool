"""应用启动插件入口"""
import os
import sys
import subprocess
from typing import Dict, Any

PLUGIN_MANIFEST = {
    "id": "app_launcher",
    "name": "应用启动",
    "priority": 12,
}

from PyQt5.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface, SearchResult
from plugins.app_launcher.service import AppLauncherService

from .utils import get_python_executable
from .widget import AppLauncherWidget


class Plugin(PluginInterface):
    """应用启动插件"""

    PLUGIN_ID = "app_launcher"
    PLUGIN_NAME = "应用启动"
    PLUGIN_ICON = FIF.APPLICATION
    PLUGIN_PRIORITY = 12

    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return AppLauncherWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        self._widget.load_data()

    def supports_search(self) -> bool:
        """支持全局搜索"""
        return True

    def search(self, query: str):
        """搜索应用"""
        service = AppLauncherService(self.PLUGIN_ID)
        results = []
        apps = service.search_apps(query)
        for app in apps[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=app['name'],
                description=app.get('target_path', ''),
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in app['name'].lower() else 0.5,
                action=lambda a=app: self._launch_app(a),
                metadata={'app_id': app['id']}
            )
            results.append(result)
        return results

    def _launch_app(self, app: Dict[str, Any]) -> None:
        """启动应用（全局搜索调用）"""
        target_path = app.get('target_path', '')
        if not target_path or not os.path.exists(target_path):
            return
        arguments = app.get('arguments', '') or ''

        if os.path.isdir(target_path):
            os.startfile(target_path)
            return

        ext = os.path.splitext(target_path)[1].lower()

        if ext == '.py':
            if getattr(sys, 'frozen', False):
                cmd = f'"{sys.executable}" --run-script "{target_path}"'
            else:
                python_exe = get_python_executable()
                cmd = f'"{python_exe}" "{target_path}"'
            if arguments:
                cmd += f' {arguments}'
            subprocess.Popen(cmd, shell=True)
        elif ext in ('.bat', '.cmd'):
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'"{target_path}"', shell=True)
        elif ext == '.ps1':
            if arguments:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{target_path}"', shell=True)
        elif ext == '.vbs':
            if arguments:
                subprocess.Popen(f'wscript "{target_path}" {arguments}', shell=True)
            else:
                subprocess.Popen(f'wscript "{target_path}"', shell=True)
        else:
            if arguments:
                subprocess.Popen(f'"{target_path}" {arguments}', shell=True)
            else:
                os.startfile(target_path)
