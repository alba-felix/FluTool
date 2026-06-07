"""notes 子系统运行时上下文。"""

from typing import Optional

from ..dao.database import Database
from ..services.category_service import CategoryService
from ..services.image_service import ImageService
from ..services.note_service import NoteService
from .event_bus import EventBus
from .theme_manager import ThemeManager


class NotesRuntime:
    """集中持有 notes 子系统的核心依赖。"""

    def __init__(
        self,
        database: Database,
        event_bus: EventBus,
        image_service: ImageService,
        note_service: NoteService,
        category_service: CategoryService,
        theme_manager: ThemeManager,
    ):
        self.database = database
        self.event_bus = event_bus
        self.image_service = image_service
        self.note_service = note_service
        self.category_service = category_service
        self.theme_manager = theme_manager

    @classmethod
    def create_default(cls) -> "NotesRuntime":
        """创建默认运行时上下文。"""
        database = Database.get_instance()
        event_bus = EventBus.get_instance()
        image_service = ImageService.create_default()
        note_service = NoteService(image_service=image_service, event_bus=event_bus)
        category_service = CategoryService(event_bus=event_bus)
        theme_manager = ThemeManager.get_instance()
        return cls(
            database=database,
            event_bus=event_bus,
            image_service=image_service,
            note_service=note_service,
            category_service=category_service,
            theme_manager=theme_manager,
        )


_notes_runtime: Optional[NotesRuntime] = None


def set_notes_runtime(runtime: NotesRuntime) -> None:
    """设置全局 notes 运行时上下文。"""
    global _notes_runtime
    _notes_runtime = runtime


def get_notes_runtime() -> NotesRuntime:
    """获取全局 notes 运行时上下文。"""
    global _notes_runtime
    if _notes_runtime is None:
        _notes_runtime = NotesRuntime.create_default()
    return _notes_runtime
