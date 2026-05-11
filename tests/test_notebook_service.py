from storage import DatabaseManager
from plugins.notebook.service import NotebookService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_notebook_service_note_flow(tmp_path):
    """随手记服务覆盖新增、更新、搜索、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "notebook_service.db"))
    service = NotebookService("notebook_test", db)

    note_id = service.add_note(
        title="今日记录",
        content="完成 service 重构",
        note_type="markdown",
    )

    note = service.get_note(note_id)
    assert note["title"] == "今日记录"
    assert service.note_exists("今日记录")

    assert service.update_note(note_id, content="完成 notebook service 重构")
    assert service.search_notes("notebook")[0]["id"] == note_id

    assert service.delete_note(note_id)
    assert service.list_notes() == []
    reset_database_singleton()
