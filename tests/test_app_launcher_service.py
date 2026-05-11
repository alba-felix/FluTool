from storage import DatabaseManager
from plugins.app_launcher.service import AppLauncherService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_app_launcher_service_category_app_flow(tmp_path):
    """应用启动器服务覆盖分类、应用、新近、收藏和批量操作链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "app_launcher_service.db"))
    service = AppLauncherService("app_launcher_test", db)

    category_id = service.add_category("常用", icon_name="APPLICATION", color="#009faa")
    assert service.get_category(category_id)["name"] == "常用"

    app_id = service.add_app(
        name="记事本",
        target_path="C:\\Windows\\System32\\notepad.exe",
        category_id=category_id,
        icon_path="data/app_icons/notepad.ico",
    )

    apps = service.list_apps(category_id)
    assert apps[0]["id"] == app_id
    assert apps[0]["category_name"] == "常用"
    assert service.search_apps("记事本")[0]["id"] == app_id

    assert service.record_launch(app_id)
    assert service.list_recent_apps()[0]["id"] == app_id

    assert service.set_favorite(app_id, True)
    assert service.list_favorite_apps()[0]["id"] == app_id

    assert service.batch_update_apps([app_id], notes="系统工具") == 1
    assert service.list_apps(category_id)[0]["notes"] == "系统工具"

    assert service.batch_delete_apps([app_id]) == 1
    assert service.list_apps(category_id) == []

    assert service.delete_category(category_id)
    assert service.list_categories() == []
    reset_database_singleton()
