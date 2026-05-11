from storage import DatabaseManager
from storage.migration import MigrationManager


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_database_connection_enables_foreign_keys(tmp_path):
    """数据库连接默认启用 SQLite 外键约束"""
    reset_database_singleton()
    db = DatabaseManager()
    assert not db.is_initialized

    db.initialize(str(tmp_path / "foreign_keys.db"))
    assert db.is_initialized
    assert db.db_path == tmp_path / "foreign_keys.db"

    with db.get_connection() as conn:
        enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1
    reset_database_singleton()


def test_quick_copy_items_cascade_when_card_deleted_directly(tmp_path):
    """删除快速复制卡片时由数据库级联删除内容项"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "quick_copy_cascade.db"))

    card_id = db.quick_copy.add_card("测试卡片")
    item_id = db.quick_copy.add_item(card_id, "测试内容")

    with db.get_connection() as conn:
        conn.execute("DELETE FROM quick_copy_cards WHERE id = ?", (card_id,))
        conn.commit()

    with db.get_connection() as conn:
        item = conn.execute("SELECT id FROM quick_copy_items WHERE id = ?", (item_id,)).fetchone()

    assert item is None
    reset_database_singleton()


def test_migration_manager_adds_todo_status_column(tmp_path):
    """迁移管理器为旧 todos 表补 status 字段并修正已完成状态"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "migration_base.db"))

    with db.get_connection() as conn:
        conn.execute("DROP TABLE todos")
        conn.execute("""
            CREATE TABLE todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO todos (title, completed) VALUES (?, ?)", ("旧任务", 1))
        conn.commit()

        MigrationManager().run_migrations(conn)

        columns = [row[1] for row in conn.execute("PRAGMA table_info(todos)").fetchall()]
        row = conn.execute("SELECT status FROM todos WHERE title = ?", ("旧任务",)).fetchone()

    assert "status" in columns
    assert row["status"] == "已完成"
    reset_database_singleton()
