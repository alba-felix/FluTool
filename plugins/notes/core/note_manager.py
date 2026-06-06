"""
笔记管理器模块
提供笔记的增删改查、收藏、归档等功能
采用单例模式确保全局只有一个实例
"""

from datetime import datetime
from typing import List, Optional, Callable

from ..dao.note_dao import NoteDAO
from ..dao.category_dao import CategoryDAO
from ..models.note import Note
from ..services.image_service import ImageService
from .event_bus import EventBus


class NoteManager:
    """
    笔记管理器类（单例模式）
    
    负责管理笔记的增删改查、收藏、归档等操作
    
    属性:
        _instance: 类属性，保存单例实例
        _initialized: 是否已初始化
        _note_dao: 笔记数据访问对象
        _category_dao: 分类数据访问对象
        _image_service: 图片服务
        _event_bus: 事件总线
        _on_note_changed_callbacks: 笔记变更回调函数列表（向后兼容）
    """
    
    _instance: Optional['NoteManager'] = None

    def __new__(cls):
        """单例模式：确保只有一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化笔记管理器"""
        if self._initialized:
            return
        self._initialized = True
        self._note_dao = NoteDAO()
        self._category_dao = CategoryDAO()
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
        return self._note_dao.get_all(include_archived)

    def get_by_id(self, note_id: int) -> Optional[Note]:
        """根据 ID 获取笔记"""
        return self._note_dao.get_by_id(note_id)

    def get_by_category(self, category_id: int, include_archived: bool = False) -> List[Note]:
        """根据分类 ID 获取笔记列表"""
        return self._note_dao.get_by_category(category_id, include_archived)

    def get_favorites(self) -> List[Note]:
        """获取所有收藏的笔记"""
        return self._note_dao.get_favorites()

    def get_archived(self) -> List[Note]:
        """获取所有归档的笔记"""
        return self._note_dao.get_archived()

    def search(self, keyword: str) -> List[Note]:
        """搜索笔记（按关键词）"""
        if not keyword or not keyword.strip():
            return []
        return self._note_dao.search(keyword)

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
        
        参数:
            title: 笔记标题
            content: 笔记内容
            category_id: 分类 ID（可选）
            tags: 标签列表
            code_blocks: 代码块列表
            remarks: 备注
            images: 图片文件名列表
            
        返回:
            新笔记的 ID，失败返回 None
        """
        if not content or not content.strip():
            return None
        if not title or not title.strip():
            title = '无标题'
        if category_id is None:
            default_category = self._category_dao.get_default_category()
            category_id = default_category.id if default_category else None

        note = Note(
            title=title,
            content=content,
            category_id=category_id,
            tags=tags or [],
            code_blocks=[],
            remarks=remarks,
            images=images or [],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        if code_blocks:
            from ..models.note import CodeBlock
            note.code_blocks = [CodeBlock.from_dict(cb) for cb in code_blocks]

        note_id = self._note_dao.add(note)
        if note_id:
            self._emit_note_event(note_id, 'created')
            self._notify_changed()
        return note_id

    def update_note(self, note: Note) -> bool:
        """
        更新笔记
        
        参数:
            note: 要更新的笔记对象
            
        返回:
            更新成功返回 True，失败返回 False
        """
        if not note.content or not note.content.strip():
            return False
        if not note.title or not note.title.strip():
            note.title = '无标题'
        note.updated_at = datetime.now()
        result = self._note_dao.update(note)
        if result:
            self._emit_note_event(note.id, 'updated')
            self._notify_changed()
        return result

    def delete_note(self, note_id: int) -> bool:
        """
        删除笔记（同时删除关联的图片文件）

        参数:
            note_id: 笔记 ID

        返回:
            删除成功返回 True，失败返回 False
        """
        if not note_id:
            return False
        note = self._note_dao.get_by_id(note_id)
        if note is None:
            return False
        for image_filename in note.images:
            self._delete_image_file(image_filename)
        result = self._note_dao.delete(note_id)
        if result:
            self._emit_note_event(note_id, 'deleted')
            self._notify_changed()
        return result

    def toggle_favorite(self, note_id: int) -> bool:
        """切换笔记的收藏状态"""
        result = self._note_dao.toggle_favorite(note_id)
        if result:
            self._emit_note_event(note_id, 'favorited')
            self._notify_changed()
        return result

    def toggle_archive(self, note_id: int) -> bool:
        """切换笔记的归档状态"""
        result = self._note_dao.toggle_archive(note_id)
        if result:
            self._emit_note_event(note_id, 'archived')
            self._notify_changed()
        return result

    def set_category(self, note_id: int, category_id: Optional[int]) -> bool:
        """设置笔记的分类"""
        result = self._note_dao.set_category(note_id, category_id)
        if result:
            self._emit_note_event(note_id, 'updated')
            self._notify_changed()
        return result

    def save_image(self, image_data, category_name: str = '', filename: str = None, index: int = 0) -> Optional[str]:
        """
        保存图片到本地
        
        参数:
            image_data: 图片数据（bytes 或 QPixmap）
            category_name: 分类名称（用于文件名前缀）
            filename: 可选的文件名
            index: 序号
            
        返回:
            保存的文件名，失败返回 None
        """
        return self._image_service.save(
            image_data=image_data,
            filename=filename,
            category_name=category_name,
            index=index
        )

    def get_image_path(self, filename: str):
        """
        获取图片的完整路径
        
        参数:
            filename: 图片文件名
            
        返回:
            图片的完整路径，文件不存在返回 None
        """
        return self._image_service.get_path(filename)

    def _delete_image_file(self, filename: str):
        """删除图片文件（内部方法）"""
        self._image_service.delete(filename)

    def add_image_to_note(self, note_id: int, image_filename: str) -> bool:
        """
        为笔记添加图片
        
        参数:
            note_id: 笔记 ID
            image_filename: 图片文件名
            
        返回:
            添加成功返回 True，失败返回 False
        """
        note = self._note_dao.get_by_id(note_id)
        if note is None:
            return False
        if image_filename not in note.images:
            note.images.append(image_filename)
            return self.update_note(note)
        return True

    def remove_image_from_note(self, note_id: int, image_filename: str) -> bool:
        """
        从笔记中移除图片（同时删除图片文件）
        
        参数:
            note_id: 笔记 ID
            image_filename: 图片文件名
            
        返回:
            移除成功返回 True，失败返回 False
        """
        note = self._note_dao.get_by_id(note_id)
        if note is None:
            return False
        if image_filename in note.images:
            note.images.remove(image_filename)
            self._delete_image_file(image_filename)
            return self.update_note(note)
        return True

    @classmethod
    def get_instance(cls) -> 'NoteManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance