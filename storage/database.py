from pathlib import Path
from typing import Optional

from storage.connection import DatabaseConnection
from storage.migration import MigrationManager
from storage.schema import SchemaManager
from storage.repository_registry import RepositoryRegistry


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

    @classmethod
    def reset_instance(cls) -> None:
        """重置数据库单例，主要用于测试隔离"""
        cls._instance = None
        cls._db_path = None
    
    def initialize(self, db_path: str) -> None:
        """初始化数据库"""
        if self._initialized:
            return
        self._initialized = True
        self._db_path = Path(db_path)
        self._connection = DatabaseConnection(self._db_path)
        self._repositories = None
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[DatabaseManager] Initializing database at: {self._db_path}")
        print(f"[DatabaseManager] Database exists: {self._db_path.exists()}")
        self._create_tables()
        print(f"[DatabaseManager] Tables created/verified")
        
        # 初始化所有 Repository
        self._init_repositories()

    def reinitialize(self, db_path: Optional[str] = None) -> None:
        """重新初始化数据库连接和仓储，用于数据恢复后重建状态。"""
        if db_path is not None:
            self._db_path = Path(db_path)
        if self._db_path is None:
            raise RuntimeError("Database path is not configured. Call initialize() first.")

        self._initialized = True
        self._connection = DatabaseConnection(self._db_path)
        self._repositories = None
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
        self._init_repositories()
    
    def _init_repositories(self):
        """初始化所有 Repository 实例"""
        self._repositories = RepositoryRegistry(self)
        for name, repository in self._repositories.as_dict().items():
            setattr(self, name, repository)

    @property
    def db_path(self) -> Optional[Path]:
        """获取当前数据库路径"""
        return self._db_path

    @property
    def is_initialized(self) -> bool:
        """检查数据库是否已初始化"""
        return bool(getattr(self, "_initialized", False) and self._db_path is not None)
    
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        if self._db_path is None or not hasattr(self, "_connection"):
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._connection.get_connection()
    
    def _create_tables(self) -> None:
        """创建基础表结构"""
        with self.get_connection() as conn:
            SchemaManager().create_tables(conn)

    def _migrate_ai_tables(self, conn) -> None:
        """迁移 AI 表，处理旧结构问题"""
        MigrationManager().migrate_ai_tables(conn)
    
    def _run_migrations(self, conn) -> None:
        """运行数据库迁移，添加缺失的列"""
        MigrationManager().run_migrations(conn)
    
    def _create_indexes(self, conn) -> None:
        """创建索引"""
        SchemaManager().create_indexes(conn)
