from typing import List, Dict, Any, Optional
import json
from .base import BaseRepository, TableConfig


class TodoRepository:
    """待办事项仓储"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add(self, title: str, description: str = '', priority: str = '中',
            start_date: str = '', due_date: str = '', tags: list = None,
            completed: int = 0, pinned: int = 0, status: str = '进行中') -> int:
        """添加待办事项"""
        tags_json = json.dumps(tags) if tags else '[]'
        sql = """
            INSERT INTO todos (title, description, priority, start_date, due_date, tags, completed, pinned, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (
                title, description, priority, start_date, due_date, 
                tags_json, completed, pinned, status
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_all(self, completed: int = None) -> List[Dict[str, Any]]:
        """获取待办事项列表"""
        if completed is not None:
            sql = """
                SELECT * FROM todos 
                WHERE completed = ? 
                ORDER BY pinned DESC, sort_order, id
            """
            params = (completed,)
        else:
            sql = """
                SELECT * FROM todos 
                ORDER BY pinned DESC, sort_order, id
            """
            params = ()
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            todos = [dict(row) for row in cursor.fetchall()]
            for todo in todos:
                todo['tags'] = json.loads(todo['tags']) if todo.get('tags') else []
            return todos
    
    def get_by_id(self, todo_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取待办事项"""
        sql = "SELECT * FROM todos WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (todo_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['tags'] = json.loads(result['tags']) if result.get('tags') else []
                return result
            return None
    
    def update(self, todo_id: int, **kwargs) -> bool:
        """更新待办事项"""
        allowed_fields = {'title', 'description', 'priority', 'start_date', 'due_date', 'tags', 'completed', 'pinned', 'sort_order', 'status'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if 'tags' in filtered:
            filtered['tags'] = json.dumps(filtered['tags'])
        
        if not filtered:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE todos 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        values = list(filtered.values()) + [todo_id]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete(self, todo_id: int) -> bool:
        """删除待办事项"""
        sql = "DELETE FROM todos WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (todo_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_completed(self, todo_id: int) -> bool:
        """切换待办事项完成状态"""
        sql = """
            UPDATE todos 
            SET completed = NOT completed,
                status = CASE WHEN completed = 0 THEN '已完成' ELSE '未完成' END,
                updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (todo_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_pinned(self, todo_id: int) -> bool:
        """切换待办事项置顶状态"""
        sql = """
            UPDATE todos 
            SET pinned = NOT pinned, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (todo_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索待办事项"""
        sql = """
            SELECT id, title, description, priority, due_date, completed, pinned 
            FROM todos 
            WHERE title LIKE ? OR description LIKE ? OR tags LIKE ?
            ORDER BY pinned DESC, id DESC 
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit))
            return [dict(row) for row in cursor.fetchall()]
