import ast
from pathlib import Path

from storage import DatabaseManager
from plugins.todo.service import TodoService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_todo_confirmation_dialogs_use_message_box():
    """待办确认框不能用 MessageBoxBase(title, content, parent) 签名"""
    source = Path("plugins/todo/__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    invalid_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id == "MessageBoxBase" and len(node.args) > 1:
            invalid_calls.append(node.lineno)

    assert invalid_calls == []


def test_database_manager_add_todo_accepts_status(tmp_path):
    """待办添加兼容接口支持保存状态字段"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "todo_status.db"))

    todo_id = db.add_todo(title="测试待办", status="未完成")
    todo = db.todos.get_by_id(todo_id)

    assert todo["status"] == "未完成"
    reset_database_singleton()


def test_todo_service_crud_status_flow(tmp_path):
    """待办服务覆盖新增、更新、搜索、切换、删除链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "todo_service.db"))
    service = TodoService(db)

    todo_id = service.add_todo({
        "title": "服务测试",
        "description": "覆盖待办服务",
        "priority": "高",
        "tags": ["service"],
        "status": "进行中",
        "completed": False,
        "pinned": True,
    })

    todo = service.list_todos()[0]
    assert todo["id"] == todo_id
    assert todo["pinned"] == 1
    assert todo["status"] == "进行中"

    assert service.update_todo(todo_id, {
        "title": "服务测试更新",
        "description": "更新内容",
        "priority": "紧急",
        "tags": ["service", "updated"],
        "status": "未完成",
        "completed": False,
        "pinned": False,
    })
    assert service.search("更新")[0]["status"] == "未完成"

    assert service.toggle_completed(todo_id)
    assert service.list_todos()[0]["status"] == "已完成"

    assert service.update_fields(todo_id, completed=0, status="未完成")
    assert service.list_todos()[0]["status"] == "未完成"

    assert service.delete_todo(todo_id)
    assert service.list_todos() == []
    reset_database_singleton()
