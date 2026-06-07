"""全局搜索功能"""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
from qfluentwidgets import FluentIcon


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    plugin_id: str
    plugin_name: str
    title: str
    description: str
    icon: FluentIcon
    relevance: float
    action: Callable
    metadata: Dict[str, Any]


class LRUCache:
    """简单的 LRU 缓存实现"""

    def __init__(self, maxsize: int = 32):
        self._maxsize = maxsize
        self._data: OrderedDict = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: Any) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()


class GlobalSearchManager:
    """全局搜索管理器
    
    提供：
    - 按插件隔离搜索，单个插件超时不阻塞整体
    - 搜索结果 LRU 缓存
    - 搜索超时控制
    """
    
    # 每个插件的最长搜索时间（秒）
    PLUGIN_TIMEOUT = 2.0
    # 搜索结果 LRU 缓存上限
    CACHE_SIZE = 64
    # 返回结果上限
    MAX_RESULTS = 50

    def __init__(self):
        self._plugins: Dict[str, Any] = {}
        self._cache = LRUCache(self.CACHE_SIZE)
        # 线程数不宜过多，避免频繁切换开销；设为 4 兼顾响应和开销
        self._executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="globalsearch"
        )

    def register_plugin(self, plugin) -> None:
        """注册插件到搜索管理器

        Args:
            plugin: 插件实例
        """
        if plugin.supports_search():
            self._plugins[plugin.get_id()] = plugin

    def unregister_plugin(self, plugin_id: str) -> None:
        """注销插件

        Args:
            plugin_id: 插件ID
        """
        self._plugins.pop(plugin_id, None)

    def search(self, query: str) -> List[SearchResult]:
        """执行全局搜索

        每个插件在独立线程中执行，超时或报错不影响其他插件。
        结果按相关度排序，上限 MAX_RESULTS 条。

        Args:
            query: 搜索关键词

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        if not query or not query.strip():
            return []

        query_lower = query.lower().strip()

        # 命中缓存则直接返回
        cached = self._cache.get(query_lower)
        if cached is not None:
            return cached

        results = self._search_all_plugins(query_lower)

        # 写入缓存后返回
        self._cache.put(query_lower, results)
        return results

    def _search_all_plugins(self, query_lower: str) -> List[SearchResult]:
        """并发搜索所有已注册插件，带超时控制"""
        if not self._plugins:
            return []

        futures = {}
        for plugin_id, plugin in self._plugins.items():
            future = self._executor.submit(self._safe_search, plugin, query_lower)
            futures[future] = plugin_id

        results: List[SearchResult] = []
        for future, plugin_id in futures.items():
            try:
                plugin_results = future.result(timeout=self.PLUGIN_TIMEOUT)
                if plugin_results:
                    results.extend(plugin_results)
            except TimeoutError:
                print(f"[GlobalSearch] 插件 {plugin_id} 搜索超时（{self.PLUGIN_TIMEOUT}s）")
            except Exception as e:
                print(f"[GlobalSearch] 插件 {plugin_id} 搜索异常: {e}")

        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:self.MAX_RESULTS]

    def _safe_search(self, plugin, query: str) -> list:
        """安全调用插件搜索方法，确保异常不扩散"""
        try:
            return plugin.search(query) or []
        except Exception as e:
            print(f"[GlobalSearch] 插件 {plugin.get_id()} search() 异常: {e}")
            return []

    def clear_cache(self) -> None:
        """清空搜索缓存"""
        self._cache.clear()

    def shutdown(self) -> None:
        """释放搜索线程池资源"""
        self._executor.shutdown(wait=False)