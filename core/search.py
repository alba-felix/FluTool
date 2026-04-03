"""全局搜索功能"""

from dataclasses import dataclass
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


class GlobalSearchManager:
    """全局搜索管理器"""
    
    def __init__(self):
        self._plugins = {}
    
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
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
    
    def search(self, query: str) -> List[SearchResult]:
        """执行全局搜索
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        if not query or not query.strip():
            return []
        
        results = []
        query_lower = query.lower().strip()
        
        for plugin_id, plugin in self._plugins.items():
            try:
                plugin_results = plugin.search(query_lower)
                results.extend(plugin_results)
            except Exception as e:
                print(f"[GlobalSearch] 搜索插件 {plugin_id} 失败: {e}")
        
        results.sort(key=lambda x: x.relevance, reverse=True)
        
        return results[:50]
