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
        return self.db.commands.get_by_plugin(self.plugin_id, category_id)

    def search_commands(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索命令。"""
        return self.db.commands.search(self.plugin_id, keyword)

    def list_categories(self) -> List[Dict[str, Any]]:
        """获取分类列表。"""
        return self.db.categories.get_by_plugin(self.plugin_id)

    def list_category_names(self) -> List[str]:
        """获取分类名称列表。"""
        return [category["name"] for category in self.list_categories()]

    def add_category(self, name: str) -> int:
        """添加分类。"""
        return self.db.categories.add_or_get(self.plugin_id, name)

    def update_category(self, category_id: int, name: str) -> bool:
        """更新分类。"""
        return self.db.categories.update(category_id, name=name)

    def delete_category(self, category_id: int) -> bool:
        """删除分类。"""
        return self.db.categories.delete(category_id)

    def add_command(self, name: str, content: str, category_name: str = None,
                    sub_title: str = "") -> int:
        """添加命令。"""
        category_id = self.resolve_category_id(category_name)
        return self.db.commands.add(
            plugin_id=self.plugin_id,
            category_id=category_id,
            name=name,
            sub_title=sub_title,
            content=content,
            sort_order=0,
        )

    def batch_add_commands(self, commands_data: Dict[str, List[Dict[str, Any]]]) -> int:
        """批量添加命令，按分类组织。

        Args:
            commands_data: {分类名: [{name, content, sub_title?}, ...], ...}

        Returns:
            实际添加的命令数量
        """
        count = 0
        for category_name, commands in commands_data.items():
            if not isinstance(commands, list):
                continue
            category_id = self.db.categories.add_or_get(self.plugin_id, category_name)
            for cmd in commands:
                if self.db.commands.exists(self.plugin_id, cmd['name'], category_name):
                    continue
                self.db.commands.add(
                    plugin_id=self.plugin_id,
                    category_id=category_id,
                    name=cmd['name'],
                    sub_title=cmd.get('sub_title', ''),
                    content=cmd['content'],
                    sort_order=count,
                )
                count += 1
        return count

    def update_command(self, command_id: int, **kwargs) -> bool:
        """更新命令。"""
        return self.db.commands.update(command_id, **kwargs)

    def delete_command(self, command_id: int) -> bool:
        """删除命令。"""
        return self.db.commands.delete(command_id)

    def resolve_category_id(self, category_name: str) -> Optional[int]:
        """根据分类名称解析分类 ID。"""
        if not category_name:
            return None

        for category in self.list_categories():
            if category["name"] == category_name:
                return category["id"]
        return None

