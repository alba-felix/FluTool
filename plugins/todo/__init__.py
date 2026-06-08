"""代办事项插件"""

from PyQt5.QtWidgets import QWidget, QApplication
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface, SearchResult
from .service import TodoService
from .widget import TodoWidget


class Plugin(PluginInterface):
    """代办事项插件"""

    PLUGIN_ID = "todo"
    PLUGIN_NAME = "代办事项"
    PLUGIN_ICON = FIF.CALENDAR
    PLUGIN_PRIORITY = 11

    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return TodoWidget(self.core, parent)

    def load_data(self) -> None:
        """加载数据"""
        if self._widget:
            self._widget.load_data()

    def supports_search(self) -> bool:
        return True

    def search(self, query: str):
        results = []
        todos = TodoService().search(query)
        for todo in todos[:20]:
            completed = todo.get('completed', False)
            todo_status = todo.get('status', '')
            if completed:
                status = "已完成"
            elif todo_status == "未完成":
                status = "未完成"
            else:
                status = "进行中"
            pinned = "" if not todo['pinned'] else ""
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=f"{status} {todo['title']}",
                description=f"优先级: {todo['priority']} | 截止: {todo['due_date'] or '无'}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if todo['pinned'] else 0.8,
                action=lambda t=todo['title']: QApplication.clipboard().setText(t),
                metadata={'todo_id': todo['id']}
            )
            results.append(result)
        return results
