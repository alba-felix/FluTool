"""
笔记管理器模块（兼容门面）
已降级为 NoteService + CategoryService 的兼容门面，保持旧调用方不受影响。
新代码请直接使用 services/ 下的服务类。
"""
from datetime import datetime
from typing import List, Optional, Callable

from ..dao.note_dao import NoteDAO
from ..dao.category_dao import CategoryDAO
from ..models.note import Note
from ..services.note_service import NoteService
from ..services.category_service import CategoryService
from ..services.image_service import ImageService
from .event_bus import EventBus


class NoteManager:
    """
    笔记管理器（兼容门面）
    
    内部委托给 NoteService/CategoryService，保留旧的回调通知机制以保证向后兼容。
    新代码请直接使用 NoteService / CategoryService。
    """
    
    _instance: Optional['NoteManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._note_dao = NoteDAO()
        self._category_dao = CategoryDAO()
        self._note_service = NoteService()
        self._category_service = CategoryService()
        self._image_service = ImageService.create_default()
        self._event_bus = EventBus.get_instance()
        self._on_note_changed_callbacks: List[Callable] = []

    def register_callback(self, callback: Callable):
        """注册笔记变更回调函数（向后兼容）"""
        self._on_note_changed_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """注销笔记变更回调函数"""
        if callback in self._on_note_changed_callbacks:
            self._on_note_changed_callbacks.remove(callback)

    def _notify_changed(self):
        """通知所有注册的回调函数笔记已变更"""
        for callback in self._on_note_changed_callbacks:
            callback()
    
    def _emit_note_event(self, note_id: int, event_type: str = 'updated'):
        """发送笔记事件到 EventBus"""
        if event_type == 'created':
            self._event_bus.emit_note_created(note_id)
        elif event_type == 'deleted':
            self._event_bus.emit_note_deleted(note_id)
        elif event_type == 'favorited':
            self._event_bus.emit_note_favorited(note_id)
        elif event_type == 'archived':
            self._event_bus.emit_note_archived(note_id)
        else:
            self._event_bus.emit_note_updated(note_id)

    def get_all(self, include_archived: bool = False) -> List[Note]:
        """获取所有笔记"""
        return self._note_service.get_all(include_archived)

    def get_by_id(self, note_id: int) -> Optional[Note]:
        """根据 ID 获取笔记"""
        return self._note_service.get_by_id(note_id)

    def get_by_category(self, category_id: int, include_archived: bool = False) -> List[Note]:
        """根据分类 ID 获取笔记列表"""
        return self._note_service.get_by_category(category_id, include_archived)

    def get_favorites(self) -> List[Note]:
        """获取所有收藏的笔记"""
        return self._note_service.get_favorites()

    def get_archived(self) -> List[Note]:
        """获取所有归档的笔记"""
        return self._note_service.get_archived()

    def search(self, keyword: str) -> List[Note]:
        """搜索笔记（按关键词）"""
        return self._note_service.search(keyword)

    def add_note(
        self,
        title: str,
        content: str,
        category_id: Optional[int] = None,
        tags: List[str] = None,
        code_blocks: List[dict] = None,
        remarks: str = '',
        images: List[str] = None
    ) -> Optional[int]:
        """
        添加新笔记
        
        参数同 NoteService.add_note()，额外保持旧回调通知。
        """
        # 注入默认分类逻辑（保持旧行为兼容）
        resolved_category_id = category_id
        if resolved_category_id is None:
            default_category = self._category_service.get_default()
            resolved_category_id = default_category.id if default_category else None

        note_id = self._note_service.add_note(
            title=title,
            content=content,
            category_id=resolved_category_id,
            tags=tags,
            code_blocks=code_blocks,
            remarks=remarks,
            images=images,
        )
        if note_id:
            self._notify_changed()
        return note_id

    def update_note(self, note: Note) -> bool:
        """更新笔记"""
        result = self._note_service.update_note(note)
        if result:
            self._notify_changed()
        return result

    def delete_note(self, note_id: int) -> bool:
        """删除笔记（同时删除关联的图片文件）"""
        result = self._note_service.delete_note(note_id)
        if result:
            self._notify_changed()
        return result

    def toggle_favorite(self, note_id: int) -> bool:
        """切换笔记的收藏状态"""
        result = self._note_service.toggle_favorite(note_id)
        if result:
            self._notify_changed()
        return result

    def toggle_archive(self, note_id: int) -> bool:
        """切换笔记的归档状态"""
        result = self._note_service.toggle_archive(note_id)
        if result:
            self._notify_changed()
        return result

    def set_category(self, note_id: int, category_id: Optional[int]) -> bool:
        """设置笔记的分类"""
        result = self._note_service.set_category(note_id, category_id)
        if result:
            self._notify_changed()
        return result

    def save_image(self, image_data, category_name: str = '', filename: str = None, index: int = 0) -> Optional[str]:
        """保存图片到本地"""
        return self._note_service.save_image(
            image_data=image_data,
            category_name=category_name,
            filename=filename,
            index=index,
        )

    def get_image_path(self, filename: str):
        """获取图片的完整路径"""
        return self._note_service.get_image_path(filename)

    def add_image_to_note(self, note_id: int, image_filename: str) -> bool:
        """为笔记添加图片"""
        result = self._note_service.add_image(note_id, image_filename)
        if result:
            self._notify_changed()
        return result

    def remove_image_from_note(self, note_id: int, image_filename: str) -> bool:
        """从笔记中移除图片（同时删除图片文件）"""
        result = self._note_service.remove_image(note_id, image_filename)
        if result:
            self._notify_changed()
        return result

    @classmethod
    def get_instance(cls) -> 'NoteManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance