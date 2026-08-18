"""AI 助手插件"""

from PyQt5.QtWidgets import QWidget
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface, SearchResult
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

    def supports_search(self) -> bool:
        """启用全局搜索支持"""
        return True

    def search(self, query: str):
        """全局搜索历史对话（按标题匹配）"""
        if not query or not query.strip():
            return []

        from .service import AIAssistantService

        results = []
        for conv in AIAssistantService().search_conversations(query, limit=20):
            conv_id = conv.get('id')
            if conv_id is None:
                continue
            updated_at = str(conv.get('updated_at') or '')
            results.append(SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=conv.get('title') or '新会话',
                description=f"更新于 {updated_at[:19]}" if updated_at else '',
                icon=self.PLUGIN_ICON,
                relevance=1.0,
                action=lambda cid=conv_id: self._open_conversation(cid),
                metadata={'conversation_id': conv_id}
            ))
        return results

    def _open_conversation(self, conversation_id) -> None:
        """切换到 AI 助手页面并打开指定会话"""
        if conversation_id is None:
            return
        # 界面未创建时通过 plugin_host 构建到主窗口容器，避免产生无父级的浮动 widget
        if not self.is_widget_created():
            main_window = getattr(self.core, 'main_window', None)
            plugin_host = getattr(main_window, '_plugin_host', None) if main_window else None
            if plugin_host is not None:
                plugin_host.build_plugin_widget(self.PLUGIN_ID)
        widget = self.get_widget()
        if widget is None:
            return
        widget.select_conversation(int(conversation_id))
