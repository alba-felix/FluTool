from .base import BaseRepository, TableConfig


class CommandRepository(BaseRepository):
    """命令仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='commands',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['name', 'sub_title', 'content'],
            allowed_fields=['plugin_id', 'category_id', 'name', 'sub_title', 'content', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, name: str, category_name: str = None) -> bool:
        """检查命令是否已存在"""
        if category_name:
            sql = """
                SELECT 1 FROM commands c
                JOIN categories cat ON c.category_id = cat.id
                WHERE c.plugin_id = ? AND c.name = ? AND cat.name = ?
            """
            params = (plugin_id, name, category_name)
        else:
            sql = "SELECT 1 FROM commands WHERE plugin_id = ? AND name = ?"
            params = (plugin_id, name)
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone() is not None
