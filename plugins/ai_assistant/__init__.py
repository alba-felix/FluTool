"""AI 助手插件"""

from PyQt5.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface
from .widget import AIAssistantWidget


class Plugin(PluginInterface):
    """AI 助手插件"""

    PLUGIN_ID = "ai_assistant"
    PLUGIN_NAME = "AI 助手"
    PLUGIN_ICON = FIF.ROBOT
    PLUGIN_PRIORITY = 8

    def initialize(self, core) -> None:
        self.core = core
        self.core.logger.info(f"Plugin '{self.get_name()}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return AIAssistantWidget(self.core, parent)
