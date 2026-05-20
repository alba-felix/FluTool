from typing import List, Dict, Any, Optional

from storage import DatabaseManager


PLUGIN_ID = 'text_tools_vocabulary'


class VocabularyService:
    """单词背诵业务服务"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    # ============ 分类操作（委托给 CategoryRepository） ============

    def add_category(self, name: str) -> int:
        return self.db.categories.add_or_get(PLUGIN_ID, name)

    def list_categories(self) -> List[Dict[str, Any]]:
        return self.db.get_categories(PLUGIN_ID)

    def update_category(self, category_id: int, name: str) -> bool:
        return self.db.update_category(PLUGIN_ID, category_id, name=name)

    def delete_category(self, category_id: int) -> bool:
        return self.db.categories.delete(category_id)

    # ============ 单词操作（委托给 VocabularyRepository） ============

    def add_word(
        self, chinese: str, english: str, pronunciation: str = "",
        category_id: Optional[int] = None
    ) -> int:
        return self.db.vocab_words.add(
            plugin_id=PLUGIN_ID, category_id=category_id,
            chinese=chinese.strip(), english=english.strip(),
            pronunciation=pronunciation.strip(),
        )

    def list_words(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.db.vocab_words.get_by_plugin(PLUGIN_ID, category_id)

    def update_word(
        self, word_id: int, chinese: str = None, english: str = None,
        pronunciation: str = None, category_id: int = None
    ) -> bool:
        kwargs = {}
        if chinese is not None:
            kwargs['chinese'] = chinese.strip()
        if english is not None:
            kwargs['english'] = english.strip()
        if pronunciation is not None:
            kwargs['pronunciation'] = pronunciation.strip()
        if category_id is not None:
            kwargs['category_id'] = category_id
        return self.db.vocab_words.update(word_id, **kwargs)

    def delete_word(self, word_id: int) -> bool:
        return self.db.vocab_words.delete(word_id)

    def search_words(self, keyword: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.db.vocab_words.search(PLUGIN_ID, keyword, limit)

    def get_word_count(self, category_id: Optional[int] = None) -> int:
        return self.db.vocab_words.get_word_count(PLUGIN_ID, category_id)

    def seed_demo_data(self) -> None:
        """写入20条模拟数据，用于演示"""
        if self.get_word_count() > 0:
            return

        categories = {
            "日常用语": ["hello", "world", "beautiful", "study", "important"],
            "科技": ["computer", "algorithm", "database", "network", "software"],
            "形容词": ["beautiful", "important", "necessary", "available", "different"],
            "动词": ["study", "participate", "concatenate", "appropriate", "convention"],
        }

        words = [
            ("hello", "你好", "/həˈloʊ/"),
            ("world", "世界", "/wɜːrld/"),
            ("computer", "计算机", "/kəmˈpjuːtər/"),
            ("beautiful", "美丽的", "/ˈbjuːtɪfl/"),
            ("study", "学习", "/ˈstʌdi/"),
            ("important", "重要的", "/ɪmˈpɔːrtnt/"),
            ("algorithm", "算法", "/ˈælɡərɪðəm/"),
            ("database", "数据库", "/ˈdeɪtəbeɪs/"),
            ("network", "网络", "/ˈnetwɜːrk/"),
            ("software", "软件", "/ˈsɔːftwer/"),
            ("necessary", "必要的", "/ˈnesəseri/"),
            ("available", "可用的", "/əˈveɪləbl/"),
            ("different", "不同的", "/ˈdɪfrənt/"),
            ("participate", "参与", "/pɑːrˈtɪsɪpeɪt/"),
            ("concatenate", "连接", "/kɒnˈkætɪneɪt/"),
            ("appropriate", "适当的", "/əˈproʊpriət/"),
            ("convention", "惯例", "/kənˈvenʃn/"),
            ("carbohydrate", "碳水化合物", "/ˌkɑːrboʊˈhaɪdreɪt/"),
            ("recursive", "递归的", "/rɪˈkɜːrsɪv/"),
            ("literal", "字面的", "/ˈlɪtərəl/"),
        ]

        cat_ids = {}
        for cat_name in categories:
            cat_ids[cat_name] = self.add_category(cat_name)

        for en, cn, pron in words:
            cat_name = next(
                (c for c, ws in categories.items() if en in ws),
                "日常用语"
            )
            self.add_word(cn, en, pron, cat_ids[cat_name])