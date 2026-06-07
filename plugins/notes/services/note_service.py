"""
笔记服务模块
提供笔记的核心业务逻辑
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from ..dao.note_dao import NoteDAO
from ..models.note import Note, CodeBlock
from ..services.image_service import ImageService
from ..core.event_bus import EventBus


class NoteService:
    """
    笔记服务类
    
    提供笔记的核心业务逻辑，不依赖 Qt 信号
    
    属性:
        _note_dao: 笔记数据访问对象
        _image_service: 图片服务
        _event_bus: 事件总线
    """
    
    def __init__(
        self,
        note_dao: Optional[NoteDAO] = None,
        image_service: Optional[ImageService] = None,
        event_bus: Optional[EventBus] = None
    ):
        self._note_dao = note_dao or NoteDAO()
        self._image_service = image_service or ImageService.create_default()
        self._event_bus = event_bus or EventBus.get_instance()
    
    def get_all(self, include_archived: bool = False) -> List[Note]:
        """获取所有笔记"""
        return self._note_dao.get_all(include_archived=include_archived)
    
    def get_by_id(self, note_id: int) -> Optional[Note]:
        """根据 ID 获取笔记"""
        return self._note_dao.get_by_id(note_id)
    
    def get_by_category(self, category_id: int, include_archived: bool = False) -> List[Note]:
        """根据分类获取笔记"""
        return self._note_dao.get_by_category(category_id, include_archived)
    
    def get_favorites(self) -> List[Note]:
        """获取收藏的笔记"""
        return self._note_dao.get_favorites()
    
    def get_archived(self) -> List[Note]:
        """获取归档的笔记"""
        return self._note_dao.get_archived()
    
    def search(self, keyword: str) -> List[Note]:
        """搜索笔记"""
        if not keyword.strip():
            return []
        return self._note_dao.search(keyword)
    
    def create(self, title: str = '', content: str = '', category_id: Optional[int] = None) -> Optional[int]:
        """
        创建新笔记
        
        参数:
            title: 标题
            content: 内容
            category_id: 分类 ID
            
        返回:
            创建的笔记 ID，失败返回 None
        """
        if not title.strip():
            title = '无标题'
        
        note = Note(
            title=title,
            content=content,
            category_id=category_id
        )
        
        note_id = self._note_dao.add(note)
        if note_id:
            self._event_bus.emit_note_created(note_id)
        return note_id

    def add_note(
        self,
        title: str,
        content: str,
        category_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        code_blocks: Optional[List[dict]] = None,
        remarks: str = '',
        images: Optional[List[str]] = None,
    ) -> Optional[int]:
        """兼容旧调用方式，创建完整笔记。"""
        if not content or not content.strip():
            return None

        normalized_title = title.strip() if title and title.strip() else '无标题'
        note = Note(
            title=normalized_title,
            content=content,
            category_id=category_id,
            tags=tags or [],
            code_blocks=[],
            remarks=remarks,
            images=images or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        if code_blocks:
            note.code_blocks = [CodeBlock.from_dict(item) for item in code_blocks]

        note_id = self._note_dao.add(note)
        if note_id:
            self._event_bus.emit_note_created(note_id)
        return note_id
    
    def update(self, note: Note) -> bool:
        """
        更新笔记
        
        参数:
            note: 要更新的笔记对象
            
        返回:
            更新成功返回 True
        """
        if not note.content.strip():
            return False
        if not note.title.strip():
            note.title = '无标题'
        note.updated_at = datetime.now()
        
        result = self._note_dao.update(note)
        if result:
            self._event_bus.emit_note_updated(note.id)
        return result

    def update_note(self, note: Note) -> bool:
        """兼容旧调用方式，更新笔记。"""
        return self.update(note)
    
    def delete(self, note_id: int) -> bool:
        """
        删除笔记（同时删除关联的图片）
        
        参数:
            note_id: 笔记 ID
            
        返回:
            删除成功返回 True
        """
        note = self._note_dao.get_by_id(note_id)
        if note:
            for image_filename in note.images:
                self._image_service.delete(image_filename)
        
        result = self._note_dao.delete(note_id)
        if result:
            self._event_bus.emit_note_deleted(note_id)
        return result

    def delete_note(self, note_id: int) -> bool:
        """兼容旧调用方式，删除笔记。"""
        return self.delete(note_id)
    
    def toggle_favorite(self, note_id: int) -> bool:
        """切换收藏状态"""
        result = self._note_dao.toggle_favorite(note_id)
        if result:
            self._event_bus.emit_note_favorited(note_id)
        return result
    
    def toggle_archive(self, note_id: int) -> bool:
        """切换归档状态"""
        result = self._note_dao.toggle_archive(note_id)
        if result:
            self._event_bus.emit_note_archived(note_id)
        return result
    
    def set_category(self, note_id: int, category_id: Optional[int]) -> bool:
        """设置分类"""
        result = self._note_dao.set_category(note_id, category_id)
        if result:
            self._event_bus.emit_note_updated(note_id)
        return result
    
    def add_image(self, note_id: int, image_filename: str) -> bool:
        """为笔记添加图片"""
        note = self._note_dao.get_by_id(note_id)
        if note is None:
            return False
        if image_filename not in note.images:
            note.images.append(image_filename)
            return self.update(note)
        return True
    
    def remove_image(self, note_id: int, image_filename: str) -> bool:
        """从笔记移除图片"""
        note = self._note_dao.get_by_id(note_id)
        if note is None:
            return False
        if image_filename in note.images:
            note.images.remove(image_filename)
            self._image_service.delete(image_filename)
            return self.update(note)
        return True

    def save_image(
        self,
        image_data: Union[bytes, 'QPixmap'],
        category_name: str = '',
        filename: str = None,
        index: int = 0,
    ) -> Optional[str]:
        """保存图片资源。"""
        return self._image_service.save(
            image_data=image_data,
            filename=filename,
            category_name=category_name,
            index=index,
        )

    def get_image_path(self, filename: str) -> Optional[Path]:
        """获取图片文件路径。"""
        return self._image_service.get_path(filename)
    
    def count(self) -> int:
        """获取笔记总数"""
        return len(self._note_dao.get_all(include_archived=True))
    
    def count_by_category(self, category_id: int) -> int:
        """获取指定分类的笔记数"""
        return self._note_dao.count_by_category(category_id)
