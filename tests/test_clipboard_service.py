from storage import DatabaseManager, MigrationManager
from plugins.clipboard.service import ClipboardService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_clipboard_service_history_flow(tmp_path):
    """剪切板服务覆盖新增、列表、搜索、删除、清空链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "clipboard_service.db"))
    service = ClipboardService(db)

    item_id = service.add_item("text", "hello clipboard")
    history = service.list_history()

    assert len(history) == 1
    assert history[0]["id"] == item_id
    assert history[0]["type"] == "text"
    assert history[0]["content"] == "hello clipboard"

    results = service.search("clipboard")
    assert len(results) == 1
    assert results[0]["id"] == item_id

    assert service.delete_item(item_id)
    assert service.list_history() == []

    service.add_item("text", "one")
    service.add_item("text", "two")
    assert service.clear_history()
    assert service.list_history() == []
    reset_database_singleton()


def test_clipboard_migration_adds_repository_columns(tmp_path):
    """迁移管理器为旧剪切板表补齐仓储写入需要的字段"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "clipboard_migration.db"))

    with db.get_connection() as conn:
        conn.execute("DROP TABLE clipboard_history")
        conn.execute("""
            CREATE TABLE clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL DEFAULT 'text',
                content TEXT NOT NULL
            )
        """)
        conn.commit()

        MigrationManager().run_migrations(conn)

        columns = [row[1] for row in conn.execute("PRAGMA table_info(clipboard_history)").fetchall()]

    assert "plugin_id" in columns
    assert "content_type" in columns

    item_id = ClipboardService(db).add_item("text", "after migration")
    assert item_id > 0
    reset_database_singleton()
