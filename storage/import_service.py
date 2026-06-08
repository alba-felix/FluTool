"""数据库 JSON 导入服务。"""

import json
from typing import Optional


class ImportService:
    """封装导入 JSON 数据的流程。"""

    def __init__(self, db):
        self.db = db

    def _resolve_category_id(self, plugin_id: str, category_name: Optional[str]) -> Optional[int]:
        """根据分类名称解析分类ID"""
        if not category_name:
            return None
        for cat in self.db.categories.get_by_plugin(plugin_id):
            if cat["name"] == category_name:
                return cat["id"]
        return None

    def import_bookmarks_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入书签数据，跳过已存在的 URL。"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for cat_order, category in enumerate(data.get('categories', [])):
            cat_name = category.get('name', '未命名分类')
            self.db.categories.add_or_get(plugin_id, cat_name, cat_order)
            for bm_order, website in enumerate(category.get('websites', [])):
                url = website.get('url', '')
                if self.db.bookmarks.exists(plugin_id, url):
                    continue

                category_id = self._resolve_category_id(plugin_id, cat_name)
                self.db.bookmarks.add(
                    plugin_id=plugin_id,
                    category_id=category_id,
                    name=website.get('name', ''),
                    url=url,
                    icon=website.get('icon', ''),
                    notes=website.get('notes', ''),
                    sort_order=bm_order
                )
                count += 1
        return count

    def import_commands_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入命令数据。"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for cat_name, commands in data.items():
            category_id = self.db.categories.add_or_get(plugin_id, cat_name)
            if not isinstance(commands, dict):
                continue

            for cmd_order, (cmd_name, cmd_data) in enumerate(commands.items()):
                if self.db.commands.exists(plugin_id, cmd_name, cat_name):
                    continue

                if isinstance(cmd_data, dict):
                    content = cmd_data.get('content', '')
                    sub_title = cmd_data.get('sub_title', '')
                else:
                    content = str(cmd_data)
                    sub_title = ''

                self.db.commands.add(
                    plugin_id=plugin_id,
                    category_id=category_id,
                    name=cmd_name,
                    content=content,
                    sub_title=sub_title,
                    sort_order=cmd_order
                )
                count += 1
        return count

    def import_apps_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入应用数据。"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for cat_order, category in enumerate(data.get('categories', [])):
            cat_name = category.get('name', '未命名分类')
            self.db.categories.add_or_get(plugin_id, cat_name, cat_order)
            for app_order, app in enumerate(category.get('apps', [])):
                name = app.get('name', '')
                target_path = app.get('target_path', '')
                if self.db.apps.exists(plugin_id, name, target_path):
                    continue

                category_id = self._resolve_category_id(plugin_id, cat_name)
                self.db.apps.add(
                    plugin_id=plugin_id,
                    category_id=category_id,
                    name=name,
                    target_path=target_path,
                    icon_path=app.get('icon_path', ''),
                    arguments=app.get('arguments', ''),
                    notes=app.get('notes', ''),
                    sort_order=app_order
                )
                count += 1
        return count

