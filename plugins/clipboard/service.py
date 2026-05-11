"""剪切板插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class ClipboardService:
    """封装剪切板插件的数据访问。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def add_item(self, item_type: str, content: str, format: str = "") -> int:
        """添加剪切板历史项。"""
        return self.db.add_clipboard_item(item_type, content, format)

    def list_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取剪切板历史。"""
        return self.db.get_clipboard_history(limit)

    def delete_item(self, item_id: int) -> bool:
        """删除剪切板历史项。"""
        return self.db.delete_clipboard_item(item_id)

    def clear_history(self) -> bool:
        """清空剪切板历史。"""
        return self.db.clear_clipboard_history()

    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索剪切板历史。"""
        return self.db.search_clipboard(keyword, limit)
