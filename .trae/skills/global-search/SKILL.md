---
name: "global-search"
description: "全局搜索功能实现指南。当用户需要在插件中实现搜索功能、集成全局搜索或了解搜索架构时调用。"
---

# SKILL.md - 全局搜索实现指南

## 1. 概述

全局搜索是 FluTool 的核心功能之一，允许用户通过统一的搜索对话框快速查找和访问各插件的数据。采用 **注册-发现** 模式，各插件实现搜索接口，由 GlobalSearchManager 统一调度。

当前插件系统采用扫描、加载、界面创建三级懒加载。全局搜索只依赖已加载插件对象，不应触发插件 widget 创建。

## 2. 架构

```
┌─────────────────────────────────────────────────────────┐
│              GlobalSearchDialog (UI层)                   │
│         搜索输入 → 结果展示 → 用户交互                    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│            GlobalSearchManager (核心层)                  │
│      注册插件 → 调度搜索 → 聚合结果 → 排序返回            │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Bookmark   │ │  Command    │ │   其他插件   │
    │  Plugin     │ │  Plugin     │ │  (实现搜索)  │
    └─────────────┘ └─────────────┘ └─────────────┘
```

## 3. 核心组件

### 3.1 SearchResult 数据结构

```python
# core/search.py
from dataclasses import dataclass
from typing import Callable, Dict, Any
from qfluentwidgets import FluentIcon

@dataclass
class SearchResult:
    """搜索结果数据结构"""
    plugin_id: str           # 插件ID
    plugin_name: str         # 插件显示名称
    title: str               # 结果标题
    description: str         # 结果描述
    icon: FluentIcon         # 图标
    relevance: float         # 相关性分数 (0.0-1.0)
    action: Callable         # 点击后的回调函数
    metadata: Dict[str, Any] # 额外元数据
```

### 3.2 GlobalSearchManager

```python
# core/search.py
class GlobalSearchManager:
    """全局搜索管理器"""
    
    def register_plugin(self, plugin) -> None:
        """注册支持搜索的插件"""
        
    def unregister_plugin(self, plugin_id: str) -> None:
        """注销插件"""
        
    def search(self, query: str) -> List[SearchResult]:
        """执行全局搜索，返回聚合排序后的结果"""
```

### 3.3 插件搜索接口

```python
# core/plugin_interface.py
class PluginInterface:
    def supports_search(self) -> bool:
        """是否支持全局搜索，默认返回 False"""
        return False
    
    def search(self, query: str) -> List[SearchResult]:
        """执行搜索，返回结果列表"""
        return []
```

## 4. 插件集成全局搜索

### 4.1 实现步骤

```python
# plugins/my_plugin/__init__.py
from core import SearchResult
from qfluentwidgets import FluentIcon as FIF

class Plugin(PluginInterface):
    PLUGIN_ID = "my_plugin"
    PLUGIN_NAME = "我的插件"
    PLUGIN_ICON = FIF.APPLICATION
    
    def supports_search(self) -> bool:
        """启用全局搜索支持"""
        return True
    
    def search(self, query: str) -> list:
        """实现搜索逻辑"""
        if not query or not query.strip():
            return []

        results = []
        query_lower = query.lower()
        
        # 从数据库或内存中搜索
        items = self._search_items(query_lower)
        
        for item in items[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=item['name'],
                description=item.get('description', ''),
                icon=self.PLUGIN_ICON,
                relevance=self._calculate_relevance(query_lower, item),
                action=lambda data=item: self._on_result_clicked(data),
                metadata={'item_id': item['id']}
            )
            results.append(result)
        
        return results
    
    def _search_items(self, query: str) -> list:
        """搜索数据项"""
        # 实现具体的搜索逻辑
        pass
    
    def _calculate_relevance(self, query: str, item: dict) -> float:
        """计算相关性分数"""
        if query in item['name'].lower():
            return 1.0
        elif query in item.get('description', '').lower():
            return 0.7
        return 0.5
    
    def _on_result_clicked(self, item: dict):
        """搜索结果点击回调"""
        # 打开详情、跳转页面等操作
        pass
```

### 4.2 完整示例 - 书签插件

```python
# plugins/bookmark/__init__.py
from core import SearchResult
from storage.database import DatabaseManager
import webbrowser

class Plugin(PluginInterface):
    PLUGIN_ID = "bookmark"
    PLUGIN_NAME = "书签管理"
    PLUGIN_ICON = FIF.BOOKMARK
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        if not query or not query.strip():
            return []

        db = DatabaseManager()
        results = []
        bookmarks = db.search_bookmarks(self.PLUGIN_ID, query)
        
        for bm in bookmarks[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=bm['name'],
                description=f"{bm['url']} - {bm.get('notes', '')}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in bm['name'].lower() else 0.5,
                action=lambda url=bm['url']: webbrowser.open(url),
                metadata={'bookmark_id': bm['id'], 'url': bm['url']}
            )
            results.append(result)
        
        return results
```

## 5. 搜索结果处理

