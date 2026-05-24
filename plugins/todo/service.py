from typing import Dict, List, Optional

from storage import DatabaseManager


class TodoService:
    """待办事项业务服务，隔离界面与数据库访问"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def list_todos(self, completed: Optional[int] = None) -> List[dict]:
        """获取待办事项列表"""
        return self.db.get_todos(completed)

    def add_todo(self, todo_data: Dict) -> int:
        """根据界面数据添加待办事项"""
        return self.db.add_todo(
            title=todo_data["title"],
            description=todo_data.get("description", ""),
            priority=todo_data.get("priority", "中"),
            start_date=todo_data.get("start_date", ""),
            due_date=todo_data.get("due_date", ""),
            tags=todo_data.get("tags", []),
            completed=1 if todo_data.get("completed", False) else 0,
            pinned=1 if todo_data.get("pinned", False) else 0,
            status=todo_data.get("status", "进行中"),
            remind_before=todo_data.get("remind_before", 0),
            last_reminded=todo_data.get("last_reminded", ""),
            due_time=todo_data.get("due_time", "23:59"),
        )

    def update_todo(self, todo_id: int, todo_data: Dict) -> bool:
        """根据界面数据更新待办事项"""
        return self.db.update_todo(
            todo_id,
            title=todo_data["title"],
            description=todo_data.get("description", ""),
            priority=todo_data.get("priority", "中"),
            start_date=todo_data.get("start_date", ""),
            due_date=todo_data.get("due_date", ""),
            tags=todo_data.get("tags", []),
            completed=1 if todo_data.get("completed", False) else 0,
            pinned=1 if todo_data.get("pinned", False) else 0,
            status=todo_data.get("status", "进行中"),
            remind_before=todo_data.get("remind_before", 0),
            last_reminded=todo_data.get("last_reminded", ""),
            due_time=todo_data.get("due_time", "23:59"),
        )

    def update_fields(self, todo_id: int, **kwargs) -> bool:
        """更新指定字段"""
        return self.db.update_todo(todo_id, **kwargs)

    def delete_todo(self, todo_id: int) -> bool:
        """删除待办事项"""
        return self.db.delete_todo(todo_id)

    def toggle_completed(self, todo_id: int) -> bool:
        """切换完成状态"""
        return self.db.toggle_todo_completed(todo_id)

    def toggle_pinned(self, todo_id: int) -> bool:
        """切换置顶状态"""
        return self.db.toggle_todo_pinned(todo_id)

    def search(self, query: str) -> List[dict]:
        """搜索待办事项"""
        return self.db.search_todos(query)
