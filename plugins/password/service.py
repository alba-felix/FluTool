"""密码插件业务服务。"""

from typing import Any, Dict, List, Optional, Tuple

from storage import DatabaseManager


class PasswordService:
    """封装密码插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def list_categories(self) -> List[Dict[str, Any]]:
        """获取密码分类。"""
        return self.db.get_categories(self.plugin_id)

    def list_category_choices(self) -> List[Tuple[str, int]]:
        """获取分类名称和 ID 选项。"""
        return [(category["name"], category["id"]) for category in self.list_categories()]

    def add_category(self, name: str) -> int:
        """添加密码分类。"""
        return self.db.add_category(self.plugin_id, name)

    def delete_category(self, category_id: int) -> bool:
        """删除密码分类。"""
        return self.db.delete_category(self.plugin_id, category_id)

    def ensure_default_category(self) -> int:
        """获取首个分类，不存在时创建默认分类。"""
        categories = self.list_categories()
        if categories:
            return categories[0]["id"]
        return self.add_category("默认分类")

    def list_passwords(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取密码列表。"""
        return self.db.get_passwords(self.plugin_id, category_id)

    def add_password(
        self,
        username: str,
        password: str,
        platform: str = "",
        category_id: Optional[int] = None,
        email: str = "",
        notes: str = "",
    ) -> int:
        """添加密码。"""
        return self.db.add_password(
            plugin_id=self.plugin_id,
            username=username,
            password=password,
            platform=platform,
            category_id=category_id,
            email=email,
            notes=notes,
        )

    def update_password(self, password_id: int, **kwargs) -> bool:
        """更新密码。"""
        return self.db.update_password(self.plugin_id, password_id, **kwargs)

    def delete_password(self, password_id: int) -> bool:
        """删除密码。"""
        return self.db.delete_password(self.plugin_id, password_id)

    def search_passwords(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索密码。"""
        return self.db.search_passwords(self.plugin_id, keyword)
