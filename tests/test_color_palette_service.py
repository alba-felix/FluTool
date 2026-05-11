from storage import DatabaseManager
from plugins.color_palette.service import ColorPaletteService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_color_palette_service_flow(tmp_path):
    """调色板服务覆盖新增、去重查询、搜索、批量删除和清空链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "color_palette_service.db"))
    service = ColorPaletteService("color_palette_test", db)

    red_id = service.add_color("red", "#ff0000", "255,0,0")
    blue_id = service.add_color("blue", "#0000ff", "0,0,255")

    colors = service.list_colors()
    assert {color["id"] for color in colors} == {red_id, blue_id}
    assert service.color_exists("#ff0000")
    assert service.search_colors("blue")[0]["id"] == blue_id

    assert service.delete_colors_by_hex(["#ff0000"]) == 1
    assert not service.color_exists("#ff0000")

    assert service.clear_colors() == 1
    assert service.list_colors() == []
    reset_database_singleton()
