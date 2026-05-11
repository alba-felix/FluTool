from storage import DatabaseManager
from plugins.toolkit.service import ToolkitService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_toolkit_service_category_tool_flow(tmp_path):
    """工具集服务覆盖分类、工具新增、更新、搜索、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "toolkit_service.db"))
    service = ToolkitService("toolkit_test", db)

    category_id = service.add_category("脚本")
    assert service.list_category_names() == ["脚本"]

    tool_id = service.add_tool(
        name="打开目录",
        content="explorer .",
        sub_title="文件管理",
        category_name="脚本",
    )

    tools = service.list_tools(category_id)
    assert len(tools) == 1
    assert tools[0]["id"] == tool_id
    assert tools[0]["category_name"] == "脚本"

    new_category_id = service.add_category("常用")
    assert service.update_tool(
        tool_id,
        name="打开项目",
        content="explorer H:\\Programming",
        sub_title="项目目录",
        category_name="常用",
    )

    moved_tools = service.list_tools(new_category_id)
    assert moved_tools[0]["name"] == "打开项目"
    assert service.search_tools("项目")[0]["id"] == tool_id

    assert service.delete_tool(tool_id)
    assert service.list_tools(new_category_id) == []

    assert service.delete_category(category_id)
    assert service.delete_category(new_category_id)
    reset_database_singleton()
