"""调色板插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class ColorPaletteService:
    """封装调色板插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def color_exists(self, color_hex: str) -> bool:
        """检查颜色是否已收藏。"""
        return self.db.color_exists(self.plugin_id, color_hex)

    def add_color(
        self,
        name: str,
        color_hex: str,
        color_rgb: str,
        category_name: str = None,
        notes: str = "",
    ) -> int:
        """添加收藏颜色。"""
        return self.db.add_color(
            plugin_id=self.plugin_id,
            name=name,
            color_hex=color_hex,
            color_rgb=color_rgb,
            category_name=category_name,
            notes=notes,
        )

    def list_colors(self) -> List[Dict[str, Any]]:
        """获取收藏颜色。"""
        return self.db.get_colors(self.plugin_id)

    def search_colors(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索收藏颜色。"""
        return self.db.search_colors(self.plugin_id, keyword)

    def delete_color(self, color_id: int) -> bool:
        """删除收藏颜色。"""
        return self.db.delete_color(self.plugin_id, color_id)

    def delete_colors_by_hex(self, color_hex_values: List[str]) -> int:
        """按 HEX 值批量删除收藏颜色，返回删除数量。"""
        color_hex_set = set(color_hex_values)
        if not color_hex_set:
            return 0

        deleted_count = 0
        for color_data in self.list_colors():
            if color_data.get("color_hex") in color_hex_set and self.delete_color(color_data["id"]):
                deleted_count += 1
        return deleted_count

    def clear_colors(self) -> int:
        """清空当前插件的收藏颜色，返回删除数量。"""
        deleted_count = 0
        for color_data in self.list_colors():
            if self.delete_color(color_data["id"]):
                deleted_count += 1
        return deleted_count
