from .base import BaseRepository, TableConfig


class PasswordRepository(BaseRepository):
    """密码仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='passwords',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['platform', 'username', 'email', 'notes'],
            allowed_fields=['plugin_id', 'category_id', 'platform', 'username', 'password', 'email', 'notes', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, username: str, password: str) -> bool:
        """检查密码是否已存在"""
        sql = "SELECT 1 FROM passwords WHERE plugin_id = ? AND username = ? AND password = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, username, password))
            return cursor.fetchone() is not None
