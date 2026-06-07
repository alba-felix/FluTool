"""
分类管理器模块（兼容门面）
已降级为 CategoryService + NoteService 的兼容门面，保持旧调用方不受影响。
新代码请直接使用 services/ 下的服务类。
"""
from typing import List, Optional, Callable

from ..dao.category_dao import CategoryDAO
from ..dao.note_dao import NoteDAO
from ..models.note import Category
from ..services.category_service import CategoryService
from ..services.note_service import NoteService
from .event_bus import EventBus


class CategoryManager:
    """
    分类管理器（兼容门面）

    内部委托给 CategoryService/NoteService，保留旧的回调通知机制以保证向后兼容。
    新代码请直接使用 CategoryService。
    """
    
    _instance: Optional['CategoryManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._category_dao = CategoryDAO()
        self._note_dao = NoteDAO()
        self._category_service = CategoryService()
        self._note_service = NoteService()
        self._categories: List[Category] = []
        self._event_bus = EventBus.get_instance()
        self._on_category_changed_callbacks: List[Callable] = []
        self._load_categories()

    def _load_categories(self):
        """加载分类列表缓存"""
        self._categories = self._category_service.get_all()

    def register_callback(self, callback: Callable):
        """注册分类变更回调函数（向后兼容）"""
        self._on_category_changed_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """注销分类变更回调函数"""
        if callback in self._on_category_changed_callbacks:
            self._on_category_changed_callbacks.remove(callback)

    def _notify_changed(self):
        """通知所有注册的回调函数分类已变更"""
        for callback in self._on_category_changed_callbacks:
            callback()
    
    def _emit_category_event(self, category_id: int, event_type: str = 'changed'):
        """发送分类事件到 EventBus"""
        if event_type == 'created':
            self._event_bus.emit_category_created(category_id)
        elif event_type == 'deleted':
            self._event_bus.emit_category_deleted(category_id)
        elif event_type == 'updated':
            self._event_bus.emit_category_updated(category_id)
        self._event_bus.emit_category_changed()

    def get_all(self) -> List[Category]:
        """获取所有分类"""
        return self._categories.copy()

    def get_user_categories(self) -> List[Category]:
        """获取用户创建的分类（排除默认分类）"""
        return [c for c in self._categories if c.name != '默认']

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """根据 ID 获取分类"""
        if category_id is None or category_id <= 0:
            return None
        for category in self._categories:
            if category.id == category_id:
                return category
        return None

    def get_by_name(self, name: str) -> Optional[Category]:
        """根据名称获取分类"""
        for category in self._categories:
            if category.name == name:
                return category
        return None

    def get_default(self) -> Optional[Category]:
        """获取默认分类"""
        return self.get_by_name('默认')

    def add(self, name: str) -> Optional[int]:
        """新增分类"""
        category_id = self._category_service.add(name)
        if category_id:
            self._load_categories()
            self._notify_changed()
        return category_id

    def rename(self, category_id: int, new_name: str) -> bool:
        """重命名分类"""
        result = self._category_service.rename(category_id, new_name)
        if result:
            self._load_categories()
            self._notify_changed()
        return result

    def delete(self, category_id: int) -> bool:
        """删除分类（内部笔记移至默认分类）"""
        result = self._category_service.delete(category_id)
        if result:
            self._load_categories()
            self._notify_changed()
        return result

    def get_note_count(self, category_id: int) -> int:
        """获取分类下的笔记数"""
        return self._note_service.count_by_category(category_id)

    def refresh(self):
        """刷新分类缓存"""
        self._load_categories()
        self._emit_category_event(0, 'changed')
        self._notify_changed()

    @classmethod
    def get_instance(cls) -> 'CategoryManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance