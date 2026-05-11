from storage import DatabaseManager
from plugins.bookmark.service import BookmarkService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_bookmark_service_category_bookmark_search_flow(tmp_path):
    """书签服务覆盖分类、书签新增、更新、搜索、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "bookmark_service.db"))

    service = BookmarkService("bookmark_test", db)

    category_id = service.add_category("开发")
    assert category_id > 0
    assert service.list_categories()[0]["name"] == "开发"

    bookmark_id = service.add_bookmark(
        name="Python",
        url="https://python.org",
        category_name="开发",
        notes="语言文档",
    )
    assert bookmark_id > 0

    bookmarks = service.list_bookmarks(category_id)
    assert len(bookmarks) == 1
    assert bookmarks[0]["name"] == "Python"
    assert bookmarks[0]["category_name"] == "开发"

    assert service.update_bookmark(bookmark_id, notes="官方文档")
    assert service.search("官方")[0]["id"] == bookmark_id

    assert service.rename_category(category_id, "编程")
    assert service.list_categories()[0]["name"] == "编程"

    assert service.delete_bookmark(bookmark_id)
    assert service.list_bookmarks(category_id) == []

    assert service.delete_category(category_id)
    assert service.list_categories() == []

    reset_database_singleton()
