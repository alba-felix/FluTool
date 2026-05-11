"""AI 助手插件业务服务。"""

from typing import Optional

from storage import DatabaseManager
from storage.repositories import AIRepository


class AIAssistantService:
    """封装 AI 助手的数据仓储访问。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.repo = AIRepository(db or DatabaseManager())

    def __getattr__(self, name):
        """临时转发仓储方法，保持 UI 调用面稳定。"""
        return getattr(self.repo, name)

    def update_conversation_title(self, conversation_id: int, title: str) -> bool:
        """更新对话标题。"""
        return self.repo.update_conversation(conversation_id, title=title)

    def search_conversations(self, keyword: str, limit: int = 100):
        """按标题搜索对话。"""
        keyword_lower = keyword.lower()
        matches = [
            conversation
            for conversation in self.repo.get_conversations()
            if keyword_lower in conversation.get("title", "").lower()
        ]
        return matches[:limit]