### 5.1 相关性计算建议

```python
def _calculate_relevance(self, query: str, item: dict) -> float:
    """计算搜索结果相关性"""
    name = item['name'].lower()
    desc = item.get('description', '').lower()
    
    if name == query:
        return 1.0           # 完全匹配
    elif name.startswith(query):
        return 0.9           # 前缀匹配
    elif query in name:
        return 0.8           # 包含匹配
    elif query in desc:
        return 0.6           # 描述中匹配
    else:
        return 0.4           # 模糊匹配
```

### 5.2 Action 回调设计

```python
# 打开URL
action=lambda url=item['url']: webbrowser.open(url)

# 跳转到插件页面并选中
action=lambda id=item['id']: self._navigate_to_item(id)

# 复制到剪贴板
action=lambda text=item['content']: self._copy_to_clipboard(text)

# 执行命令
action=lambda cmd=item['command']: subprocess.run(cmd, shell=True)
```

## 6. UI 触发方式

### 6.1 快捷键触发

```python
# ui/main_window.py
from PyQt5.QtCore import Qt

def keyPressEvent(self, event):
    if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_K:
        self._show_global_search()
    super().keyPressEvent(event)
```

### 6.2 搜索对话框

```python
# ui/global_search_dialog.py
from qfluentwidgets import MessageBoxBase, LineEdit, ListWidget

class GlobalSearchDialog(MessageBoxBase):
    """全局搜索对话框"""
    
    result_selected = pyqtSignal(object)
    
    def __init__(self, search_manager, parent=None):
        self.search_manager = search_manager
        super().__init__(parent)
        self._setup_ui()
    
    def _on_search(self, text: str):
        results = self.search_manager.search(text)
        self._display_results(results)
    
    def _on_result_clicked(self, item: QListWidgetItem):
        result = item.data(Qt.UserRole)
        if result:
            result.action()  # 执行回调
            self.close()
```

## 7. 最佳实践

### 7.1 性能优化

```python
def search(self, query: str) -> list:
    # 限制结果数量
    MAX_RESULTS = 20
    
    # 使用数据库索引搜索
    items = db.search_with_index(query, limit=MAX_RESULTS)
    
    # 避免在搜索中执行耗时操作
    # 不要网络请求、文件IO等
    
    return results[:MAX_RESULTS]
```

复杂插件推荐把搜索逻辑放在 service/repository 中：

```python
def search(self, query: str) -> list:
    if not query or not query.strip():
        return []
    return self.service.search(query.strip(), limit=20)
```

搜索方法中不要调用 `get_widget()`、不要访问 `self._widget`、不要触发 UI 初始化。

### 7.2 错误处理

```python
def search(self, query: str) -> list:
    try:
        results = self._do_search(query)
    except Exception as e:
        self.core.logger.error(f"搜索失败: {e}")
        return []
    return results
```

### 7.3 空查询处理

```python
def search(self, query: str) -> list:
    if not query or not query.strip():
        return []
    # 继续搜索...
```

## 8. 数据库搜索支持

```python
# storage/database.py
class DatabaseManager:
    def search_bookmarks(self, plugin_id: str, query: str) -> list:
        cursor = self.conn.execute(
            """
            SELECT * FROM bookmarks 
            WHERE plugin_id = ? 
            AND (name LIKE ? OR url LIKE ? OR notes LIKE ?)
            ORDER BY 
                CASE WHEN name LIKE ? THEN 0 ELSE 1 END,
                created_at DESC
            LIMIT 20
            """,
            (plugin_id, f'%{query}%', f'%{query}%', f'%{query}%', f'{query}%')
        )
        return [dict(row) for row in cursor.fetchall()]
```

## 9. 注意事项

1. **必须返回 SearchResult**: 搜索方法返回的必须是 `SearchResult` 实例列表
2. **action 必须可调用**: `action` 字段必须是可调用的函数或 lambda
3. **限制结果数量**: 单个插件最多返回 20 条结果，避免性能问题
4. **相关性排序**: 合理设置 `relevance` 值，帮助用户快速找到目标
5. **异常捕获**: 搜索方法内部应捕获异常，避免影响其他插件搜索
6. **懒加载**: 搜索时不要触发界面创建，保持轻量
7. **业务分层**: 搜索逻辑优先走 service/repository，避免 Widget 承担数据查询
8. **打包安全**: 搜索实现不要依赖插件目录源码文件；打包后插件模块在 PYZ 中

## 10. 相关文件

| 文件 | 说明 |
|------|------|
| `core/search.py` | GlobalSearchManager 和 SearchResult 定义 |
| `core/plugin_interface.py` | 插件搜索接口定义 |
| `ui/global_search_dialog.py` | 搜索对话框 UI |
| `ui/plugin_host.py` | 插件 UI 懒加载宿主，搜索不应触发它创建 widget |
| `plugins/bookmark/__init__.py` | 书签插件搜索实现示例 |
| `plugins/command/__init__.py` | 命令插件搜索实现示例 |
