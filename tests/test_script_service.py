from storage import DatabaseManager
from plugins.script_manager.service import ScriptService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_script_service_category_script_flow(tmp_path):
    """脚本服务覆盖分类、脚本新增、更新、搜索、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "script_service.db"))
    service = ScriptService("script_manager_test", db)

    category_id = service.add_category("自动化")
    assert service.list_category_names() == ["自动化"]

    script_id = service.add_script(
        name="构建",
        content="echo build",
        script_type="bat",
        category_name="自动化",
        description="构建脚本",
    )

    scripts = service.list_scripts(category_id)
    assert scripts[0]["id"] == script_id
    assert scripts[0]["category_name"] == "自动化"
    assert service.script_exists("构建")

    assert service.update_script(script_id, name="快速构建", content="echo fast")
    assert service.search_scripts("快速")[0]["content"] == "echo fast"

    assert service.delete_script(script_id)
    assert service.list_scripts(category_id) == []

    assert service.delete_category(category_id)
    assert service.list_categories() == []
    reset_database_singleton()
