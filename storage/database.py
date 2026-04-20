import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import json

from storage.repositories.bookmark_repository import BookmarkRepository
from storage.repositories.command_repository import CommandRepository
from storage.repositories.password_repository import PasswordRepository
from storage.repositories.app_repository import AppRepository
from storage.repositories.color_repository import ColorRepository
from storage.repositories.script_repository import ScriptRepository
from storage.repositories.clipboard_repository import ClipboardRepository
from storage.repositories.folder_tree_repository import FolderTreeRepository
from storage.repositories.quick_copy_repository import QuickCopyRepository
from storage.repositories.todo_repository import TodoRepository
from storage.repositories.ai_repository import AIRepository
from storage.repositories.category_repository import CategoryRepository


class DatabaseManager:
    """
    数据库管理器
    
    单例模式，管理 SQLite 数据库连接。
    作为 Repository 工厂，提供各种数据表的访问接口。
    """
    
    _instance: Optional['DatabaseManager'] = None
    _db_path: Optional[Path] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self, db_path: str) -> None:
        """初始化数据库"""
        if self._initialized:
            return
        self._initialized = True
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[DatabaseManager] Initializing database at: {self._db_path}")
        print(f"[DatabaseManager] Database exists: {self._db_path.exists()}")
        self._create_tables()
        print(f"[DatabaseManager] Tables created/verified")
        
        # 初始化所有 Repository
        self._init_repositories()
    
    def _init_repositories(self):
        """初始化所有 Repository 实例"""
        self.categories = CategoryRepository(self)
        self.bookmarks = BookmarkRepository(self)
        self.commands = CommandRepository(self)
        self.passwords = PasswordRepository(self)
        self.apps = AppRepository(self)
        self.colors = ColorRepository(self)
        self.scripts = ScriptRepository(self)
        self.clipboard = ClipboardRepository(self)
        self.folder_tree = FolderTreeRepository(self)
        self.quick_copy = QuickCopyRepository(self)
        self.todos = TodoRepository(self)
        self.ai = AIRepository(self)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        if self._db_path is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
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
    
    # ============ 向后兼容的接口 ============
    # 为了不破坏现有代码，保留原有的方法签名，但委托给对应的 Repository
    
    # Category 方法
    def add_category(self, plugin_id: str, name: str, sort_order: int = 0) -> int:
        return self.categories.add_or_get(plugin_id, name, sort_order)
    
    def get_categories(self, plugin_id: str) -> list:
        return self.categories.get_by_plugin(plugin_id)
    
    def update_category(self, plugin_id: str, category_id: int, name: str) -> bool:
        return self.categories.update(category_id, name=name)
    
    def delete_category(self, plugin_id: str, category_id: int) -> bool:
        return self.categories.delete(category_id)
    
    # Bookmark 方法
    def add_bookmark(self, plugin_id: str, name: str, url: str, 
                     category_name: str = None, icon: str = None, 
                     notes: str = None, sort_order: int = 0) -> int:
        category_id = self._resolve_category_id(plugin_id, category_name)
        return self.bookmarks.add(
            plugin_id=plugin_id, category_id=category_id, 
            name=name, url=url, icon=icon, notes=notes, sort_order=sort_order
        )
    
    def get_bookmarks(self, plugin_id: str, category_id: int = None) -> list:
        return self.bookmarks.get_by_plugin(plugin_id, category_id)
    
    def update_bookmark(self, plugin_id: str, bookmark_id: int, **kwargs) -> bool:
        return self.bookmarks.update(bookmark_id, **kwargs)
    
    def delete_bookmark(self, plugin_id: str, bookmark_id: int) -> bool:
        return self.bookmarks.delete(bookmark_id)
    
    def search_bookmarks(self, plugin_id: str, keyword: str) -> list:
        return self.bookmarks.search(plugin_id, keyword)
    
    def bookmark_exists(self, plugin_id: str, url: str) -> bool:
        return self.bookmarks.exists(plugin_id, url)
    
    # Command 方法
    def add_command(self, plugin_id: str, name: str, content: str,
                    category_name: str = None, sub_title: str = '',
                    sort_order: int = 0) -> int:
        category_id = self._resolve_category_id(plugin_id, category_name)
        return self.commands.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, sub_title=sub_title, content=content, sort_order=sort_order
        )
    
    def get_commands(self, plugin_id: str, category_id: int = None) -> list:
        return self.commands.get_by_plugin(plugin_id, category_id)
    
    def update_command(self, plugin_id: str, command_id: int, **kwargs) -> bool:
        return self.commands.update(command_id, **kwargs)
    
    def delete_command(self, plugin_id: str, command_id: int) -> bool:
        return self.commands.delete(command_id)
    
    def search_commands(self, plugin_id: str, keyword: str) -> list:
        return self.commands.search(plugin_id, keyword)
    
    def command_exists(self, plugin_id: str, name: str, category_name: str = None) -> bool:
        return self.commands.exists(plugin_id, name, category_name)
    
    # Password 方法
    def add_password(self, plugin_id: str, username: str, password: str,
                     platform: str = '', category_name: str = None,
                     category_id: int = None,
                     email: str = '', notes: str = '', sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.passwords.add(
            plugin_id=plugin_id, category_id=category_id,
            platform=platform, username=username, password=password,
            email=email, notes=notes, sort_order=sort_order
        )
    
    def get_passwords(self, plugin_id: str, category_id: int = None) -> list:
        return self.passwords.get_by_plugin(plugin_id, category_id)
    
    def update_password(self, plugin_id: str, password_id: int, **kwargs) -> bool:
        return self.passwords.update(password_id, **kwargs)
    
    def delete_password(self, plugin_id: str, password_id: int) -> bool:
        return self.passwords.delete(password_id)
    
    def search_passwords(self, plugin_id: str, keyword: str) -> list:
        return self.passwords.search(plugin_id, keyword)
    
    def password_exists(self, plugin_id: str, username: str, password: str) -> bool:
        return self.passwords.exists(plugin_id, username, password)
    
    # App 方法
    def add_app(self, plugin_id: str, name: str, target_path: str,
                category_name: str = None, category_id: int = None,
                icon_path: str = '', arguments: str = '',
                notes: str = '', sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.apps.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, icon_path=icon_path, target_path=target_path,
            arguments=arguments, notes=notes, sort_order=sort_order
        )
    
    def get_apps(self, plugin_id: str, category_id: int = None) -> list:
        return self.apps.get_by_plugin(plugin_id, category_id)
    
    def update_app(self, plugin_id: str, app_id: int, **kwargs) -> bool:
        return self.apps.update(app_id, **kwargs)
    
    def delete_app(self, plugin_id: str, app_id: int) -> bool:
        return self.apps.delete(app_id)
    
    def search_apps(self, plugin_id: str, keyword: str) -> list:
        return self.apps.search(plugin_id, keyword)
    
    def app_exists(self, plugin_id: str, name: str, target_path: str) -> bool:
        return self.apps.exists(plugin_id, name, target_path)
    
    # Color 方法
    def add_color(self, plugin_id: str, name: str, color_hex: str, color_rgb: str,
                  category_name: str = None, category_id: int = None,
                  color_argb: str = '', notes: str = '', sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.colors.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, color_hex=color_hex, color_rgb=color_rgb,
            color_argb=color_argb, notes=notes, sort_order=sort_order
        )
    
    def get_colors(self, plugin_id: str, category_id: int = None) -> list:
        return self.colors.get_by_plugin(plugin_id, category_id)
    
    def update_color(self, plugin_id: str, color_id: int, **kwargs) -> bool:
        return self.colors.update(color_id, **kwargs)
    
    def delete_color(self, plugin_id: str, color_id: int) -> bool:
        return self.colors.delete(color_id)
    
    def search_colors(self, plugin_id: str, keyword: str) -> list:
        return self.colors.search(plugin_id, keyword)
    
    def color_exists(self, plugin_id: str, color_hex: str) -> bool:
        return self.colors.exists(plugin_id, color_hex)
    
    # Script 方法
    def add_script(self, plugin_id: str, name: str, content: str,
                   script_type: str = 'bat', category_name: str = None,
                   category_id: int = None, description: str = '',
                   sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.scripts.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, script_type=script_type, content=content,
            description=description, sort_order=sort_order
        )
    
    def get_scripts(self, plugin_id: str, category_id: int = None) -> list:
        return self.scripts.get_by_plugin(plugin_id, category_id)
    
    def update_script(self, plugin_id: str, script_id: int, **kwargs) -> bool:
        return self.scripts.update(script_id, **kwargs)
    
    def delete_script(self, plugin_id: str, script_id: int) -> bool:
        return self.scripts.delete(script_id)
    
    def search_scripts(self, plugin_id: str, keyword: str) -> list:
        return self.scripts.search(plugin_id, keyword)
    
    def script_exists(self, plugin_id: str, name: str) -> bool:
        return self.scripts.exists(plugin_id, name)
    
    # Clipboard 方法
    def add_clipboard_item(self, item_type: str, content: str, format: str = '') -> int:
        return self.clipboard.add(item_type=item_type, content=content, format=format)
    
    def get_clipboard_history(self, limit: int = 100) -> list:
        return self.clipboard.get_history(limit)
    
    def clear_clipboard_history(self) -> bool:
        return self.clipboard.clear()
    
    def delete_clipboard_item(self, item_id: int) -> bool:
        return self.clipboard.delete(item_id)
    
    def search_clipboard(self, keyword: str, limit: int = 20) -> list:
        return self.clipboard.search(keyword, limit)
    
    # Folder Tree 方法
    def add_folder_tree_rule(self, rule_name: str, exclude_items: list) -> int:
        return self.folder_tree.add(rule_name=rule_name, exclude_items=exclude_items)
    
    def get_folder_tree_rule(self, rule_name: str) -> Optional[Dict[str, Any]]:
        return self.folder_tree.get_by_name(rule_name)
    
    def get_all_folder_tree_rules(self) -> list:
        return self.folder_tree.get_all()
    
    def update_folder_tree_rule(self, rule_name: str, exclude_items: list) -> bool:
        return self.folder_tree.update_by_name(rule_name, exclude_items=exclude_items)
    
    def delete_folder_tree_rule(self, rule_name: str) -> bool:
        return self.folder_tree.delete_by_name(rule_name)
    
    def folder_tree_rule_exists(self, rule_name: str) -> bool:
        return self.folder_tree.exists(rule_name)
    
    def search_folder_tree_rules(self, keyword: str) -> list:
        return self.folder_tree.search(keyword)
    
    # Quick Copy 方法
    def add_quick_copy_card(self, title: str, sort_order: int = 0) -> int:
        return self.quick_copy.add_card(title=title, sort_order=sort_order)
    
    def get_quick_copy_cards(self) -> list:
        return self.quick_copy.get_cards()
    
    def update_quick_copy_card(self, card_id: int, **kwargs) -> bool:
        return self.quick_copy.update_card(card_id, **kwargs)
    
    def delete_quick_copy_card(self, card_id: int) -> bool:
        return self.quick_copy.delete_card(card_id)
    
    def add_quick_copy_item(self, card_id: int, content: str, sort_order: int = 0) -> int:
        return self.quick_copy.add_item(card_id=card_id, content=content, sort_order=sort_order)
    
    def get_quick_copy_items(self, card_id: int) -> list:
        return self.quick_copy.get_items(card_id)
    
    def update_quick_copy_item(self, item_id: int, **kwargs) -> bool:
        return self.quick_copy.update_item(item_id, **kwargs)
    
    def delete_quick_copy_item(self, item_id: int) -> bool:
        return self.quick_copy.delete_item(item_id)
    
    def search_quick_copy(self, keyword: str, limit: int = 20) -> list:
        return self.quick_copy.search(keyword, limit)
    
    # Todo 方法
    def add_todo(self, title: str, description: str = '', priority: str = '中',
                 start_date: str = '', due_date: str = '', tags: list = None,
                 completed: int = 0, pinned: int = 0) -> int:
        return self.todos.add(
            title=title, description=description, priority=priority,
            start_date=start_date, due_date=due_date, tags=tags,
            completed=completed, pinned=pinned
        )
    
    def get_todos(self, completed: int = None) -> list:
        return self.todos.get_all(completed)
    
    def update_todo(self, todo_id: int, **kwargs) -> bool:
        return self.todos.update(todo_id, **kwargs)
    
    def delete_todo(self, todo_id: int) -> bool:
        return self.todos.delete(todo_id)
    
    def toggle_todo_completed(self, todo_id: int) -> bool:
        return self.todos.toggle_completed(todo_id)
    
    def toggle_todo_pinned(self, todo_id: int) -> bool:
        return self.todos.toggle_pinned(todo_id)
    
    def search_todos(self, keyword: str, limit: int = 20) -> list:
        return self.todos.search(keyword, limit)
    
    # AI 方法
    def add_ai_conversation(self, title: str, provider: str, model_id: str,
                           system_prompt: str = '', pinned: int = 0, archived: int = 0) -> int:
        return self.ai.add_conversation(
            title=title, provider=provider, model_id=model_id,
            system_prompt=system_prompt, pinned=pinned, archived=archived
        )
    
    def get_ai_conversations(self, archived: int = 0) -> list:
        return self.ai.get_conversations(archived)
    
    def update_ai_conversation(self, conversation_id: int, **kwargs) -> bool:
        return self.ai.update_conversation(conversation_id, **kwargs)
    
    def delete_ai_conversation(self, conversation_id: int) -> bool:
        return self.ai.delete_conversation(conversation_id)
    
    def add_ai_message(self, conversation_id: int, role: str, content: str,
                      tool_name: str = '', tool_payload: str = '',
                      status: str = 'done', token_input: int = 0,
                      token_output: int = 0, latency_ms: int = 0) -> int:
        return self.ai.add_message(
            conversation_id=conversation_id, role=role, content=content,
            tool_name=tool_name, tool_payload=tool_payload, status=status,
            token_input=token_input, token_output=token_output, latency_ms=latency_ms
        )
    
    def get_ai_messages(self, conversation_id: int) -> list:
        return self.ai.get_messages(conversation_id)
    
    def update_ai_message(self, message_id: int, **kwargs) -> bool:
        return self.ai.update_message(message_id, **kwargs)
    
    def delete_ai_message(self, message_id: int) -> bool:
        return self.ai.delete_message(message_id)
    
    # 辅助方法
    def _resolve_category_id(self, plugin_id: str, category_name: str = None) -> Optional[int]:
        """解析分类 ID"""
        if not category_name:
            return None
        categories = self.categories.get_by_plugin(plugin_id)
        for cat in categories:
            if cat['name'] == category_name:
                return cat['id']
        return None
    
    # Import 方法（保持向后兼容）
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
