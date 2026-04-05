import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import json


class DatabaseManager:
    """
    数据库管理器
    
    单例模式，管理 SQLite 数据库连接。
    支持多插件共享同一数据库文件。
    """
    
    _instance: Optional['DatabaseManager'] = None
    _db_path: Optional[Path] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self, db_path: str) -> None:
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径
        """
        if self._initialized:
            return
        self._initialized = True
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[DatabaseManager] Initializing database at: {self._db_path}")
        print(f"[DatabaseManager] Database exists: {self._db_path.exists()}")
        self._create_tables()
        print(f"[DatabaseManager] Tables created/verified")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self) -> None:
        """创建基础表结构"""
        with self.get_connection() as conn:
            conn.executescript('''
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
            ''')
            conn.commit()
            
            self._run_migrations(conn)
            self._migrate_ai_tables(conn)
            self._create_indexes(conn)

    def _migrate_ai_tables(self, conn) -> None:
        """迁移 AI 表，处理旧结构问题"""
        cursor = conn.execute("PRAGMA table_info(ai_conversations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        need_migrate = False
        if "provider_id" in columns and "provider" not in columns:
            need_migrate = True
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
            cursor = conn.execute("SELECT COUNT(*) FROM ai_conversations WHERE provider = 'default' AND provider_id != 'default'")
            if cursor.fetchone()[0] > 0:
                conn.execute("UPDATE ai_conversations SET provider = provider_id WHERE provider = 'default'")
                conn.commit()
    
    def _run_migrations(self, conn) -> None:
        """运行数据库迁移，添加缺失的列"""
        migrations = [
            ("clipboard_history", "timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("clipboard_history", "item_type", "TEXT NOT NULL DEFAULT 'text'"),
            ("clipboard_history", "format", "TEXT DEFAULT ''"),
            ("todos", "sort_order", "INTEGER DEFAULT 0"),
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
        ]
        
        for table, column, definition in migrations:
            try:
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                if column not in columns:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                    conn.commit()
            except Exception:
                pass
    
    def _create_indexes(self, conn) -> None:
        """创建索引"""
        indexes = [
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
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception:
                pass
        conn.commit()
    
    def add_category(self, plugin_id: str, name: str, sort_order: int = 0) -> int:
        """添加分类"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO categories (plugin_id, name, sort_order) VALUES (?, ?, ?)",
                (plugin_id, name, sort_order)
            )
            conn.commit()
            if cursor.rowcount == 0:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, name)
                )
                row = cursor.fetchone()
                return row['id'] if row else 0
            return cursor.lastrowid
    
    def get_categories(self, plugin_id: str) -> List[Dict[str, Any]]:
        """获取插件的所有分类"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM categories WHERE plugin_id = ? ORDER BY sort_order, id",
                (plugin_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_category(self, plugin_id: str, category_id: int, name: str) -> bool:
        """更新分类名称"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE categories SET name = ? WHERE plugin_id = ? AND id = ?",
                (name, plugin_id, category_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_todos(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索待办事项"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT id, title, description, priority, due_date, completed, pinned 
                   FROM todos 
                   WHERE title LIKE ? OR description LIKE ? OR tags LIKE ?
                   ORDER BY pinned DESC, id DESC LIMIT ?""",
                (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def search_folder_tree_rules(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索文件夹树规则"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, rule_name, exclude_items FROM folder_tree_rules WHERE rule_name LIKE ?",
                (f'%{keyword}%',)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_category(self, plugin_id: str, category_id: int) -> bool:
        """删除分类"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM categories WHERE plugin_id = ? AND id = ?",
                (plugin_id, category_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def add_bookmark(self, plugin_id: str, name: str, url: str, 
                     category_name: str = None, icon: str = None, 
                     notes: str = None, sort_order: int = 0) -> int:
        """添加书签"""
        with self.get_connection() as conn:
            category_id = None
            if category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO bookmarks (plugin_id, category_id, name, url, icon, notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, name, url, icon, notes, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def bookmark_exists(self, plugin_id: str, url: str) -> bool:
        """检查书签是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM bookmarks WHERE plugin_id = ? AND url = ?",
                (plugin_id, url)
            )
            return cursor.fetchone() is not None
    
    def get_bookmarks(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取书签列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT b.*, c.name as category_name 
                       FROM bookmarks b 
                       LEFT JOIN categories c ON b.category_id = c.id 
                       WHERE b.plugin_id = ? AND b.category_id = ?
                       ORDER BY b.sort_order, b.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT b.*, c.name as category_name 
                       FROM bookmarks b 
                       LEFT JOIN categories c ON b.category_id = c.id 
                       WHERE b.plugin_id = ?
                       ORDER BY b.sort_order, b.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_bookmark(self, plugin_id: str, bookmark_id: int, **kwargs) -> bool:
        """更新书签"""
        allowed_fields = {'name', 'url', 'icon', 'notes', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, bookmark_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE bookmarks SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_bookmark(self, plugin_id: str, bookmark_id: int) -> bool:
        """删除书签"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM bookmarks WHERE plugin_id = ? AND id = ?",
                (plugin_id, bookmark_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_bookmarks(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索书签"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT b.*, c.name as category_name 
                   FROM bookmarks b 
                   LEFT JOIN categories c ON b.category_id = c.id 
                   WHERE b.plugin_id = ? AND (b.name LIKE ? OR b.url LIKE ? OR b.notes LIKE ?)
                   ORDER BY b.sort_order, b.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def import_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入数据（跳过已存在的书签）"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for cat_order, category in enumerate(data.get('categories', [])):
            cat_name = category.get('name', '未命名分类')
            cat_id = self.add_category(plugin_id, cat_name, cat_order)
            for bm_order, website in enumerate(category.get('websites', [])):
                url = website.get('url', '')
                if self.bookmark_exists(plugin_id, url):
                    continue
                self.add_bookmark(
                    plugin_id=plugin_id,
                    name=website.get('name', ''),
                    url=url,
                    category_name=cat_name,
                    icon=website.get('icon', ''),
                    notes=website.get('notes', ''),
                    sort_order=bm_order
                )
                count += 1
        return count
    
    def add_command(self, plugin_id: str, name: str, content: str,
                    category_name: str = None, sub_title: str = '',
                    sort_order: int = 0) -> int:
        """添加命令"""
        with self.get_connection() as conn:
            category_id = None
            if category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO commands (plugin_id, category_id, name, sub_title, content, sort_order) VALUES (?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, name, sub_title, content, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def command_exists(self, plugin_id: str, name: str, category_name: str = None) -> bool:
        """检查命令是否已存在"""
        with self.get_connection() as conn:
            if category_name:
                cursor = conn.execute(
                    """SELECT 1 FROM commands c
                       JOIN categories cat ON c.category_id = cat.id
                       WHERE c.plugin_id = ? AND c.name = ? AND cat.name = ?""",
                    (plugin_id, name, category_name)
                )
            else:
                cursor = conn.execute(
                    "SELECT 1 FROM commands WHERE plugin_id = ? AND name = ?",
                    (plugin_id, name)
                )
            return cursor.fetchone() is not None
    
    def get_commands(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取命令列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT c.*, cat.name as category_name 
                       FROM commands c 
                       LEFT JOIN categories cat ON c.category_id = cat.id 
                       WHERE c.plugin_id = ? AND c.category_id = ?
                       ORDER BY c.sort_order, c.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT c.*, cat.name as category_name 
                       FROM commands c 
                       LEFT JOIN categories cat ON c.category_id = cat.id 
                       WHERE c.plugin_id = ?
                       ORDER BY c.sort_order, c.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_command(self, plugin_id: str, command_id: int, **kwargs) -> bool:
        """更新命令"""
        allowed_fields = {'name', 'sub_title', 'content', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, command_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE commands SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_command(self, plugin_id: str, command_id: int) -> bool:
        """删除命令"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM commands WHERE plugin_id = ? AND id = ?",
                (plugin_id, command_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_commands(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索命令"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT c.*, cat.name as category_name 
                   FROM commands c 
                   LEFT JOIN categories cat ON c.category_id = cat.id 
                   WHERE c.plugin_id = ? AND (c.name LIKE ? OR c.sub_title LIKE ? OR c.content LIKE ? OR cat.name LIKE ?)
                   ORDER BY c.sort_order, c.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def import_commands_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入命令数据"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for cat_name, commands in data.items():
            cat_id = self.add_category(plugin_id, cat_name)
            if isinstance(commands, dict):
                for cmd_order, (cmd_name, cmd_data) in enumerate(commands.items()):
                    if self.command_exists(plugin_id, cmd_name, cat_name):
                        continue
                    if isinstance(cmd_data, dict):
                        content = cmd_data.get('content', '')
                        sub_title = cmd_data.get('sub_title', '')
                    else:
                        content = str(cmd_data)
                        sub_title = ''
                    self.add_command(
                        plugin_id=plugin_id,
                        name=cmd_name,
                        content=content,
                        category_name=cat_name,
                        sub_title=sub_title,
                        sort_order=cmd_order
                    )
                    count += 1
        return count
    
    def add_password(self, plugin_id: str, username: str, password: str,
                     platform: str = '', category_name: str = None,
                     category_id: int = None,
                     email: str = '', notes: str = '', sort_order: int = 0) -> int:
        """添加密码"""
        with self.get_connection() as conn:
            if category_id is None and category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO passwords (plugin_id, category_id, platform, username, password, email, notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, platform, username, password, email, notes, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def password_exists(self, plugin_id: str, username: str, password: str) -> bool:
        """检查密码是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM passwords WHERE plugin_id = ? AND username = ? AND password = ?",
                (plugin_id, username, password)
            )
            return cursor.fetchone() is not None
    
    def get_passwords(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取密码列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT p.*, c.name as category_name 
                       FROM passwords p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.plugin_id = ? AND p.category_id = ?
                       ORDER BY p.sort_order, p.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT p.*, c.name as category_name 
                       FROM passwords p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.plugin_id = ?
                       ORDER BY p.sort_order, p.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_password(self, plugin_id: str, password_id: int, **kwargs) -> bool:
        """更新密码"""
        allowed_fields = {'platform', 'username', 'password', 'email', 'notes', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, password_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE passwords SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_password(self, plugin_id: str, password_id: int) -> bool:
        """删除密码"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM passwords WHERE plugin_id = ? AND id = ?",
                (plugin_id, password_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_passwords(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索密码"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT p.*, c.name as category_name 
                   FROM passwords p 
                   LEFT JOIN categories c ON p.category_id = c.id 
                   WHERE p.plugin_id = ? AND (p.platform LIKE ? OR p.username LIKE ? OR p.email LIKE ? OR p.notes LIKE ?)
                   ORDER BY p.sort_order, p.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def add_app(self, plugin_id: str, name: str, target_path: str,
                category_name: str = None, category_id: int = None,
                icon_path: str = '', arguments: str = '',
                notes: str = '', sort_order: int = 0) -> int:
        """添加应用"""
        with self.get_connection() as conn:
            if category_id is None and category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO app_launcher (plugin_id, category_id, name, icon_path, target_path, arguments, notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, name, icon_path, target_path, arguments, notes, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def app_exists(self, plugin_id: str, name: str, target_path: str) -> bool:
        """检查应用是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM app_launcher WHERE plugin_id = ? AND name = ? AND target_path = ?",
                (plugin_id, name, target_path)
            )
            return cursor.fetchone() is not None
    
    def get_apps(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取应用列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT a.*, c.name as category_name 
                       FROM app_launcher a 
                       LEFT JOIN categories c ON a.category_id = c.id 
                       WHERE a.plugin_id = ? AND a.category_id = ?
                       ORDER BY a.sort_order, a.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT a.*, c.name as category_name 
                       FROM app_launcher a 
                       LEFT JOIN categories c ON a.category_id = c.id 
                       WHERE a.plugin_id = ?
                       ORDER BY a.sort_order, a.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_app(self, plugin_id: str, app_id: int, **kwargs) -> bool:
        """更新应用"""
        allowed_fields = {'name', 'icon_path', 'target_path', 'arguments', 'notes', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, app_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE app_launcher SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_app(self, plugin_id: str, app_id: int) -> bool:
        """删除应用"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM app_launcher WHERE plugin_id = ? AND id = ?",
                (plugin_id, app_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_apps(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索应用"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT a.*, c.name as category_name 
                   FROM app_launcher a 
                   LEFT JOIN categories c ON a.category_id = c.id 
                   WHERE a.plugin_id = ? AND (a.name LIKE ? OR a.target_path LIKE ? OR a.notes LIKE ?)
                   ORDER BY a.sort_order, a.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def import_apps_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入应用数据"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for cat_order, category in enumerate(data.get('categories', [])):
            cat_name = category.get('name', '未命名分类')
            self.add_category(plugin_id, cat_name, cat_order)
            for app_order, app in enumerate(category.get('apps', [])):
                name = app.get('name', '')
                target_path = app.get('target_path', '')
                if self.app_exists(plugin_id, name, target_path):
                    continue
                self.add_app(
                    plugin_id=plugin_id,
                    name=name,
                    target_path=target_path,
                    category_name=cat_name,
                    icon_path=app.get('icon_path', ''),
                    arguments=app.get('arguments', ''),
                    notes=app.get('notes', ''),
                    sort_order=app_order
                )
                count += 1
        return count
    
    def add_color(self, plugin_id: str, name: str, color_hex: str, color_rgb: str,
                  category_name: str = None, category_id: int = None,
                  color_argb: str = '', notes: str = '', sort_order: int = 0) -> int:
        """添加颜色"""
        with self.get_connection() as conn:
            if category_id is None and category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO color_palette (plugin_id, category_id, name, color_hex, color_rgb, color_argb, notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, name, color_hex, color_rgb, color_argb, notes, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def color_exists(self, plugin_id: str, color_hex: str) -> bool:
        """检查颜色是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM color_palette WHERE plugin_id = ? AND color_hex = ?",
                (plugin_id, color_hex)
            )
            return cursor.fetchone() is not None
    
    def get_colors(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取颜色列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT c.*, cat.name as category_name 
                       FROM color_palette c 
                       LEFT JOIN categories cat ON c.category_id = cat.id 
                       WHERE c.plugin_id = ? AND c.category_id = ?
                       ORDER BY c.sort_order, c.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT c.*, cat.name as category_name 
                       FROM color_palette c 
                       LEFT JOIN categories cat ON c.category_id = cat.id 
                       WHERE c.plugin_id = ?
                       ORDER BY c.sort_order, c.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_color(self, plugin_id: str, color_id: int, **kwargs) -> bool:
        """更新颜色"""
        allowed_fields = {'name', 'color_hex', 'color_rgb', 'color_argb', 'notes', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, color_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE color_palette SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_color(self, plugin_id: str, color_id: int) -> bool:
        """删除颜色"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM color_palette WHERE plugin_id = ? AND id = ?",
                (plugin_id, color_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_colors(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索颜色"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT c.*, cat.name as category_name 
                   FROM color_palette c 
                   LEFT JOIN categories cat ON c.category_id = cat.id 
                   WHERE c.plugin_id = ? AND (c.name LIKE ? OR c.color_hex LIKE ? OR c.color_rgb LIKE ? OR c.notes LIKE ?)
                   ORDER BY c.sort_order, c.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def add_script(self, plugin_id: str, name: str, content: str,
                   script_type: str = 'bat', category_name: str = None,
                   category_id: int = None, description: str = '',
                   sort_order: int = 0) -> int:
        """添加脚本"""
        with self.get_connection() as conn:
            if category_id is None and category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO scripts (plugin_id, category_id, name, script_type, content, description, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, name, script_type, content, description, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def script_exists(self, plugin_id: str, name: str) -> bool:
        """检查脚本是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM scripts WHERE plugin_id = ? AND name = ?",
                (plugin_id, name)
            )
            return cursor.fetchone() is not None
    
    def get_scripts(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取脚本列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT s.*, c.name as category_name 
                       FROM scripts s 
                       LEFT JOIN categories c ON s.category_id = c.id 
                       WHERE s.plugin_id = ? AND s.category_id = ?
                       ORDER BY s.sort_order, s.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT s.*, c.name as category_name 
                       FROM scripts s 
                       LEFT JOIN categories c ON s.category_id = c.id 
                       WHERE s.plugin_id = ?
                       ORDER BY s.sort_order, s.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_script(self, plugin_id: str, script_id: int, **kwargs) -> bool:
        """更新脚本"""
        allowed_fields = {'name', 'script_type', 'content', 'description', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, script_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE scripts SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_script(self, plugin_id: str, script_id: int) -> bool:
        """删除脚本"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM scripts WHERE plugin_id = ? AND id = ?",
                (plugin_id, script_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_scripts(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索脚本"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT s.*, c.name as category_name 
                   FROM scripts s 
                   LEFT JOIN categories c ON s.category_id = c.id 
                   WHERE s.plugin_id = ? AND (s.name LIKE ? OR s.content LIKE ? OR s.description LIKE ? OR s.script_type LIKE ?)
                   ORDER BY s.sort_order, s.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def add_clipboard_item(self, item_type: str, content: str, format: str = '') -> int:
        """添加剪贴板历史项"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO clipboard_history (plugin_id, content_type, content, format, item_type) VALUES (?, ?, ?, ?, ?)",
                ("clipboard", item_type, content, format, item_type)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_clipboard_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取剪贴板历史"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, item_type as type, content, format, timestamp FROM clipboard_history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def clear_clipboard_history(self) -> bool:
        """清空剪贴板历史"""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM clipboard_history")
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_clipboard_item(self, item_id: int) -> bool:
        """删除剪贴板历史项"""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM clipboard_history WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search_clipboard(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索剪贴板历史"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, item_type as type, content, format, timestamp FROM clipboard_history WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f'%{keyword}%', limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def add_folder_tree_rule(self, rule_name: str, exclude_items: list) -> int:
        """添加文件夹树规则"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO folder_tree_rules (rule_name, exclude_items) VALUES (?, ?)",
                (rule_name, json.dumps(exclude_items))
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_folder_tree_rule(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """获取文件夹树规则"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM folder_tree_rules WHERE rule_name = ?",
                (rule_name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_folder_tree_rules(self) -> List[Dict[str, Any]]:
        """获取所有文件夹树规则"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM folder_tree_rules ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_folder_tree_rule(self, rule_name: str, exclude_items: list) -> bool:
        """更新文件夹树规则"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE folder_tree_rules SET exclude_items = ?, updated_at = CURRENT_TIMESTAMP WHERE rule_name = ?",
                (json.dumps(exclude_items), rule_name)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_folder_tree_rule(self, rule_name: str) -> bool:
        """删除文件夹树规则"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM folder_tree_rules WHERE rule_name = ?",
                (rule_name,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def folder_tree_rule_exists(self, rule_name: str) -> bool:
        """检查文件夹树规则是否存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM folder_tree_rules WHERE rule_name = ?",
                (rule_name,)
            )
            return cursor.fetchone() is not None
    
    def add_quick_copy_card(self, title: str, sort_order: int = 0) -> int:
        """添加快速复制卡片"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO quick_copy_cards (title, sort_order) VALUES (?, ?)",
                (title, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_quick_copy_cards(self) -> List[Dict[str, Any]]:
        """获取所有快速复制卡片"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM quick_copy_cards ORDER BY sort_order, id")
            return [dict(row) for row in cursor.fetchall()]
    
    def update_quick_copy_card(self, card_id: int, **kwargs) -> bool:
        """更新快速复制卡片"""
        allowed_fields = {'title', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [card_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE quick_copy_cards SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_quick_copy_card(self, card_id: int) -> bool:
        """删除快速复制卡片"""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM quick_copy_cards WHERE id = ?", (card_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def add_quick_copy_item(self, card_id: int, content: str, sort_order: int = 0) -> int:
        """添加快速复制项"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO quick_copy_items (card_id, content, sort_order) VALUES (?, ?, ?)",
                (card_id, content, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_quick_copy_items(self, card_id: int) -> List[Dict[str, Any]]:
        """获取快速复制项"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM quick_copy_items WHERE card_id = ? ORDER BY sort_order, id",
                (card_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_quick_copy_item(self, item_id: int, **kwargs) -> bool:
        """更新快速复制项"""
        allowed_fields = {'content', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [item_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE quick_copy_items SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_quick_copy_item(self, item_id: int) -> bool:
        """删除快速复制项"""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM quick_copy_items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search_quick_copy(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索快速复制内容"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT i.id, i.card_id, i.content, c.title as card_title 
                   FROM quick_copy_items i 
                   JOIN quick_copy_cards c ON i.card_id = c.id 
                   WHERE i.content LIKE ? OR c.title LIKE ?
                   ORDER BY i.id DESC LIMIT ?""",
                (f'%{keyword}%', f'%{keyword}%', limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def add_todo(self, title: str, description: str = '', priority: str = '中',
                 start_date: str = '', due_date: str = '', tags: list = None,
                 completed: int = 0, pinned: int = 0) -> int:
        """添加待办事项"""
        with self.get_connection() as conn:
            tags_json = json.dumps(tags) if tags else '[]'
            cursor = conn.execute(
                "INSERT INTO todos (title, description, priority, start_date, due_date, tags, completed, pinned) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, description, priority, start_date, due_date, tags_json, completed, pinned)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_todos(self, completed: int = None) -> List[Dict[str, Any]]:
        """获取待办事项列表"""
        with self.get_connection() as conn:
            if completed is not None:
                cursor = conn.execute(
                    "SELECT * FROM todos WHERE completed = ? ORDER BY pinned DESC, sort_order, id",
                    (completed,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM todos ORDER BY pinned DESC, sort_order, id"
                )
            todos = [dict(row) for row in cursor.fetchall()]
            for todo in todos:
                todo['tags'] = json.loads(todo['tags']) if todo['tags'] else []
            return todos
    
    def update_todo(self, todo_id: int, **kwargs) -> bool:
        """更新待办事项"""
        allowed_fields = {'title', 'description', 'priority', 'start_date', 'due_date', 'tags', 'completed', 'pinned', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if 'tags' in updates:
            updates['tags'] = json.dumps(updates['tags'])
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [todo_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE todos SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_todo(self, todo_id: int) -> bool:
        """删除待办事项"""
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_todo_completed(self, todo_id: int) -> bool:
        """切换待办事项完成状态"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE todos SET completed = NOT completed, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (todo_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_todo_pinned(self, todo_id: int) -> bool:
        """切换待办事项置顶状态"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE todos SET pinned = NOT pinned, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (todo_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
