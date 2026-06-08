"""调色板插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class ColorPaletteService:
    """封装调色板插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def _resolve_category_id(self, category_name: Optional[str]) -> Optional[int]:
        """根据分类名称解析分类ID"""
        if not category_name:
            return None
        for cat in self.db.categories.get_by_plugin(self.plugin_id):
            if cat["name"] == category_name:
                return cat["id"]
        return None

    def color_exists(self, color_hex: str) -> bool:
        """检查颜色是否已收藏。"""
        return self.db.colors.exists(self.plugin_id, color_hex)

    def add_color(
        self,
        name: str,
        color_hex: str,
        color_rgb: str,
        category_name: str = None,
        notes: str = "",
    ) -> int:
        """添加收藏颜色。"""
        category_id = self._resolve_category_id(category_name)
        return self.db.colors.add(
            plugin_id=self.plugin_id,
            category_id=category_id,
            name=name,
            color_hex=color_hex,
            color_rgb=color_rgb,
            notes=notes,
            sort_order=0,
        )

    def list_colors(self) -> List[Dict[str, Any]]:
        """获取收藏颜色。"""
        return self.db.colors.get_by_plugin(self.plugin_id)

    def search_colors(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索收藏颜色。"""
        return self.db.colors.search(self.plugin_id, keyword)

    def delete_color(self, color_id: int) -> bool:
        """删除收藏颜色。"""
        return self.db.colors.delete(color_id)

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
