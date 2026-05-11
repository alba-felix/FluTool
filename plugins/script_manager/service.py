"""脚本管理插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class ScriptService:
    """封装脚本管理插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def list_categories(self) -> List[Dict[str, Any]]:
        """获取脚本分类。"""
        return self.db.get_categories(self.plugin_id)

    def list_category_names(self) -> List[str]:
        """获取脚本分类名称。"""
        return [category["name"] for category in self.list_categories()]

    def add_category(self, name: str) -> int:
        """添加脚本分类。"""
        return self.db.add_category(self.plugin_id, name)

    def update_category(self, category_id: int, name: str) -> bool:
        """更新脚本分类。"""
        return self.db.update_category(self.plugin_id, category_id, name)

    def delete_category(self, category_id: int) -> bool:
        """删除脚本分类。"""
        return self.db.delete_category(self.plugin_id, category_id)

    def resolve_category_id(self, category_name: str) -> Optional[int]:
        """根据分类名称解析分类 ID。"""
        if not category_name:
            return None
        for category in self.list_categories():
            if category["name"] == category_name:
                return category["id"]
        return None

    def list_scripts(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取脚本列表。"""
        return self.db.get_scripts(self.plugin_id, category_id)

    def search_scripts(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索脚本。"""
        return self.db.search_scripts(self.plugin_id, keyword)

    def add_script(
        self,
        name: str,
        content: str,
        script_type: str = "bat",
        category_name: str = None,
        category_id: int = None,
        description: str = "",
    ) -> int:
        """添加脚本。"""
        return self.db.add_script(
            plugin_id=self.plugin_id,
            name=name,
            content=content,
            script_type=script_type,
            category_name=category_name,
            category_id=category_id,
            description=description,
        )

    def update_script(self, script_id: int, **kwargs) -> bool:
        """更新脚本。"""
        return self.db.update_script(self.plugin_id, script_id, **kwargs)

    def delete_script(self, script_id: int) -> bool:
        """删除脚本。"""
        return self.db.delete_script(self.plugin_id, script_id)

    def script_exists(self, name: str) -> bool:
        """检查脚本名称是否存在。"""
        return self.db.script_exists(self.plugin_id, name)

    def ensure_scripts(self, scripts: List[Dict[str, Any]]) -> int:
        """确保内置脚本存在，返回新增数量。"""
        created_count = 0
        for script in scripts:
            if self.script_exists(script["name"]):
                continue
            self.add_script(
                name=script["name"],
                content=script["content"],
                script_type=script["script_type"],
                description=script["description"],
            )
            created_count += 1
        return created_count
