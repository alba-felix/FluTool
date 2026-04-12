from .base import BaseRepository, TableConfig


class ColorRepository(BaseRepository):
    """颜色调色板仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='color_palette',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['name', 'color_hex', 'color_rgb', 'notes'],
            allowed_fields=['plugin_id', 'category_id', 'name', 'color_hex', 'color_rgb', 'color_argb', 'notes', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, color_hex: str) -> bool:
        """检查颜色是否已存在"""
        sql = "SELECT 1 FROM color_palette WHERE plugin_id = ? AND color_hex = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, color_hex))
            return cursor.fetchone() is not None
