from storage import DatabaseManager
from plugins.folder_tree.service import FolderTreeService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_folder_tree_service_rule_flow(tmp_path):
    """文件夹树服务覆盖规则新增、更新、重命名、搜索、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "folder_tree_service.db"))
    service = FolderTreeService(db)

    rule_id = service.add_rule("前端", ["node_modules", ".git"])
    assert rule_id > 0
    assert service.list_rules()[0]["exclude_items"] == ["node_modules", ".git"]

    assert service.update_rule("前端", ["node_modules", "dist"])
    assert service.search_rules("前端")[0]["exclude_items"] == ["node_modules", "dist"]

    new_rule_id = service.rename_rule("前端", "构建产物", ["dist", "build"])
    assert new_rule_id > 0
    assert service.search_rules("前端") == []
    assert service.search_rules("构建")[0]["exclude_items"] == ["dist", "build"]

    assert service.delete_rule("构建产物")
    assert service.list_rules() == []
    reset_database_singleton()
