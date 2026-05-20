"""Repository 注册表。"""

from storage.repositories import (
    AIRepository,
    AppRepository,
    BookmarkRepository,
    CategoryRepository,
    ClipboardRepository,
    ColorRepository,
    CommandRepository,
    FolderTreeRepository,
    NotebookRepository,
    PasswordRepository,
    QuickCopyRepository,
    ScriptRepository,
    TodoRepository,
    VocabularyRepository,
    LearningCardRepository,
)


class RepositoryRegistry:
    """集中创建和持有所有 Repository 实例。"""

    def __init__(self, db_manager):
        self.categories = CategoryRepository(db_manager)
        self.bookmarks = BookmarkRepository(db_manager)
        self.commands = CommandRepository(db_manager)
        self.passwords = PasswordRepository(db_manager)
        self.apps = AppRepository(db_manager)
        self.colors = ColorRepository(db_manager)
        self.scripts = ScriptRepository(db_manager)
        self.clipboard = ClipboardRepository(db_manager)
        self.folder_tree = FolderTreeRepository(db_manager)
        self.quick_copy = QuickCopyRepository(db_manager)
        self.todos = TodoRepository(db_manager)
        self.ai = AIRepository(db_manager)
        self.notebooks = NotebookRepository(db_manager)
        self.vocab_words = VocabularyRepository(db_manager)
        self.learning_cards = LearningCardRepository(db_manager)

    def as_dict(self) -> dict:
        """返回兼容 DatabaseManager 旧属性名的仓储映射。"""
        return {
            "categories": self.categories,
            "bookmarks": self.bookmarks,
            "commands": self.commands,
            "passwords": self.passwords,
            "apps": self.apps,
            "colors": self.colors,
            "scripts": self.scripts,
            "clipboard": self.clipboard,
            "folder_tree": self.folder_tree,
            "quick_copy": self.quick_copy,
            "todos": self.todos,
            "ai": self.ai,
            "notebooks": self.notebooks,
            "vocab_words": self.vocab_words,
            "learning_cards": self.learning_cards,
        }

