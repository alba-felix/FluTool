from typing import List, Dict, Any
from .base import BaseRepository, TableConfig


class ClipboardRepository(BaseRepository):
    """剪贴板历史仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='clipboard_history',
            primary_key='id',
            plugin_field=None,  # 剪贴板历史没有 plugin_id 字段
            has_category=False,
            searchable_fields=['content'],
            allowed_fields=['item_type', 'content', 'format']
        )
        super().__init__(db_manager, config)
    
    def add(self, item_type: str, content: str, format: str = '') -> int:
        """添加剪贴板历史项"""
        sql = """
            INSERT INTO clipboard_history (plugin_id, content_type, item_type, content, format) 
            VALUES (?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, ('clipboard', item_type, item_type, content, format))
            conn.commit()
            return cursor.lastrowid
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取剪贴板历史"""
        sql = """
            SELECT id, item_type as type, content, format, timestamp 
            FROM clipboard_history 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def clear(self) -> bool:
        """清空剪贴板历史"""
        sql = "DELETE FROM clipboard_history"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete(self, item_id: int) -> bool:
        """删除剪贴板历史项"""
        sql = "DELETE FROM clipboard_history WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (item_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索剪贴板历史"""
        sql = """
            SELECT id, item_type as type, content, format, timestamp 
            FROM clipboard_history 
            WHERE content LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (f'%{keyword}%', limit))
            return [dict(row) for row in cursor.fetchall()]
