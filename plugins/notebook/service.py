"""随手记插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class NotebookService:
    """封装随手记插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def _resolve_category_id(self, category_name: Optional[str]) -> Optional[int]:
        """根据分类名称解析分类ID"""
        if not category_name:
            return None
        for cat in self.db.categories.get_by_plugin(self.plugin_id):
            if cat["name"] == category_name:
                return cat["id"]
        return None

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
        category_id = self._resolve_category_id(category_name)
        return self.db.notebooks.add(
            plugin_id=self.plugin_id,
            category_id=category_id,
            title=title,
            content=content,
            note_type=note_type,
            sort_order=sort_order,
            color=color,
        )

    def note_exists(self, title: str) -> bool:
        """检查笔记标题是否存在。"""
        return self.db.notebooks.exists(self.plugin_id, title)

    def list_notes(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取笔记列表。"""
        return self.db.notebooks.get_by_plugin(self.plugin_id, category_id)

    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取当前插件的笔记。"""
        for note in self.list_notes():
            if note["id"] == note_id:
                return note
        return None

    def update_note(self, note_id: int, **kwargs) -> bool:
        """更新笔记。"""
        return self.db.notebooks.update(note_id, **kwargs)

    def delete_note(self, note_id: int) -> bool:
        """删除笔记。"""
        return self.db.notebooks.delete(note_id)

    def search_notes(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索笔记。"""
        return self.db.notebooks.search(self.plugin_id, keyword, limit)
