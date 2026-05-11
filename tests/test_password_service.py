from storage import DatabaseManager
from plugins.password.service import PasswordService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_password_service_category_password_flow(tmp_path):
    """密码服务覆盖分类、密码新增、移动、搜索、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "password_service.db"))
    service = PasswordService("password_test", db)

    category_id = service.add_category("工作")
    archive_id = service.add_category("归档")
    assert service.list_category_choices() == [("工作", category_id), ("归档", archive_id)]

    password_id = service.add_password(
        platform="GitHub",
        username="dev",
        password="encrypted:secret",
        category_id=category_id,
        email="dev@example.com",
        notes="代码托管",
    )

    passwords = service.list_passwords(category_id)
    assert passwords[0]["id"] == password_id
    assert passwords[0]["category_name"] == "工作"

    assert service.update_password(password_id, category_id=archive_id, notes="主账号")
    assert service.list_passwords(archive_id)[0]["notes"] == "主账号"
    assert service.search_passwords("GitHub")[0]["id"] == password_id

    assert service.delete_password(password_id)
    assert service.list_passwords(archive_id) == []

    assert service.delete_category(category_id)
    assert service.delete_category(archive_id)
    assert service.list_categories() == []
    reset_database_singleton()
