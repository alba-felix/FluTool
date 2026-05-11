"""命令插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class CommandService:
    """封装命令插件的数据访问。"""

    def __init__(self, plugin_id: str, db: DatabaseManager = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def list_commands(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取命令列表。"""
        return self.db.get_commands(self.plugin_id, category_id)

    def search_commands(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索命令。"""
        return self.db.search_commands(self.plugin_id, keyword)

    def list_categories(self) -> List[Dict[str, Any]]:
        """获取分类列表。"""
        return self.db.get_categories(self.plugin_id)

    def list_category_names(self) -> List[str]:
        """获取分类名称列表。"""
        return [category["name"] for category in self.list_categories()]

    def add_category(self, name: str) -> int:
        """添加分类。"""
        return self.db.add_category(self.plugin_id, name)

    def update_category(self, category_id: int, name: str) -> bool:
        """更新分类。"""
        return self.db.update_category(self.plugin_id, category_id, name)

    def delete_category(self, category_id: int) -> bool:
        """删除分类。"""
        return self.db.delete_category(self.plugin_id, category_id)

    def add_command(self, name: str, content: str, category_name: str = None,
                    sub_title: str = "") -> int:
        """添加命令。"""
        return self.db.add_command(
            plugin_id=self.plugin_id,
            name=name,
            content=content,
            category_name=category_name,
            sub_title=sub_title
        )

    def update_command(self, command_id: int, **kwargs) -> bool:
        """更新命令。"""
        return self.db.update_command(self.plugin_id, command_id, **kwargs)

    def delete_command(self, command_id: int) -> bool:
        """删除命令。"""
        return self.db.delete_command(self.plugin_id, command_id)

    def resolve_category_id(self, category_name: str) -> Optional[int]:
        """根据分类名称解析分类 ID。"""
        if not category_name:
            return None

        for category in self.list_categories():
            if category["name"] == category_name:
                return category["id"]
        return None

