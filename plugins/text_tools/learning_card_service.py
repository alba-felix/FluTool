from typing import List, Dict, Any, Optional

from storage import DatabaseManager


PLUGIN_ID = 'text_tools_learning_card'


class LearningCardService:
    """知识卡片业务服务"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    # ============ 分类操作 ============

    def add_category(self, name: str) -> int:
        return self.db.categories.add_or_get(PLUGIN_ID, name)

    def list_categories(self) -> List[Dict[str, Any]]:
        return self.db.get_categories(PLUGIN_ID)

    def update_category(self, category_id: int, name: str) -> bool:
        return self.db.update_category(PLUGIN_ID, category_id, name=name)

    def delete_category(self, category_id: int) -> bool:
        return self.db.categories.delete(category_id)

    # ============ 卡片操作 ============

    def add_card(
        self, title: str, content: str, note: str = "",
        category_id: Optional[int] = None
    ) -> int:
        return self.db.learning_cards.add(
            plugin_id=PLUGIN_ID, category_id=category_id,
            title=title.strip(), content=content.strip(),
            note=note.strip(),
        )

    def list_cards(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.db.learning_cards.get_by_plugin(PLUGIN_ID, category_id)

    def update_card(
        self, card_id: int, title: str = None, content: str = None,
        note: str = None, category_id: int = None
    ) -> bool:
        kwargs = {}
        if title is not None:
            kwargs['title'] = title.strip()
        if content is not None:
            kwargs['content'] = content.strip()
        if note is not None:
            kwargs['note'] = note.strip()
        if category_id is not None:
            kwargs['category_id'] = category_id
        return self.db.learning_cards.update(card_id, **kwargs)

    def delete_card(self, card_id: int) -> bool:
        return self.db.learning_cards.delete(card_id)

    def search_cards(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.db.learning_cards.search(PLUGIN_ID, keyword, limit)

    def get_card_count(self, category_id: Optional[int] = None) -> int:
        return self.db.learning_cards.get_card_count(PLUGIN_ID, category_id)