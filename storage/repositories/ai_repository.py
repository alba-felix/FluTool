from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class AIRepository:
    """AI 会话与消息仓储"""

    def __init__(self):
        self._db = DatabaseManager()

    def create_conversation(
        self,
        title: str,
        provider: str,
        model_id: str,
        system_prompt: str = "",
    ) -> int:
        with self._db.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(ai_conversations)")
            columns = [row[1] for row in cursor.fetchall()]

            if "provider_id" in columns:
                cursor = conn.execute(
                    """
                    INSERT INTO ai_conversations (title, provider_id, provider, model_id, system_prompt)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, provider, provider, model_id, system_prompt),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO ai_conversations (title, provider, model_id, system_prompt)
                    VALUES (?, ?, ?, ?)
                    """,
                    (title, provider, model_id, system_prompt),
                )
            conn.commit()
            return int(cursor.lastrowid)

    def list_conversations(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ai_conversations
                WHERE archived = 0
                ORDER BY pinned DESC, updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        tool_name: str = "",
        tool_payload: str = "",
        status: str = "done",
    ) -> int:
        with self._db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ai_messages
                (conversation_id, role, content, tool_name, tool_payload, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, tool_name, tool_payload, status),
            )
            conn.execute(
                """
                UPDATE ai_conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (conversation_id,),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def list_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        with self._db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ai_messages
                WHERE conversation_id = ?
                ORDER BY id
                """,
                (conversation_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        with self._db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM ai_conversations WHERE id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def delete_conversation(self, conversation_id: int) -> bool:
        with self._db.get_connection() as conn:
            conn.execute(
                "DELETE FROM ai_messages WHERE conversation_id = ?",
                (conversation_id,),
            )
            cursor = conn.execute(
                "DELETE FROM ai_conversations WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def search_conversations(self, keyword: str, limit: int = 100) -> List[Dict[str, Any]]:
        """搜索对话历史（标题和内容）"""
        with self._db.get_connection() as conn:
            search_pattern = f"%{keyword}%"
            cursor = conn.execute(
                """
                SELECT DISTINCT c.* FROM ai_conversations c
                LEFT JOIN ai_messages m ON c.id = m.conversation_id
                WHERE c.archived = 0
                AND (
                    c.title LIKE ?
                    OR m.content LIKE ?
                )
                ORDER BY c.pinned DESC, c.updated_at DESC
                LIMIT ?
                """,
                (search_pattern, search_pattern, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_messages(self, keyword: str, limit: int = 100) -> List[Dict[str, Any]]:
        """搜索消息内容"""
        with self._db.get_connection() as conn:
            search_pattern = f"%{keyword}%"
            cursor = conn.execute(
                """
                SELECT m.*, c.title as conversation_title
                FROM ai_messages m
                JOIN ai_conversations c ON m.conversation_id = c.id
                WHERE c.archived = 0
                AND m.content LIKE ?
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (search_pattern, limit),
            )
            return [dict(row) for row in cursor.fetchall()]
