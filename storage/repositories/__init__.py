"""
存储层 Repository 模块

提供各种数据表的仓储类，封装数据库访问逻辑。
"""

from .base import BaseRepository, TableConfig
from .bookmark_repository import BookmarkRepository
from .command_repository import CommandRepository
from .password_repository import PasswordRepository
from .app_repository import AppRepository
from .color_repository import ColorRepository
from .script_repository import ScriptRepository
from .clipboard_repository import ClipboardRepository
from .folder_tree_repository import FolderTreeRepository
from .quick_copy_repository import QuickCopyRepository
from .todo_repository import TodoRepository
from .ai_repository import AIRepository
from .category_repository import CategoryRepository
from .notebook_repository import NotebookRepository
from .vocabulary_repository import VocabularyRepository

__all__ = [
    'BaseRepository',
    'TableConfig',
    'BookmarkRepository',
    'CommandRepository',
    'PasswordRepository',
    'AppRepository',
    'ColorRepository',
    'ScriptRepository',
    'ClipboardRepository',
    'FolderTreeRepository',
    'QuickCopyRepository',
    'TodoRepository',
    'AIRepository',
    'CategoryRepository',
    'NotebookRepository',
    'VocabularyRepository',
]
