from .base import BaseRepository, TableConfig


class BookmarkRepository(BaseRepository):
    """书签仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='bookmarks',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['name', 'url', 'notes'],
            allowed_fields=['plugin_id', 'category_id', 'name', 'url', 'icon', 'notes', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, url: str) -> bool:
        """检查书签是否已存在"""
        sql = "SELECT 1 FROM bookmarks WHERE plugin_id = ? AND url = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, url))
            return cursor.fetchone() is not None
