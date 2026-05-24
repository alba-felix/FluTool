"""数据库迁移管理。"""

from loguru import logger


MIGRATIONS = [
    ("clipboard_history", "plugin_id", "TEXT DEFAULT 'clipboard'"),
    ("clipboard_history", "content_type", "TEXT DEFAULT 'text'"),
    ("clipboard_history", "timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("clipboard_history", "item_type", "TEXT NOT NULL DEFAULT 'text'"),
    ("clipboard_history", "format", "TEXT DEFAULT ''"),
    ("todos", "sort_order", "INTEGER DEFAULT 0"),
    ("todos", "status", "TEXT DEFAULT '进行中'"),
    ("todos", "remind_before", "INTEGER DEFAULT 0"),
    ("todos", "last_reminded", "TEXT DEFAULT ''"),
    ("todos", "due_time", "TEXT DEFAULT '23:59'"),
    ("notebook", "color", "TEXT DEFAULT ''"),
    ("ai_conversations", "provider_id", "TEXT NOT NULL DEFAULT 'default'"),
    ("ai_conversations", "provider", "TEXT NOT NULL DEFAULT 'default'"),
    ("ai_conversations", "model_id", "TEXT NOT NULL DEFAULT 'default'"),
    ("ai_conversations", "system_prompt", "TEXT DEFAULT ''"),
    ("ai_conversations", "pinned", "INTEGER DEFAULT 0"),
    ("ai_conversations", "archived", "INTEGER DEFAULT 0"),
    ("ai_messages", "tool_name", "TEXT DEFAULT ''"),
    ("ai_messages", "tool_payload", "TEXT DEFAULT ''"),
    ("ai_messages", "status", "TEXT DEFAULT 'done'"),
    ("ai_messages", "token_input", "INTEGER DEFAULT 0"),
    ("ai_messages", "token_output", "INTEGER DEFAULT 0"),
    ("ai_messages", "latency_ms", "INTEGER DEFAULT 0"),
    ("app_launcher", "launch_count", "INTEGER DEFAULT 0"),
    ("app_launcher", "last_launch_time", "TIMESTAMP"),
    ("app_launcher", "is_favorite", "INTEGER DEFAULT 0"),
    ("categories", "icon_name", "TEXT DEFAULT ''"),
    ("categories", "color", "TEXT DEFAULT ''"),
]


class MigrationManager:
    """负责数据库结构迁移和历史数据修正。"""

    def migrate_ai_tables(self, conn) -> None:
        """迁移 AI 表，处理旧结构问题。"""
        cursor = conn.execute("PRAGMA table_info(ai_conversations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        if "provider_id" in columns:
            try:
                conn.execute("SELECT provider_id FROM ai_conversations WHERE provider_id IS NULL LIMIT 1")
            except Exception:
                pass
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM ai_conversations WHERE provider_id IS NULL")
                if cursor.fetchone()[0] > 0:
                    conn.execute("UPDATE ai_conversations SET provider_id = 'default' WHERE provider_id IS NULL")
                    conn.commit()

        if "provider" not in columns:
            conn.execute("ALTER TABLE ai_conversations ADD COLUMN provider TEXT NOT NULL DEFAULT 'default'")
            conn.commit()
        if "model_id" not in columns:
            conn.execute("ALTER TABLE ai_conversations ADD COLUMN model_id TEXT NOT NULL DEFAULT 'default'")
            conn.commit()
        if "system_prompt" not in columns:
            conn.execute("ALTER TABLE ai_conversations ADD COLUMN system_prompt TEXT DEFAULT ''")
            conn.commit()

        if "provider_id" in columns and "provider" in columns:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM ai_conversations "
                "WHERE provider = 'default' AND provider_id != 'default'"
            )
            if cursor.fetchone()[0] > 0:
                conn.execute("UPDATE ai_conversations SET provider = provider_id WHERE provider = 'default'")
                conn.commit()

    def run_migrations(self, conn) -> None:
        """运行数据库迁移，添加缺失的列。"""
        for table, column, definition in MIGRATIONS:
            try:
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                if column not in columns:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                    conn.commit()
            except Exception:
                pass

        try:
            cursor = conn.execute("PRAGMA table_info(todos)")
            columns = [row[1] for row in cursor.fetchall()]
            if "status" in columns:
                conn.execute("UPDATE todos SET status = '已完成' WHERE completed = 1 AND status = '进行中'")
                conn.commit()
        except Exception:
            pass

        self._migrate_vocabulary_tables(conn)
        self._migrate_learning_cards_table(conn)
        self._migrate_categories_table(conn)

    def _migrate_categories_table(self, conn) -> None:
        """分类表迁移：确保 categories 表存在 updated_at 列。"""
        try:
            cursor = conn.execute("PRAGMA table_info(categories)")
            columns = {row[1] for row in cursor.fetchall()}
            if "updated_at" not in columns:
                logger.info("categories 表缺少 updated_at 列，正在添加")
                conn.execute("ALTER TABLE categories ADD COLUMN updated_at TIMESTAMP")
                conn.commit()
                logger.info("categories 表 updated_at 列添加成功")
        except Exception as e:
            logger.error(f"categories 表迁移失败: {e}")
            raise

    def _migrate_learning_cards_table(self, conn) -> None:
        """知识卡片表迁移：确保 learning_cards 表存在且结构正确。"""
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='learning_cards'")
            if cursor.fetchone() is None:
                logger.info("learning_cards 表不存在，创建新表")
                conn.execute("""
                    CREATE TABLE learning_cards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin_id TEXT NOT NULL,
                        category_id INTEGER,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        note TEXT DEFAULT '',
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                    )
                """)
                conn.commit()
                logger.info("learning_cards 表创建成功")
                return

            cursor = conn.execute("PRAGMA table_info(learning_cards)")
            columns = {row[1] for row in cursor.fetchall()}
            logger.debug(f"learning_cards 表当前列: {columns}")
            
            if "updated_at" not in columns:
                logger.info("learning_cards 表缺少 updated_at 列，正在添加")
                conn.execute("ALTER TABLE learning_cards ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                conn.commit()
                logger.info("updated_at 列添加成功")
            else:
                logger.debug("learning_cards 表结构正确，无需迁移")
        except Exception as e:
            logger.error(f"learning_cards 表迁移失败: {e}")
            raise

    def _migrate_vocabulary_tables(self, conn) -> None:
        """词汇背诵表结构重构：vocabulary_words 增加 plugin_id 列、废弃独立的 word_categories 表。"""
        PLUGIN_ID = 'text_tools_vocabulary'
        
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vocabulary_words'")
            if cursor.fetchone() is None:
                logger.debug("vocabulary_words 表不存在，无需迁移")
                return

            cursor = conn.execute("PRAGMA table_info(vocabulary_words)")
            columns = {row[1] for row in cursor.fetchall()}

            if "plugin_id" in columns:
                logger.debug("vocabulary_words 表已包含 plugin_id 列，无需迁移")
                return

            logger.info("vocabulary_words 表缺少 plugin_id 列，开始数据迁移")

            cursor = conn.execute("SELECT COUNT(*) FROM vocabulary_words")
            old_count = cursor.fetchone()[0]
            logger.info(f"旧表中有 {old_count} 条词汇数据")

            conn.execute("ALTER TABLE vocabulary_words RENAME TO vocabulary_words_old")
            conn.commit()

            conn.execute("""
                CREATE TABLE vocabulary_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id TEXT NOT NULL,
                    category_id INTEGER,
                    chinese TEXT NOT NULL,
                    english TEXT NOT NULL,
                    pronunciation TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)
            conn.commit()

            if old_count > 0:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_categories'")
                has_old_categories = cursor.fetchone() is not None

                category_map = {}
                if has_old_categories:
                    cursor = conn.execute("SELECT id, name FROM word_categories")
                    for row in cursor.fetchall():
                        old_cat_id, cat_name = row[0], row[1]
                        new_cat_id = self._ensure_category(conn, PLUGIN_ID, cat_name)
                        category_map[old_cat_id] = new_cat_id
                    logger.info(f"迁移了 {len(category_map)} 个分类")

                cursor = conn.execute("""
                    SELECT id, category_id, chinese, english, pronunciation, sort_order, created_at
                    FROM vocabulary_words_old
                """)
                old_words = cursor.fetchall()

                migrated = 0
                for row in old_words:
                    old_id, old_cat_id, chinese, english, pronunciation, sort_order, created_at = row
                    new_cat_id = category_map.get(old_cat_id) if old_cat_id else None
                    
                    conn.execute("""
                        INSERT INTO vocabulary_words 
                        (plugin_id, category_id, chinese, english, pronunciation, sort_order, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (PLUGIN_ID, new_cat_id, chinese, english, pronunciation, sort_order or 0, created_at))
                    migrated += 1

                conn.commit()
                logger.info(f"成功迁移 {migrated} 条词汇数据")

            conn.execute("DROP TABLE vocabulary_words_old")
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_categories'")
            if cursor.fetchone() is not None:
                conn.execute("DROP TABLE word_categories")
            conn.commit()
            logger.info("词汇表迁移完成，旧表已清理")

        except Exception as e:
            logger.error(f"词汇表迁移失败: {e}")
            try:
                conn.execute("DROP TABLE IF EXISTS vocabulary_words")
                conn.execute("DROP TABLE IF EXISTS vocabulary_words_old")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS vocabulary_words (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin_id TEXT NOT NULL,
                        category_id INTEGER,
                        chinese TEXT NOT NULL,
                        english TEXT NOT NULL,
                        pronunciation TEXT DEFAULT '',
                        sort_order INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                    )
                """)
                conn.commit()
                logger.warning("迁移失败，已创建新表（数据丢失）")
            except Exception as e2:
                logger.error(f"回滚创建表也失败: {e2}")
            raise

    def _ensure_category(self, conn, plugin_id: str, name: str) -> int:
        """确保分类存在，返回分类 ID。"""
        cursor = conn.execute(
            "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
            (plugin_id, name)
        )
        row = cursor.fetchone()
        if row:
            return row[0]
        
        cursor = conn.execute(
            "INSERT INTO categories (plugin_id, name) VALUES (?, ?)",
            (plugin_id, name)
        )
        conn.commit()
        return cursor.lastrowid
