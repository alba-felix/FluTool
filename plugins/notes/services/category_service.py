"""
分类服务模块
提供分类的核心业务逻辑
"""
from typing import List, Optional

from ..dao.category_dao import CategoryDAO
from ..dao.note_dao import NoteDAO
from ..models.note import Category
from ..core.event_bus import EventBus, EventType


class CategoryService:
    """
    分类服务类
    
    提供分类的核心业务逻辑，不依赖 Qt 信号
    
    属性:
        _category_dao: 分类数据访问对象
        _note_dao: 笔记数据访问对象
        _event_bus: 事件总线
    """
    
    def __init__(
        self,
        category_dao: Optional[CategoryDAO] = None,
        note_dao: Optional[NoteDAO] = None,
        event_bus: Optional[EventBus] = None
    ):
        self._category_dao = category_dao or CategoryDAO()
        self._note_dao = note_dao or NoteDAO()
        self._event_bus = event_bus or EventBus.get_instance()
    
    def get_all(self) -> List[Category]:
        """获取所有分类"""
        return self._category_dao.get_all()
    
    def get_by_id(self, category_id: int) -> Optional[Category]:
        """根据 ID 获取分类"""
        return self._category_dao.get_by_id(category_id)
    
    def get_by_name(self, name: str) -> Optional[Category]:
        """根据名称获取分类"""
        return self._category_dao.get_by_name(name)
    
    def get_default(self) -> Optional[Category]:
        """获取默认分类"""
        return self.get_by_name('默认')
    
    def get_user_categories(self) -> List[Category]:
        """获取用户创建的分类（排除默认分类）"""
        return [c for c in self._category_dao.get_all() if c.name != '默认']
    
    def create(self, name: str) -> Optional[int]:
        """
        创建新分类
        
        参数:
            name: 分类名称
            
        返回:
            创建的分类 ID，失败返回 None
        """
        if self._category_dao.exists(name):
            return None
        category_id = self._category_dao.add(name)
        if category_id:
            self._event_bus.emit_category_created(category_id)
        return category_id
    
    def rename(self, category_id: int, new_name: str) -> bool:
        """
        重命名分类
        
        参数:
            category_id: 分类 ID
            new_name: 新名称
            
        返回:
            重命名成功返回 True
        """
        category = self._category_dao.get_by_id(category_id)
        if category is None or category.name == '默认':
            return False
        if self._category_dao.exists(new_name):
            return False
        result = self._category_dao.update(category_id, new_name)
        if result:
            self._event_bus.emit_category_updated(category_id)
        return result
    
    def delete(self, category_id: int) -> bool:
        """
        删除分类
        
        删除前会将该分类下的笔记移动到默认分类
        
        参数:
            category_id: 分类 ID
            
        返回:
            删除成功返回 True
        """
        category = self._category_dao.get_by_id(category_id)
        if category is None or category.name == '默认':
            return False
        
        default_category = self.get_default()
        if default_category:
            notes = self._note_dao.get_by_category(category_id, include_archived=True)
            for note in notes:
                self._note_dao.set_category(note.id, default_category.id)
        
        result = self._category_dao.delete(category_id)
        if result:
            self._event_bus.emit_category_deleted(category_id)
        return result
    
    def exists(self, name: str) -> bool:
        """检查分类是否存在"""
        return self._category_dao.exists(name)
    
    def get_note_count(self, category_id: int) -> int:
        """获取分类下的笔记数"""
        return self._note_dao.count_by_category(category_id)
    
    def count(self) -> int:
        """获取分类总数"""
        return len(self._category_dao.get_all())