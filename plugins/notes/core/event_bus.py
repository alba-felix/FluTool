"""
Notes 插件领域事件总线

继承内核 EventBus 的线程安全 handler 管理，
同时定义 notes 领域专用的 pyqtSignal 和 EventType，
实现领域信号与内核事件桥接。
"""
from enum import Enum, auto
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass

from PyQt5.QtCore import QObject, pyqtSignal

from core.event_bus import EventBus as CoreEventBus


class EventType(Enum):
    """事件类型枚举"""
    NOTE_CREATED = auto()
    NOTE_UPDATED = auto()
    NOTE_DELETED = auto()
    NOTE_FAVORITED = auto()
    NOTE_ARCHIVED = auto()

    CATEGORY_CREATED = auto()
    CATEGORY_UPDATED = auto()
    CATEGORY_DELETED = auto()
    CATEGORY_CHANGED = auto()

    THEME_CHANGED = auto()


@dataclass
class Event:
    """事件数据类"""
    type: EventType
    data: Any = None
    source: Optional[str] = None


class EventBus(QObject):
    """
    Notes 插件领域事件总线

    提供 notes 领域专用的 pyqtSignal（类型安全），
    同时桥接到内核 EventBus（跨模块通信）。

    使用示例:
        bus = EventBus.get_instance()

        # 订阅事件
        bus.note_created.connect(lambda note_id: print(f"Note {note_id} created"))

        # 发布事件（同时触发领域信号 + 内核桥接）
        bus.emit_note_created(123)
    """

    _instance: Optional['EventBus'] = None

    note_created = pyqtSignal(int)
    note_updated = pyqtSignal(int)
    note_deleted = pyqtSignal(int)
    note_favorited = pyqtSignal(int)
    note_archived = pyqtSignal(int)

    category_created = pyqtSignal(int)
    category_updated = pyqtSignal(int)
    category_deleted = pyqtSignal(int)
    category_changed = pyqtSignal()

    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._core_bus: Optional[CoreEventBus] = None

    def _get_core_bus(self) -> Optional[CoreEventBus]:
        """懒加载内核 EventBus（避免循环导入）"""
        if self._core_bus is None:
            try:
                from core.app_core import AppCore
                core = AppCore()
                self._core_bus = core.event_bus
            except Exception:
                pass
        return self._core_bus

    def _bridge_to_core(self, event_name: str, data: Any = None):
        """将领域事件桥接到内核 EventBus，实现跨模块通信"""
        core_bus = self._get_core_bus()
        if core_bus is not None:
            core_bus.emit(f"notes.{event_name}", data)

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        if cls._instance is not None:
            cls._instance = None

    def emit(self, event: Event) -> None:
        """
        发送事件

        参数:
            event: 事件对象
        """
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """
        订阅事件

        参数:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """
        取消订阅事件

        参数:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def clear_handlers(self, event_type: Optional[EventType] = None) -> None:
        """
        清除事件处理器

        参数:
            event_type: 指定事件类型，None 表示清除所有
        """
        if event_type is None:
            self._handlers.clear()
        elif event_type in self._handlers:
            self._handlers[event_type].clear()

    def emit_note_created(self, note_id: int) -> None:
        """发送笔记创建事件"""
        self.note_created.emit(note_id)
        self.emit(Event(EventType.NOTE_CREATED, note_id))
        self._bridge_to_core("note_created", note_id)

    def emit_note_updated(self, note_id: int) -> None:
        """发送笔记更新事件"""
        self.note_updated.emit(note_id)
        self.emit(Event(EventType.NOTE_UPDATED, note_id))
        self._bridge_to_core("note_updated", note_id)

    def emit_note_deleted(self, note_id: int) -> None:
        """发送笔记删除事件"""
        self.note_deleted.emit(note_id)
        self.emit(Event(EventType.NOTE_DELETED, note_id))
        self._bridge_to_core("note_deleted", note_id)

    def emit_note_favorited(self, note_id: int) -> None:
        """发送笔记收藏事件"""
        self.note_favorited.emit(note_id)
        self.emit(Event(EventType.NOTE_FAVORITED, note_id))
        self._bridge_to_core("note_favorited", note_id)

    def emit_note_archived(self, note_id: int) -> None:
        """发送笔记归档事件"""
        self.note_archived.emit(note_id)
        self.emit(Event(EventType.NOTE_ARCHIVED, note_id))
        self._bridge_to_core("note_archived", note_id)

    def emit_category_created(self, category_id: int) -> None:
        """发送分类创建事件"""
        self.category_created.emit(category_id)
        self.emit(Event(EventType.CATEGORY_CREATED, category_id))
        self._bridge_to_core("category_created", category_id)

    def emit_category_updated(self, category_id: int) -> None:
        """发送分类更新事件"""
        self.category_updated.emit(category_id)
        self.emit(Event(EventType.CATEGORY_UPDATED, category_id))
        self._bridge_to_core("category_updated", category_id)

    def emit_category_deleted(self, category_id: int) -> None:
        """发送分类删除事件"""
        self.category_deleted.emit(category_id)
        self.emit(Event(EventType.CATEGORY_DELETED, category_id))
        self._bridge_to_core("category_deleted", category_id)

    def emit_category_changed(self) -> None:
        """发送分类变更事件"""
        self.category_changed.emit()
        self.emit(Event(EventType.CATEGORY_CHANGED))
        self._bridge_to_core("category_changed")

    def emit_theme_changed(self, is_dark: bool) -> None:
        """发送主题变更事件"""
        self.theme_changed.emit(is_dark)
        self.emit(Event(EventType.THEME_CHANGED, is_dark))
        self._bridge_to_core("theme_changed", is_dark)
