from .base import BaseRepository, TableConfig


class ScriptRepository(BaseRepository):
    """脚本仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='scripts',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['name', 'content', 'description', 'script_type'],
            allowed_fields=['plugin_id', 'category_id', 'name', 'script_type', 'content', 'description', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, name: str) -> bool:
        """检查脚本是否已存在"""
        sql = "SELECT 1 FROM scripts WHERE plugin_id = ? AND name = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, name))
            return cursor.fetchone() is not None
