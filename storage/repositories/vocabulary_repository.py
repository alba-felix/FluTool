from typing import Optional, List, Dict, Any

from .base import BaseRepository, TableConfig


PLUGIN_ID = 'text_tools_vocabulary'


class VocabularyRepository(BaseRepository):
    """单词背诵仓储"""

    def __init__(self, db_manager):
        config = TableConfig(
            table_name='vocabulary_words',
            primary_key='id',
            plugin_field='plugin_id',
            has_category=True,
            category_field='category_id',
            searchable_fields=['chinese', 'english', 'pronunciation'],
            allowed_fields=['plugin_id', 'category_id', 'chinese', 'english', 'pronunciation', 'sort_order'],
        )
        super().__init__(db_manager, config)

    def exists(self, chinese: str, english: str) -> bool:
        sql = "SELECT 1 FROM vocabulary_words WHERE plugin_id = ? AND chinese = ? AND english = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (PLUGIN_ID, chinese, english))
            return cursor.fetchone() is not None

    def get_by_plugin(self, plugin_id: str, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if category_id is not None:
            sql = """
                SELECT w.*, c.name as category_name
                FROM vocabulary_words w
                LEFT JOIN categories c ON w.category_id = c.id
                WHERE w.plugin_id = ? AND w.category_id = ?
                ORDER BY w.sort_order, w.id
            """
            params = (plugin_id, category_id)
        else:
            sql = """
                SELECT w.*, c.name as category_name
                FROM vocabulary_words w
                LEFT JOIN categories c ON w.category_id = c.id
                WHERE w.plugin_id = ?
                ORDER BY w.sort_order, w.id
            """
            params = (plugin_id,)

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def search(self, plugin_id: str, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        sql = """
            SELECT w.*, c.name as category_name
            FROM vocabulary_words w
            LEFT JOIN categories c ON w.category_id = c.id
            WHERE w.plugin_id = ?
              AND (w.chinese LIKE ? OR w.english LIKE ? OR w.pronunciation LIKE ?)
            ORDER BY w.sort_order, w.id
            LIMIT ?
        """
        pattern = f'%{keyword}%'
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (plugin_id, pattern, pattern, pattern, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_word_count(self, plugin_id: str, category_id: Optional[int] = None) -> int:
        with self.db.get_connection() as conn:
            if category_id is not None:
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM vocabulary_words WHERE plugin_id = ? AND category_id = ?",
                    (plugin_id, category_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*) as cnt FROM vocabulary_words WHERE plugin_id = ?",
                    (plugin_id,),
                )
            return dict(cursor.fetchone())["cnt"]