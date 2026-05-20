from typing import Optional, List, Dict, Any

from .base import BaseRepository, TableConfig


PLUGIN_ID = 'text_tools_learning_card'


class LearningCardRepository(BaseRepository):
    """知识卡片仓储"""

    def __init__(self, db_manager):
        config = TableConfig(
            table_name='learning_cards',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['title', 'content', 'note'],
            allowed_fields=['plugin_id', 'category_id', 'title', 'content', 'note', 'sort_order'],
        )
        super().__init__(db_manager, config)

    def get_by_plugin(self, plugin_id: str, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if category_id is not None:
            sql = """
                SELECT c.*, cat.name as category_name
                FROM learning_cards c
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.plugin_id = ? AND c.category_id = ?
                ORDER BY c.sort_order, c.id
            """
            params = (plugin_id, category_id)
        else:
            sql = """
                SELECT c.*, cat.name as category_name
                FROM learning_cards c
                LEFT JOIN categories cat ON c.category_id = cat.id
                WHERE c.plugin_id = ?
                ORDER BY c.sort_order, c.id
            """
            params = (plugin_id,)

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def search(self, plugin_id: str, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        sql = """
            SELECT c.*, cat.name as category_name
            FROM learning_cards c
            LEFT JOIN categories cat ON c.category_id = cat.id
            WHERE c.plugin_id = ?
              AND (c.title LIKE ? OR c.content LIKE ? OR c.note LIKE ?)
            ORDER BY c.sort_order, c.id
            LIMIT ?
        """
        pattern = f'%{keyword}%'
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, pattern, pattern, pattern, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_card_count(self, plugin_id: str, category_id: Optional[int] = None) -> int:
        with self.db.get_connection() as conn:
            if category_id is not None:
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM learning_cards WHERE plugin_id = ? AND category_id = ?",
                    (plugin_id, category_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM learning_cards WHERE plugin_id = ?",
                    (plugin_id,),
                )
            return dict(cursor.fetchone())["cnt"]