"""快速复制业务服务。"""

from typing import Any, Dict, List, Union

from storage.database import DatabaseManager

ItemType = Union[str, Dict[str, str]]


class QuickCopyService:
    """封装快速复制的数据访问和更新规则。"""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()

    @property
    def _repo(self):
        return self.db.quick_copy

    def list_cards(self) -> List[Dict[str, Any]]:
        """获取卡片及其内容项。"""
        cards = self._repo.get_cards_with_items()
        return [
            {
                "id": card["id"],
                "title": card["title"],
                "items": [
                    {"content": item["content"], "remark": item.get("remark", "")}
                    for item in card.get("items", [])
                ]
            }
            for card in cards
        ]

    def add_card(self, title: str, sort_order: int) -> Dict[str, Any]:
        """添加快速复制卡片。"""
        card_id = self._repo.add_card(title, sort_order)
        return {
            "id": card_id,
            "title": title,
            "items": []
        }

    def update_card(self, card_id: int, title: str, items: List[ItemType]) -> None:
        """更新卡片标题和内容项。"""
        self._repo.update_card(card_id, title=title)

        existing_items = self._repo.get_items(card_id)
        for index, item in enumerate(items):
            if isinstance(item, str):
                content = item
                remark = ""
            else:
                content = item.get("content", "")
                remark = item.get("remark", "")

            if index < len(existing_items):
                self._repo.update_item(
                    existing_items[index]["id"],
                    content=content,
                    sort_order=index,
                    remark=remark
                )
            else:
                self._repo.add_item(card_id, content, index, remark)

        for item in existing_items[len(items):]:
            self._repo.delete_item(item["id"])

    def delete_card(self, card_id: int) -> bool:
        """删除卡片。"""
        return self._repo.delete_card(card_id)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索快速复制内容。"""
        return self._repo.search(query, limit)