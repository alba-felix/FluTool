from typing import Optional, List, Dict, Any
from .base import BaseRepository, TableConfig


class NotebookRepository(BaseRepository):
    """笔记本仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='notebook',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['title', 'content'],
            allowed_fields=['plugin_id', 'category_id', 'title', 'content', 'note_type', 'sort_order', 'color']
        )
        super().__init__(db_manager, config)
    
    def exists(self, plugin_id: str, title: str) -> bool:
        """检查笔记是否存在"""
        sql = "SELECT 1 FROM notebook WHERE plugin_id = ? AND title = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, title))
            return cursor.fetchone() is not None
    
    def get_by_plugin(self, plugin_id: str, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """根据插件 ID 获取笔记列表"""
        if category_id is not None:
            sql = """
                SELECT n.*, c.name as category_name 
                FROM notebook n 
                LEFT JOIN categories c ON n.category_id = c.id 
                WHERE n.plugin_id = ? AND n.category_id = ?
                ORDER BY n.sort_order, n.id DESC
            """
            params = (plugin_id, category_id)
        else:
            sql = """
                SELECT n.*, c.name as category_name 
                FROM notebook n 
                LEFT JOIN categories c ON n.category_id = c.id 
                WHERE n.plugin_id = ?
                ORDER BY n.sort_order, n.id DESC
            """
            params = (plugin_id,)
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def search(self, plugin_id: str, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索笔记"""
        sql = """
            SELECT n.*, c.name as category_name 
            FROM notebook n 
            LEFT JOIN categories c ON n.category_id = c.id 
            WHERE n.plugin_id = ? AND (n.title LIKE ? OR n.content LIKE ?)
            ORDER BY n.sort_order, n.id DESC
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, f'%{keyword}%', f'%{keyword}%', limit))
            return [dict(row) for row in cursor.fetchall()]
