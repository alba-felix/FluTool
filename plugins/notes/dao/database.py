import sqlite3
from typing import Optional
from pathlib import Path

from core.utils import get_app_data_path


class Database:
    _instance: Optional['Database'] = None
    _connection: Optional[sqlite3.Connection] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None:
            self._connect()

    def _connect(self):
        db_path: Path = get_app_data_path("data/notes/notes.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(db_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._init_tables()

    def _init_tables(self):
        cursor = self._connection.cursor()

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

        self._connection.commit()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._connection

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self._connection.commit()

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    @classmethod
    def get_instance(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance