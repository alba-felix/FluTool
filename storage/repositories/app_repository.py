from .base import BaseRepository, TableConfig


class AppRepository(BaseRepository):
    """应用启动器仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='app_launcher',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['name', 'target_path', 'notes'],
            allowed_fields=['plugin_id', 'category_id', 'name', 'icon_path', 'target_path', 'arguments', 'notes', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, name: str, target_path: str) -> bool:
        """检查应用是否已存在"""
        sql = "SELECT 1 FROM app_launcher WHERE plugin_id = ? AND name = ? AND target_path = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, name, target_path))
            return cursor.fetchone() is not None
