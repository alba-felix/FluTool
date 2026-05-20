"""数据库表结构和索引管理。"""

from storage.migration import MigrationManager


CREATE_TABLES_SQL = '''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(plugin_id, name)
    );
    
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        icon TEXT,
        notes TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        name TEXT NOT NULL,
        sub_title TEXT DEFAULT '',
        content TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS passwords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        platform TEXT DEFAULT '',
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        email TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS app_launcher (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        name TEXT NOT NULL,
        icon_path TEXT DEFAULT '',
        target_path TEXT NOT NULL,
        arguments TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS notebook (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        note_type TEXT DEFAULT 'markdown',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS color_palette (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        name TEXT NOT NULL,
        color_hex TEXT NOT NULL,
        color_rgb TEXT NOT NULL,
        color_argb TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS scripts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT NOT NULL,
        category_id INTEGER,
        name TEXT NOT NULL,
        script_type TEXT DEFAULT 'bat',
        content TEXT NOT NULL,
        description TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    
    CREATE TABLE IF NOT EXISTS clipboard_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plugin_id TEXT DEFAULT 'clipboard',
        content_type TEXT DEFAULT 'text',
        item_type TEXT NOT NULL DEFAULT 'text',
        content TEXT NOT NULL,
        format TEXT DEFAULT '',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS folder_tree_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name TEXT NOT NULL UNIQUE,
        exclude_items TEXT NOT NULL DEFAULT '[]',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS quick_copy_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS quick_copy_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES quick_copy_cards(id) ON DELETE CASCADE
    );
    
    CREATE TABLE IF NOT EXISTS todos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        priority TEXT DEFAULT '中',
        start_date TEXT DEFAULT '',
        due_date TEXT DEFAULT '',
        tags TEXT DEFAULT '[]',
        completed INTEGER DEFAULT 0,
        pinned INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS ai_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        provider TEXT NOT NULL,
        model_id TEXT NOT NULL,
        system_prompt TEXT DEFAULT '',
        pinned INTEGER DEFAULT 0,
        archived INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS ai_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        tool_name TEXT DEFAULT '',
        tool_payload TEXT DEFAULT '',
        status TEXT DEFAULT 'done',
        token_input INTEGER DEFAULT 0,
        token_output INTEGER DEFAULT 0,
        latency_ms INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
    );

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
    );

    CREATE TABLE IF NOT EXISTS learning_cards (
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
    );
'''

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_bookmarks_plugin_id ON bookmarks(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_bookmarks_category_id ON bookmarks(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_categories_plugin_id ON categories(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_commands_plugin_id ON commands(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_commands_category_id ON commands(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_passwords_plugin_id ON passwords(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_passwords_category_id ON passwords(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_app_launcher_plugin_id ON app_launcher(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_app_launcher_category_id ON app_launcher(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_notebook_plugin_id ON notebook(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_notebook_category_id ON notebook(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_color_palette_plugin_id ON color_palette(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_color_palette_category_id ON color_palette(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_scripts_plugin_id ON scripts(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_scripts_category_id ON scripts(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_clipboard_timestamp ON clipboard_history(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_quick_copy_card_id ON quick_copy_items(card_id)",
    "CREATE INDEX IF NOT EXISTS idx_todos_completed ON todos(completed)",
    "CREATE INDEX IF NOT EXISTS idx_todos_pinned ON todos(pinned)",
    "CREATE INDEX IF NOT EXISTS idx_ai_conversations_updated_at ON ai_conversations(updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation_id ON ai_messages(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_ai_messages_created_at ON ai_messages(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_vocabulary_words_plugin_id ON vocabulary_words(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_vocabulary_words_category_id ON vocabulary_words(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_learning_cards_plugin_id ON learning_cards(plugin_id)",
    "CREATE INDEX IF NOT EXISTS idx_learning_cards_category_id ON learning_cards(category_id)",
]


class SchemaManager:
    """管理数据库表结构和索引。"""

    def create_tables(self, conn) -> None:
        """创建基础表结构并执行迁移。"""
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        MigrationManager().run_migrations(conn)
        MigrationManager().migrate_ai_tables(conn)
        self.create_indexes(conn)

    def create_indexes(self, conn) -> None:
        """创建索引。"""
        for index_sql in INDEXES:
            try:
                conn.execute(index_sql)
            except Exception:
                pass
        conn.commit()
