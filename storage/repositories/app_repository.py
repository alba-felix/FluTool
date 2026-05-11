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
            allowed_fields=[
                'plugin_id', 'category_id', 'name', 'icon_path', 'target_path',
                'arguments', 'notes', 'sort_order', 'launch_count',
                'last_launch_time', 'is_favorite'
            ]
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, name: str, target_path: str) -> bool:
        """检查应用是否已存在"""
        sql = "SELECT 1 FROM app_launcher WHERE plugin_id = ? AND name = ? AND target_path = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, name, target_path))
            return cursor.fetchone() is not None

    def batch_update(self, plugin_id: str, app_ids: list, **kwargs) -> int:
        """批量更新应用"""
        allowed_fields = {'category_id', 'arguments', 'notes', 'is_favorite', 'sort_order', 'name', 'icon_path', 'target_path'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not filtered or not app_ids:
            return 0

        set_clause = ', '.join(f"{field} = ?" for field in filtered.keys())
        placeholders = ', '.join('?' for _ in app_ids)
        sql = f"""
            UPDATE app_launcher
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE plugin_id = ? AND id IN ({placeholders})
        """
        params = list(filtered.values()) + [plugin_id] + list(app_ids)

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount

    def batch_delete(self, plugin_id: str, app_ids: list) -> int:
        """批量删除应用"""
        if not app_ids:
            return 0

        placeholders = ', '.join('?' for _ in app_ids)
        sql = f"DELETE FROM app_launcher WHERE plugin_id = ? AND id IN ({placeholders})"

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, [plugin_id] + list(app_ids))
            conn.commit()
            return cursor.rowcount
