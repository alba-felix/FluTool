from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class ToolkitService:
    """工具集业务服务，隔离界面与数据库访问"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def list_categories(self) -> List[Dict[str, Any]]:
        """获取分类列表"""
        return self.db.get_categories(self.plugin_id)

    def list_category_names(self) -> List[str]:
        """获取分类名称列表"""
        return [category["name"] for category in self.list_categories()]

    def add_category(self, name: str) -> int:
        """添加分类"""
        return self.db.add_category(self.plugin_id, name)

    def update_category(self, category_id: int, name: str) -> bool:
        """更新分类"""
        return self.db.update_category(self.plugin_id, category_id, name)

    def delete_category(self, category_id: int) -> bool:
        """删除分类"""
        return self.db.delete_category(self.plugin_id, category_id)

    def list_tools(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取工具列表"""
        return self.db.get_commands(self.plugin_id, category_id)

    def search_tools(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索工具"""
        return self.db.search_commands(self.plugin_id, keyword)

    def add_tool(self, name: str, content: str, sub_title: str = "", category_name: str = "") -> int:
        """添加工具"""
        return self.db.add_command(
            plugin_id=self.plugin_id,
            name=name,
            content=content,
            sub_title=sub_title,
            category_name=category_name,
        )

    def update_tool(self, tool_id: int, name: str, content: str,
                    sub_title: str = "", category_name: str = "") -> bool:
        """更新工具"""
        kwargs = {
            "name": name,
            "content": content,
            "sub_title": sub_title,
        }
        if category_name:
            kwargs["category_id"] = self.resolve_category_id(category_name)
        return self.db.update_command(self.plugin_id, tool_id, **kwargs)

    def delete_tool(self, tool_id: int) -> bool:
        """删除工具"""
        return self.db.delete_command(self.plugin_id, tool_id)

    def resolve_category_id(self, category_name: str) -> Optional[int]:
        """根据分类名称解析分类 ID"""
        if not category_name:
            return None

        for category in self.list_categories():
            if category["name"] == category_name:
                return category["id"]
        return None
