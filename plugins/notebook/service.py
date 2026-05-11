"""随手记插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class NotebookService:
    """封装随手记插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def add_note(
        self,
        title: str,
        content: str,
        category_name: str = None,
        note_type: str = "markdown",
        sort_order: int = 0,
        color: str = None,
    ) -> int:
        """添加笔记。"""
        return self.db.add_note(
            plugin_id=self.plugin_id,
            title=title,
            content=content,
            category_name=category_name,
            note_type=note_type,
            sort_order=sort_order,
            color=color,
        )

    def note_exists(self, title: str) -> bool:
        """检查笔记标题是否存在。"""
        return self.db.note_exists(self.plugin_id, title)

    def list_notes(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取笔记列表。"""
        return self.db.get_notes(self.plugin_id, category_id)

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取当前插件的笔记。"""
        for note in self.list_notes():
            if note["id"] == note_id:
                return note
        return None

    def update_note(self, note_id: int, **kwargs) -> bool:
        """更新笔记。"""
        return self.db.update_note(self.plugin_id, note_id, **kwargs)

    def delete_note(self, note_id: int) -> bool:
        """删除笔记。"""
        return self.db.delete_note(self.plugin_id, note_id)

    def search_notes(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索笔记。"""
        return self.db.search_notes(self.plugin_id, keyword, limit)
