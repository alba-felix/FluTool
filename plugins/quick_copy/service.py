"""快速复制业务服务。"""

from typing import Any, Dict, List

from storage.database import DatabaseManager


class QuickCopyService:
    """封装快速复制的数据访问和更新规则。"""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()

    def list_cards(self) -> List[Dict[str, Any]]:
        """获取卡片及其内容项。"""
        cards = self.db.get_quick_copy_cards_with_items()
        return [
            {
                "id": card["id"],
                "title": card["title"],
                "items": [item["content"] for item in card.get("items", [])]
            }
            for card in cards
        ]

    def add_card(self, title: str, sort_order: int) -> Dict[str, Any]:
        """添加快速复制卡片。"""
        card_id = self.db.add_quick_copy_card(title, sort_order)
        return {
            "id": card_id,
            "title": title,
            "items": []
        }

    def update_card(self, card_id: int, title: str, items: List[str]) -> None:
        """更新卡片标题和内容项。"""
        self.db.update_quick_copy_card(card_id, title=title)

        existing_items = self.db.get_quick_copy_items(card_id)
        for index, content in enumerate(items):
            if index < len(existing_items):
                self.db.update_quick_copy_item(
                    existing_items[index]["id"],
                    content=content,
                    sort_order=index
                )
            else:
                self.db.add_quick_copy_item(card_id, content, index)

        for item in existing_items[len(items):]:
            self.db.delete_quick_copy_item(item["id"])

    def delete_card(self, card_id: int) -> bool:
        """删除卡片。"""
        return self.db.delete_quick_copy_card(card_id)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索快速复制内容。"""
        return self.db.search_quick_copy(query, limit)

