import sqlite3
import threading
from typing import Optional
from pathlib import Path

from core.utils import get_app_data_path


class Database:
    _instance: Optional['Database'] = None
    _connection: Optional[sqlite3.Connection] = None
    # 类级锁：__init__ 会被重复调用，实例属性锁可能被替换，类属性对单例始终一致
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None:
            self._connect()

    def _create_connection(self) -> sqlite3.Connection:
        """创建新连接并完成建表迁移，全部成功后才返回（失败不影响现有连接）"""
        db_path: Path = get_app_data_path("data/notes/notes.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(db_path), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self._init_tables(connection)
        return connection

    def _connect(self):
        with self._lock:
            self._connection = self._create_connection()

    def _init_tables(self, connection: sqlite3.Connection):
        cursor = connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category_id INTEGER,
                tags TEXT,
                code_blocks TEXT,
                remarks TEXT,
                images TEXT,
                is_archived INTEGER DEFAULT 0,
                is_favorite INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        ''')

        cursor.execute("SELECT COUNT(*) FROM categories WHERE name = '默认'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO categories (name) VALUES ('默认')")

        # 迁移：为旧库补充 sort_order 列（按 created_at 顺序初始化）
        columns = [row[1] for row in cursor.execute("PRAGMA table_info(categories)").fetchall()]
        if 'sort_order' not in columns:
            cursor.execute("ALTER TABLE categories ADD COLUMN sort_order INTEGER DEFAULT 0")
            cursor.execute(
                "UPDATE categories SET sort_order = id "
                "WHERE sort_order = 0"
            )

        connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        with self._lock:
            return self._connection

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(query, params)
        return cursor

    def commit(self):
        with self._lock:
            self._connection.commit()

    def close(self):
        with self._lock:
            if self._connection:
                self._connection.close()
                self._connection = None

    @classmethod
    def get_instance(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reinitialize(cls) -> 'Database':
        """重建数据库连接并重跑建表迁移（数据恢复后调用）。

        线程安全：先在新连接上完成全部初始化，再持锁原子替换引用；
        失败时保留旧连接。旧连接不主动 close——正在使用它的线程
        （如全局搜索线程池）通过游标持有引用，待其查询结束后由
        引用计数自动回收，避免 "Cannot operate on a closed database"。
        """
        instance = cls.get_instance()
        with cls._lock:
            instance._connection = instance._create_connection()
        return instance
