from typing import List, Optional

from storage import DatabaseManager


class BookmarkService:
    """书签业务服务，隔离插件界面与数据库访问"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def list_categories(self) -> List[dict]:
        """获取当前插件的分类列表"""
        return self.db.get_categories(self.plugin_id)

    def add_category(self, name: str) -> int:
        """添加分类"""
        return self.db.add_category(self.plugin_id, name)

    def rename_category(self, category_id: int, name: str) -> bool:
        """重命名分类"""
        return self.db.update_category(self.plugin_id, category_id, name)

    def delete_category(self, category_id: int) -> bool:
        """删除分类"""
        return self.db.delete_category(self.plugin_id, category_id)

    def list_bookmarks(self, category_id: Optional[int] = None) -> List[dict]:
        """获取书签列表"""
        return self.db.get_bookmarks(self.plugin_id, category_id)

    def add_bookmark(
        self,
        name: str,
        url: str,
        category_name: Optional[str] = None,
        icon: str = "",
        notes: str = "",
    ) -> int:
        """添加书签"""
        return self.db.add_bookmark(
            plugin_id=self.plugin_id,
            name=name,
            url=url,
            category_name=category_name,
            icon=icon,
            notes=notes,
        )

    def update_bookmark(self, bookmark_id: int, **kwargs) -> bool:
        """更新书签"""
        return self.db.update_bookmark(self.plugin_id, bookmark_id, **kwargs)

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """删除书签"""
        return self.db.delete_bookmark(self.plugin_id, bookmark_id)

    def search(self, query: str) -> List[dict]:
        """搜索书签"""
        return self.db.search_bookmarks(self.plugin_id, query)
