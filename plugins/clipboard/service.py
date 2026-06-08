"""剪切板插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class ClipboardService:
    """封装剪切板插件的数据访问。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    @property
    def _repo(self):
        return self.db.clipboard

    def add_item(self, item_type: str, content: str, format: str = "") -> int:
        """添加剪切板历史项。"""
        return self._repo.add(item_type, content, format)

    def list_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取剪切板历史。"""
        return self._repo.get_history(limit)

    def delete_item(self, item_id: int) -> bool:
        """删除剪切板历史项。"""
        return self._repo.delete(item_id)

    def clear_history(self) -> bool:
        """清空剪切板历史。"""
        return self._repo.clear()

    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索剪切板历史。"""
        return self._repo.search(keyword, limit)
