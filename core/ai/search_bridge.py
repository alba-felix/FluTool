from typing import List

from core.search import SearchResult


class AISearchBridge:
    """将全局搜索结果转为 AI 可消费的上下文文本"""

    def __init__(self, search_manager):
        self._search_manager = search_manager

    def search_context(self, query: str, limit: int = 5) -> str:
        if not self._search_manager:
            return ""
        if not query or not query.strip():
            return ""

        results: List[SearchResult] = self._search_manager.search(query.strip())
        if not results:
            return ""

        lines = []
        for index, item in enumerate(results[:limit], start=1):
            line = (
                f"{index}. [{item.plugin_name}] 标题: {item.title}; "
                f"描述: {item.description}"
            )
            lines.append(line)
        return "\n".join(lines)
