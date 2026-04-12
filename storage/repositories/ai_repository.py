from typing import List, Dict, Any, Optional
from .base import BaseRepository, TableConfig


class AIRepository:
    """AI 对话仓储"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    # ============ 对话操作 ============
    
    def add_conversation(self, title: str, provider: str, model_id: str,
                        system_prompt: str = '', pinned: int = 0, archived: int = 0) -> int:
        """添加 AI 对话"""
        sql = """
            INSERT INTO ai_conversations (title, provider, model_id, system_prompt, pinned, archived) 
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (
                title, provider, model_id, system_prompt, pinned, archived
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_conversations(self, archived: int = 0) -> List[Dict[str, Any]]:
        """获取 AI 对话列表"""
        sql = """
            SELECT * FROM ai_conversations 
            WHERE archived = ?
            ORDER BY pinned DESC, updated_at DESC
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (archived,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_conversation_by_id(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取对话"""
        sql = "SELECT * FROM ai_conversations WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (conversation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_conversation(self, conversation_id: int, **kwargs) -> bool:
        """更新 AI 对话"""
        allowed_fields = {'title', 'provider', 'model_id', 'system_prompt', 'pinned', 'archived'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not filtered:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE ai_conversations 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        values = list(filtered.values()) + [conversation_id]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """删除 AI 对话（级联删除消息）"""
        sql = "DELETE FROM ai_conversations WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (conversation_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ============ 消息操作 ============
    
    def add_message(self, conversation_id: int, role: str, content: str,
                   tool_name: str = '', tool_payload: str = '',
                   status: str = 'done', token_input: int = 0,
                   token_output: int = 0, latency_ms: int = 0) -> int:
        """添加 AI 消息"""
        sql = """
            INSERT INTO ai_messages 
            (conversation_id, role, content, tool_name, tool_payload, status, token_input, token_output, latency_ms) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (
                conversation_id, role, content, tool_name, tool_payload,
                status, token_input, token_output, latency_ms
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        """获取对话的所有消息"""
        sql = """
            SELECT * FROM ai_messages 
            WHERE conversation_id = ?
            ORDER BY created_at
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (conversation_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取消息"""
        sql = "SELECT * FROM ai_messages WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (message_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_message(self, message_id: int, **kwargs) -> bool:
        """更新 AI 消息"""
        allowed_fields = {'role', 'content', 'tool_name', 'tool_payload', 'status', 
                         'token_input', 'token_output', 'latency_ms'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not filtered:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE ai_messages 
            SET {set_clause} 
            WHERE id = ?
        """
        values = list(filtered.values()) + [message_id]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_message(self, message_id: int) -> bool:
        """删除 AI 消息"""
        sql = "DELETE FROM ai_messages WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (message_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_last_message(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """获取对话的最后一条消息"""
        sql = """
            SELECT * FROM ai_messages 
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (conversation_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_message_count(self, conversation_id: int) -> int:
        """获取对话的消息数量"""
        sql = "SELECT COUNT(*) FROM ai_messages WHERE conversation_id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (conversation_id,))
            row = cursor.fetchone()
            return row[0] if row else 0
