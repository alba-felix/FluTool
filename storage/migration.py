"""数据库迁移管理。"""


MIGRATIONS = [
    ("clipboard_history", "plugin_id", "TEXT DEFAULT 'clipboard'"),
    ("clipboard_history", "content_type", "TEXT DEFAULT 'text'"),
    ("clipboard_history", "timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("clipboard_history", "item_type", "TEXT NOT NULL DEFAULT 'text'"),
    ("clipboard_history", "format", "TEXT DEFAULT ''"),
    ("todos", "sort_order", "INTEGER DEFAULT 0"),
    ("todos", "status", "TEXT DEFAULT '进行中'"),
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
