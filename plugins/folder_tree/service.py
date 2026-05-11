"""文件夹树插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class FolderTreeService:
    """封装文件夹树规则的数据访问。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    @property
    def is_ready(self) -> bool:
        """数据库是否已初始化。"""
        return bool(getattr(self.db, "is_initialized", False))

    def list_rules(self) -> List[Dict[str, Any]]:
        """获取所有自定义规则。"""
        if not self.is_ready:
            return []
        return self.db.get_all_folder_tree_rules()

    def add_rule(self, rule_name: str, exclude_items: List[str]) -> int:
        """添加自定义规则。"""
        return self.db.add_folder_tree_rule(rule_name, exclude_items)

    def update_rule(self, rule_name: str, exclude_items: List[str]) -> bool:
        """更新自定义规则。"""
        return self.db.update_folder_tree_rule(rule_name, exclude_items)

    def delete_rule(self, rule_name: str) -> bool:
        """删除自定义规则。"""
        return self.db.delete_folder_tree_rule(rule_name)

    def rename_rule(self, old_name: str, new_name: str, exclude_items: List[str]) -> int:
        """重命名规则。"""
        self.delete_rule(old_name)
        return self.add_rule(new_name, exclude_items)

    def search_rules(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索自定义规则。"""
        if not self.is_ready:
            return []
        return self.db.search_folder_tree_rules(keyword)
