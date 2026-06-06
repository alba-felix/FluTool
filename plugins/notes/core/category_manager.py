"""
分类管理器模块
提供分类的增删改查功能
采用单例模式确保全局只有一个实例
"""
from typing import List, Optional, Callable

from ..dao.category_dao import CategoryDAO
from ..dao.note_dao import NoteDAO
from ..models.note import Category
from .event_bus import EventBus


class CategoryManager:
    """
    分类管理器类（单例模式）
    
    负责管理分类的增删改查操作
    
    属性:
        _instance: 类属性，保存单例实例
        _initialized: 是否已初始化
        _category_dao: 分类数据访问对象
        _note_dao: 笔记数据访问对象
        _categories: 分类缓存列表
        _event_bus: 事件总线
        _on_category_changed_callbacks: 分类变更回调函数列表（向后兼容）
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
        self._categories: List[Category] = []
        self._event_bus = EventBus.get_instance()
        self._on_category_changed_callbacks: List[Callable] = []
        self._load_categories()

    def _load_categories(self):
        self._categories = self._category_dao.get_all()

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
        return self._categories.copy()

    def get_user_categories(self) -> List[Category]:
        return [c for c in self._categories if c.name != '默认']

    def get_by_id(self, category_id: int) -> Optional[Category]:
        if category_id is None or category_id <= 0:
            return None
        for category in self._categories:
            if category.id == category_id:
                return category
        return None

    def get_by_name(self, name: str) -> Optional[Category]:
        for category in self._categories:
            if category.name == name:
                return category
        return None

    def get_default(self) -> Optional[Category]:
        return self.get_by_name('默认')

    def add(self, name: str) -> Optional[int]:
        if self._category_dao.exists(name):
            return None
        category_id = self._category_dao.add(name)
        if category_id:
            self._load_categories()
            self._emit_category_event(category_id, 'created')
            self._notify_changed()
        return category_id

    def rename(self, category_id: int, new_name: str) -> bool:
        category = self.get_by_id(category_id)
        if category is None or category.name == '默认':
            return False
        if self._category_dao.exists(new_name):
            return False
        result = self._category_dao.update(category_id, new_name)
        if result:
            self._load_categories()
            self._emit_category_event(category_id, 'updated')
            self._notify_changed()
        return result

    def delete(self, category_id: int) -> bool:
        category = self.get_by_id(category_id)
        if category is None or category.name == '默认':
            return False
        default_category = self.get_default()
        if default_category:
            notes = self._note_dao.get_by_category(category_id, include_archived=True)
            for note in notes:
                self._note_dao.set_category(note.id, default_category.id)
        result = self._category_dao.delete(category_id)
        if result:
            self._load_categories()
            self._emit_category_event(category_id, 'deleted')
            self._notify_changed()
        return result

    def get_note_count(self, category_id: int) -> int:
        return self._note_dao.count_by_category(category_id)

    def refresh(self):
        self._load_categories()
        self._emit_category_event(0, 'changed')
        self._notify_changed()

    @classmethod
    def get_instance(cls) -> 'CategoryManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance