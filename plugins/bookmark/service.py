from typing import List, Optional

from PyQt5.QtCore import QUrl

from storage import DatabaseManager


class BookmarkService:
    """书签业务服务，隔离插件界面与数据库访问"""

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

    def list_categories(self) -> List[dict]:
        """获取当前插件的分类列表"""
        return self.db.categories.get_by_plugin(self.plugin_id)

    def add_category(self, name: str) -> int:
        """添加分类"""
        return self.db.categories.add_or_get(self.plugin_id, name)

    def rename_category(self, category_id: int, name: str) -> bool:
        """重命名分类"""
        return self.db.categories.update(category_id, name=name)

    def delete_category(self, category_id: int) -> bool:
        """删除分类"""
        return self.db.categories.delete(category_id)

    def list_bookmarks(self, category_id: Optional[int] = None) -> List[dict]:
        """获取书签列表"""
        return self.db.bookmarks.get_by_plugin(self.plugin_id, category_id)

    def add_bookmark(
        self,
        name: str,
        url: str,
        category_name: Optional[str] = None,
        icon: str = "",
        notes: str = "",
    ) -> int:
        """添加书签"""
        category_id = self._resolve_category_id(category_name)
        return self.db.bookmarks.add(
            plugin_id=self.plugin_id,
            category_id=category_id,
            name=name,
            url=url,
            icon=icon,
            notes=notes,
            sort_order=0,
        )

    def update_bookmark(self, bookmark_id: int, **kwargs) -> bool:
        """更新书签"""
        return self.db.bookmarks.update(bookmark_id, **kwargs)

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """删除书签"""
        return self.db.bookmarks.delete(bookmark_id)

    def batch_delete_bookmarks(self, bookmark_ids: List[int]) -> bool:
        """批量删除书签"""
        success = True
        for bm_id in bookmark_ids:
            if not self.delete_bookmark(bm_id):
                success = False
        return success

    def category_name_exists(self, name: str) -> bool:
        """检查分类名称是否已存在"""
        return any(c['name'] == name for c in self.list_categories())

    def normalize_url(self, url: str) -> str:
        """规范化URL，仅补协议，不强制添加 www 前缀"""
        url = url.strip()
        if not url:
            return ""

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        qurl = QUrl(url)
        if not qurl.isValid() or not qurl.host():
            return ""

        return url

    def search(self, query: str) -> List[dict]:
        """搜索书签"""
        return self.db.bookmarks.search(self.plugin_id, query)
