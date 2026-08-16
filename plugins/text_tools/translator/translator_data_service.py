"""翻译管理器数据服务。"""

from typing import Dict, List, Optional

from storage import DatabaseManager


class TranslatorDataService:
    """封装翻译历史和单词本数据访问。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def initialize_tables(self) -> None:
        """初始化翻译相关表。"""
        with self.db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_text TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    source_lang TEXT DEFAULT 'auto',
                    target_lang TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    source_lang TEXT DEFAULT 'en',
                    target_lang TEXT DEFAULT 'zh',
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_history(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> int:
        """添加翻译历史。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO translation_history
                (source_text, target_text, source_lang, target_lang)
                VALUES (?, ?, ?, ?)
                """,
                (source_text, target_text, source_lang, target_lang),
            )
            conn.commit()
            return cursor.lastrowid

    def list_history(self, lang_filter: str = "全部语言", date_filter: str = "全部时间",
                     limit: int = 100) -> List[Dict]:
        """获取翻译历史。"""
        query = """
            SELECT id, source_text, target_text, source_lang, target_lang, created_at
            FROM translation_history
            WHERE 1=1
        """
        params = []

        if lang_filter == "中文→英语":
            query += " AND source_lang = '中文' AND target_lang = '英语'"
        elif lang_filter == "英语→中文":
            query += " AND source_lang = '英语' AND target_lang = '中文'"
        elif lang_filter == "自动→中文":
            query += " AND source_lang = '自动检测' AND target_lang = '中文'"
        elif lang_filter == "其他":
            query += " AND source_lang NOT IN ('中文', '英语', '自动检测')"

        if date_filter == "今天":
            query += " AND date(created_at) = date('now')"
        elif date_filter == "最近7天":
            query += " AND created_at >= datetime('now', '-7 days')"
        elif date_filter == "最近30天":
            query += " AND created_at >= datetime('now', '-30 days')"

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def delete_history(self, record_id: int) -> bool:
        """删除单条翻译历史。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM translation_history WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_histories(self, record_ids: List[int]) -> int:
        """批量删除翻译历史。"""
        if not record_ids:
            return 0
        deleted_count = 0
        with self.db.get_connection() as conn:
            for record_id in record_ids:
                cursor = conn.execute("DELETE FROM translation_history WHERE id = ?", (record_id,))
                deleted_count += cursor.rowcount
            conn.commit()
        return deleted_count

    def clear_history(self) -> None:
        """清空翻译历史。"""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM translation_history")
            conn.commit()

    def list_vocabulary(self, limit: int = 100) -> List[Dict]:
        """获取单词本。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, word, translation, notes FROM vocabulary ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_vocabulary(self, record_id: int) -> Optional[Dict]:
        """获取单个单词。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, word, translation, notes FROM vocabulary WHERE id = ?",
                (record_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def vocabulary_exists(self, word: str) -> bool:
        """检查单词是否存在。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("SELECT id FROM vocabulary WHERE word = ?", (word,))
            return cursor.fetchone() is not None

    def add_vocabulary(self, word: str, translation: str, notes: str = "",
                       source_lang: str = "en", target_lang: str = "zh") -> int:
        """添加单词。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO vocabulary (word, translation, notes, source_lang, target_lang)
                VALUES (?, ?, ?, ?, ?)
                """,
                (word, translation, notes, source_lang, target_lang),
            )
            conn.commit()
            return cursor.lastrowid

    def update_vocabulary(self, record_id: int, word: str, translation: str, notes: str = "") -> bool:
        """更新单词。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE vocabulary SET word = ?, translation = ?, notes = ? WHERE id = ?",
                (word, translation, notes, record_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_vocabulary(self, record_id: int) -> bool:
        """删除单词。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM vocabulary WHERE id = ?", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
