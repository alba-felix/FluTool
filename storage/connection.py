import sqlite3
from contextlib import contextmanager
from pathlib import Path


class DatabaseConnection:
    """数据库连接工厂，统一配置 SQLite 连接参数"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    @contextmanager
    def get_connection(self):
        """获取已启用外键约束的 SQLite 连接"""
        if self.db_path is None:
            raise RuntimeError("Database path is not configured.")

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
