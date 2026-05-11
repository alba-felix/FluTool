from pathlib import Path
from typing import Optional, List, Dict, Any

from storage.connection import DatabaseConnection
from storage.migration import MigrationManager
from storage.schema import SchemaManager
from storage.import_service import ImportService
from storage.repository_registry import RepositoryRegistry


class DatabaseManager:
    """
    数据库管理器
    
    单例模式，管理 SQLite 数据库连接。
    作为 Repository 工厂，提供各种数据表的访问接口。
    """
    
    _instance: Optional['DatabaseManager'] = None
    _db_path: Optional[Path] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置数据库单例，主要用于测试隔离"""
        cls._instance = None
        cls._db_path = None
    
    def initialize(self, db_path: str) -> None:
        """初始化数据库"""
        if self._initialized:
            return
        self._initialized = True
        self._db_path = Path(db_path)
        self._connection = DatabaseConnection(self._db_path)
        self._repositories = None
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[DatabaseManager] Initializing database at: {self._db_path}")
        print(f"[DatabaseManager] Database exists: {self._db_path.exists()}")
        self._create_tables()
        print(f"[DatabaseManager] Tables created/verified")
        
        # 初始化所有 Repository
        self._init_repositories()
    
    def _init_repositories(self):
        """初始化所有 Repository 实例"""
        self._repositories = RepositoryRegistry(self)
        for name, repository in self._repositories.as_dict().items():
            setattr(self, name, repository)

    @property
    def db_path(self) -> Optional[Path]:
        """获取当前数据库路径"""
        return self._db_path

    @property
    def is_initialized(self) -> bool:
        """检查数据库是否已初始化"""
        return bool(getattr(self, "_initialized", False) and self._db_path is not None)
    
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        if self._db_path is None or not hasattr(self, "_connection"):
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._connection.get_connection()
    
    def _create_tables(self) -> None:
        """创建基础表结构"""
        with self.get_connection() as conn:
            SchemaManager().create_tables(conn)

    def _migrate_ai_tables(self, conn) -> None:
        """迁移 AI 表，处理旧结构问题"""
        MigrationManager().migrate_ai_tables(conn)
    
    def _run_migrations(self, conn) -> None:
        """运行数据库迁移，添加缺失的列"""
        MigrationManager().run_migrations(conn)
    
    def _create_indexes(self, conn) -> None:
        """创建索引"""
        SchemaManager().create_indexes(conn)
    
    # ============ 向后兼容的接口 ============
    # 为了不破坏现有代码，保留原有的方法签名，但委托给对应的 Repository
    
    # Category 方法
    def add_category(self, plugin_id: str, name: str, sort_order: int = 0) -> int:
        return self.categories.add_or_get(plugin_id, name, sort_order)
    
    def get_categories(self, plugin_id: str) -> list:
        return self.categories.get_by_plugin(plugin_id)
    
    def update_category(self, plugin_id: str, category_id: int, name: str = None, **kwargs) -> bool:
        if name is not None:
            kwargs['name'] = name
        return self.categories.update(category_id, **kwargs)

    def update_category_sort_orders(self, plugin_id: str, category_ids: list) -> bool:
        return self.categories.update_sort_orders(plugin_id, category_ids)
    
    def delete_category(self, plugin_id: str, category_id: int) -> bool:
        return self.categories.delete(category_id)
    
    # Bookmark 方法
    def add_bookmark(self, plugin_id: str, name: str, url: str, 
                     category_name: str = None, icon: str = None, 
                     notes: str = None, sort_order: int = 0) -> int:
        category_id = self._resolve_category_id(plugin_id, category_name)
        return self.bookmarks.add(
            plugin_id=plugin_id, category_id=category_id, 
            name=name, url=url, icon=icon, notes=notes, sort_order=sort_order
        )
    
    def get_bookmarks(self, plugin_id: str, category_id: int = None) -> list:
        return self.bookmarks.get_by_plugin(plugin_id, category_id)
    
    def update_bookmark(self, plugin_id: str, bookmark_id: int, **kwargs) -> bool:
        return self.bookmarks.update(bookmark_id, **kwargs)
    
    def delete_bookmark(self, plugin_id: str, bookmark_id: int) -> bool:
        return self.bookmarks.delete(bookmark_id)
    
    def search_bookmarks(self, plugin_id: str, keyword: str) -> list:
        return self.bookmarks.search(plugin_id, keyword)
    
    def bookmark_exists(self, plugin_id: str, url: str) -> bool:
        return self.bookmarks.exists(plugin_id, url)
    
    # Command 方法
    def add_command(self, plugin_id: str, name: str, content: str,
                    category_name: str = None, sub_title: str = '',
                    sort_order: int = 0) -> int:
        category_id = self._resolve_category_id(plugin_id, category_name)
        return self.commands.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, sub_title=sub_title, content=content, sort_order=sort_order
        )
    
    def get_commands(self, plugin_id: str, category_id: int = None) -> list:
        return self.commands.get_by_plugin(plugin_id, category_id)
    
    def update_command(self, plugin_id: str, command_id: int, **kwargs) -> bool:
        return self.commands.update(command_id, **kwargs)
    
    def delete_command(self, plugin_id: str, command_id: int) -> bool:
        return self.commands.delete(command_id)
    
    def search_commands(self, plugin_id: str, keyword: str) -> list:
        return self.commands.search(plugin_id, keyword)
    
    def command_exists(self, plugin_id: str, name: str, category_name: str = None) -> bool:
        return self.commands.exists(plugin_id, name, category_name)
    
    # Password 方法
    def add_password(self, plugin_id: str, username: str, password: str,
                     platform: str = '', category_name: str = None,
                     category_id: int = None,
                     email: str = '', notes: str = '', sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.passwords.add(
            plugin_id=plugin_id, category_id=category_id,
            platform=platform, username=username, password=password,
            email=email, notes=notes, sort_order=sort_order
        )
    
    def get_passwords(self, plugin_id: str, category_id: int = None) -> list:
        return self.passwords.get_by_plugin(plugin_id, category_id)
    
    def update_password(self, plugin_id: str, password_id: int, **kwargs) -> bool:
        return self.passwords.update(password_id, **kwargs)
    
    def delete_password(self, plugin_id: str, password_id: int) -> bool:
        return self.passwords.delete(password_id)
    
    def search_passwords(self, plugin_id: str, keyword: str) -> list:
        return self.passwords.search(plugin_id, keyword)
    
    def password_exists(self, plugin_id: str, username: str, password: str) -> bool:
        return self.passwords.exists(plugin_id, username, password)
    
    # App 方法
    def add_app(self, plugin_id: str, name: str, target_path: str,
                category_name: str = None, category_id: int = None,
                icon_path: str = '', arguments: str = '',
                notes: str = '', sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.apps.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, icon_path=icon_path, target_path=target_path,
            arguments=arguments, notes=notes, sort_order=sort_order
        )
    
    def get_apps(self, plugin_id: str, category_id: int = None) -> list:
        return self.apps.get_by_plugin(plugin_id, category_id)
    
    def update_app(self, plugin_id: str, app_id: int, **kwargs) -> bool:
        return self.apps.update(app_id, **kwargs)
    
    def delete_app(self, plugin_id: str, app_id: int) -> bool:
        return self.apps.delete(app_id)
    
    def search_apps(self, plugin_id: str, keyword: str) -> list:
        return self.apps.search(plugin_id, keyword)

    def batch_update_apps(self, plugin_id: str, app_ids: list, **kwargs) -> int:
        return self.apps.batch_update(plugin_id, app_ids, **kwargs)

    def batch_delete_apps(self, plugin_id: str, app_ids: list) -> int:
        return self.apps.batch_delete(plugin_id, app_ids)
    
    def app_exists(self, plugin_id: str, name: str, target_path: str) -> bool:
        return self.apps.exists(plugin_id, name, target_path)
    
    # Color 方法
    def add_color(self, plugin_id: str, name: str, color_hex: str, color_rgb: str,
                  category_name: str = None, category_id: int = None,
                  color_argb: str = '', notes: str = '', sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.colors.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, color_hex=color_hex, color_rgb=color_rgb,
            color_argb=color_argb, notes=notes, sort_order=sort_order
        )
    
    def get_colors(self, plugin_id: str, category_id: int = None) -> list:
        return self.colors.get_by_plugin(plugin_id, category_id)
    
    def update_color(self, plugin_id: str, color_id: int, **kwargs) -> bool:
        return self.colors.update(color_id, **kwargs)
    
    def delete_color(self, plugin_id: str, color_id: int) -> bool:
        return self.colors.delete(color_id)
    
    def search_colors(self, plugin_id: str, keyword: str) -> list:
        return self.colors.search(plugin_id, keyword)
    
    def color_exists(self, plugin_id: str, color_hex: str) -> bool:
        return self.colors.exists(plugin_id, color_hex)
    
    # Script 方法
    def add_script(self, plugin_id: str, name: str, content: str,
                   script_type: str = 'bat', category_name: str = None,
                   category_id: int = None, description: str = '',
                   sort_order: int = 0) -> int:
        if category_id is None and category_name:
            category_id = self._resolve_category_id(plugin_id, category_name)
        return self.scripts.add(
            plugin_id=plugin_id, category_id=category_id,
            name=name, script_type=script_type, content=content,
            description=description, sort_order=sort_order
        )
    
    def get_scripts(self, plugin_id: str, category_id: int = None) -> list:
        return self.scripts.get_by_plugin(plugin_id, category_id)
    
    def update_script(self, plugin_id: str, script_id: int, **kwargs) -> bool:
        return self.scripts.update(script_id, **kwargs)
    
    def delete_script(self, plugin_id: str, script_id: int) -> bool:
        return self.scripts.delete(script_id)
    
    def search_scripts(self, plugin_id: str, keyword: str) -> list:
        return self.scripts.search(plugin_id, keyword)
    
    def script_exists(self, plugin_id: str, name: str) -> bool:
        return self.scripts.exists(plugin_id, name)
    
    # Clipboard 方法
    def add_clipboard_item(self, item_type: str, content: str, format: str = '') -> int:
        return self.clipboard.add(item_type=item_type, content=content, format=format)
    
    def get_clipboard_history(self, limit: int = 100) -> list:
        return self.clipboard.get_history(limit)
    
    def clear_clipboard_history(self) -> bool:
        return self.clipboard.clear()
    
    def delete_clipboard_item(self, item_id: int) -> bool:
        return self.clipboard.delete(item_id)
    
    def search_clipboard(self, keyword: str, limit: int = 20) -> list:
        return self.clipboard.search(keyword, limit)
    
    # Folder Tree 方法
    def add_folder_tree_rule(self, rule_name: str, exclude_items: list) -> int:
        return self.folder_tree.add(rule_name=rule_name, exclude_items=exclude_items)
    
    def get_folder_tree_rule(self, rule_name: str) -> Optional[Dict[str, Any]]:
        return self.folder_tree.get_by_name(rule_name)
    
    def get_all_folder_tree_rules(self) -> list:
        return self.folder_tree.get_all()
    
    def update_folder_tree_rule(self, rule_name: str, exclude_items: list) -> bool:
        return self.folder_tree.update_by_name(rule_name, exclude_items=exclude_items)
    
    def delete_folder_tree_rule(self, rule_name: str) -> bool:
        return self.folder_tree.delete_by_name(rule_name)
    
    def folder_tree_rule_exists(self, rule_name: str) -> bool:
        return self.folder_tree.exists(rule_name)
    
    def search_folder_tree_rules(self, keyword: str) -> list:
        return self.folder_tree.search(keyword)
    
    # Quick Copy 方法
    def add_quick_copy_card(self, title: str, sort_order: int = 0) -> int:
        return self.quick_copy.add_card(title=title, sort_order=sort_order)
    
    def get_quick_copy_cards(self) -> list:
        return self.quick_copy.get_cards()

    def get_quick_copy_cards_with_items(self) -> list:
        return self.quick_copy.get_cards_with_items()
    
    def update_quick_copy_card(self, card_id: int, **kwargs) -> bool:
        return self.quick_copy.update_card(card_id, **kwargs)
    
    def delete_quick_copy_card(self, card_id: int) -> bool:
        return self.quick_copy.delete_card(card_id)
    
    def add_quick_copy_item(self, card_id: int, content: str, sort_order: int = 0) -> int:
        return self.quick_copy.add_item(card_id=card_id, content=content, sort_order=sort_order)
    
    def get_quick_copy_items(self, card_id: int) -> list:
        return self.quick_copy.get_items(card_id)
    
    def update_quick_copy_item(self, item_id: int, **kwargs) -> bool:
        return self.quick_copy.update_item(item_id, **kwargs)
    
    def delete_quick_copy_item(self, item_id: int) -> bool:
        return self.quick_copy.delete_item(item_id)
    
    def search_quick_copy(self, keyword: str, limit: int = 20) -> list:
        return self.quick_copy.search(keyword, limit)
    
    # Todo 方法
    def add_todo(self, title: str, description: str = '', priority: str = '中',
                 start_date: str = '', due_date: str = '', tags: list = None,
                 completed: int = 0, pinned: int = 0, status: str = '进行中') -> int:
        return self.todos.add(
            title=title, description=description, priority=priority,
            start_date=start_date, due_date=due_date, tags=tags,
            completed=completed, pinned=pinned, status=status
        )
    
    def get_todos(self, completed: int = None) -> list:
        return self.todos.get_all(completed)
    
    def update_todo(self, todo_id: int, **kwargs) -> bool:
        return self.todos.update(todo_id, **kwargs)
    
    def delete_todo(self, todo_id: int) -> bool:
        return self.todos.delete(todo_id)
    
    def toggle_todo_completed(self, todo_id: int) -> bool:
        return self.todos.toggle_completed(todo_id)
    
    def toggle_todo_pinned(self, todo_id: int) -> bool:
        return self.todos.toggle_pinned(todo_id)
    
    def search_todos(self, keyword: str, limit: int = 20) -> list:
        return self.todos.search(keyword, limit)
    
    # AI 方法
    def add_ai_conversation(self, title: str, provider: str, model_id: str,
                           system_prompt: str = '', pinned: int = 0, archived: int = 0) -> int:
        return self.ai.add_conversation(
            title=title, provider=provider, model_id=model_id,
            system_prompt=system_prompt, pinned=pinned, archived=archived
        )
    
    def get_ai_conversations(self, archived: int = 0) -> list:
        return self.ai.get_conversations(archived)
    
    def update_ai_conversation(self, conversation_id: int, **kwargs) -> bool:
        return self.ai.update_conversation(conversation_id, **kwargs)
    
    def delete_ai_conversation(self, conversation_id: int) -> bool:
        return self.ai.delete_conversation(conversation_id)
    
    def add_ai_message(self, conversation_id: int, role: str, content: str,
                      tool_name: str = '', tool_payload: str = '',
                      status: str = 'done', token_input: int = 0,
                      token_output: int = 0, latency_ms: int = 0) -> int:
        return self.ai.add_message(
            conversation_id=conversation_id, role=role, content=content,
            tool_name=tool_name, tool_payload=tool_payload, status=status,
            token_input=token_input, token_output=token_output, latency_ms=latency_ms
        )
    
    def get_ai_messages(self, conversation_id: int) -> list:
        return self.ai.get_messages(conversation_id)
    
    def update_ai_message(self, message_id: int, **kwargs) -> bool:
        return self.ai.update_message(message_id, **kwargs)
    
    def delete_ai_message(self, message_id: int) -> bool:
        return self.ai.delete_message(message_id)
    
    # Notebook 方法
    def add_note(self, plugin_id: str, title: str, content: str,
                 category_name: str = None, note_type: str = 'markdown',
                 sort_order: int = 0, color: str = None) -> int:
        category_id = self._resolve_category_id(plugin_id, category_name)
        return self.notebooks.add(
            plugin_id=plugin_id, category_id=category_id,
            title=title, content=content, note_type=note_type,
            sort_order=sort_order, color=color
        )
    
    def get_notes(self, plugin_id: str, category_id: int = None) -> list:
        return self.notebooks.get_by_plugin(plugin_id, category_id)
    
    def update_note(self, plugin_id: str, note_id: int, **kwargs) -> bool:
        return self.notebooks.update(note_id, **kwargs)
    
    def delete_note(self, plugin_id: str, note_id: int) -> bool:
        return self.notebooks.delete(note_id)
    
    def search_notes(self, plugin_id: str, keyword: str, limit: int = 20) -> list:
        return self.notebooks.search(plugin_id, keyword, limit)
    
    def note_exists(self, plugin_id: str, title: str) -> bool:
        return self.notebooks.exists(plugin_id, title)
    
    # 辅助方法
    def _resolve_category_id(self, plugin_id: str, category_name: str = None) -> Optional[int]:
        """解析分类 ID"""
        if not category_name:
            return None
        categories = self.categories.get_by_plugin(plugin_id)
        for cat in categories:
            if cat['name'] == category_name:
                return cat['id']
        return None
    
    # Import 方法（保持向后兼容）
    def import_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入数据（跳过已存在的书签）"""
        return ImportService(self).import_bookmarks_from_json(plugin_id, json_path)
    
    def import_commands_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入命令数据"""
        return ImportService(self).import_commands_from_json(plugin_id, json_path)
    
    def import_apps_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入应用数据"""
        return ImportService(self).import_apps_from_json(plugin_id, json_path)
