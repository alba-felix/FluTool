from typing import Optional, List, Dict, Any
from .base import BaseRepository, TableConfig


class CategoryRepository(BaseRepository):
    """分类仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='categories',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=False,
            searchable_fields=['name'],
            allowed_fields=['plugin_id', 'name', 'sort_order']
        )
        super().__init__(db_manager, config)
    
    def add_or_get(self, plugin_id: str, name: str, sort_order: int = 0) -> int:
        """添加分类，如果已存在则返回现有 ID"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO categories (plugin_id, name, sort_order) VALUES (?, ?, ?)",
                (plugin_id, name, sort_order)
            )
            conn.commit()
            if cursor.rowcount == 0:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, name)
                )
                row = cursor.fetchone()
                return row['id'] if row else 0
            return cursor.lastrowid
    
    def get_by_plugin(self, plugin_id: str) -> List[Dict[str, Any]]:
        """获取插件的所有分类"""
        sql = "SELECT * FROM categories WHERE plugin_id = ? ORDER BY sort_order, id"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update(self, category_id: int, **kwargs) -> bool:
        """更新分类"""
        allowed_fields = {'name', 'sort_order'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not filtered:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE categories 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        values = list(filtered.values()) + [category_id]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete(self, category_id: int) -> bool:
        """删除分类"""
        sql = "DELETE FROM categories WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (category_id,))
            conn.commit()
            return cursor.rowcount > 0
