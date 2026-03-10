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
        self._create_tables()
    
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
                
                CREATE INDEX IF NOT EXISTS idx_bookmarks_plugin_id ON bookmarks(plugin_id);
                CREATE INDEX IF NOT EXISTS idx_bookmarks_category_id ON bookmarks(category_id);
                CREATE INDEX IF NOT EXISTS idx_categories_plugin_id ON categories(plugin_id);
                CREATE INDEX IF NOT EXISTS idx_commands_plugin_id ON commands(plugin_id);
                CREATE INDEX IF NOT EXISTS idx_commands_category_id ON commands(category_id);
                CREATE INDEX IF NOT EXISTS idx_passwords_plugin_id ON passwords(plugin_id);
                CREATE INDEX IF NOT EXISTS idx_passwords_category_id ON passwords(category_id);
                CREATE INDEX IF NOT EXISTS idx_app_launcher_plugin_id ON app_launcher(plugin_id);
                CREATE INDEX IF NOT EXISTS idx_app_launcher_category_id ON app_launcher(category_id);
            ''')
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
    
    def update_category(self, plugin_id: str, category_id: int, name: str) -> bool:
        """更新分类名称"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "UPDATE categories SET name = ? WHERE plugin_id = ? AND id = ?",
                (name, plugin_id, category_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_category(self, plugin_id: str, category_id: int) -> bool:
        """删除分类"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM categories WHERE plugin_id = ? AND id = ?",
                (plugin_id, category_id)
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
    
    # ==================== Password methods ====================
    
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
    
    # ==================== App Launcher methods ====================
    
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
