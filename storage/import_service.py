"""数据库 JSON 导入服务。"""

import json


class ImportService:
    """封装导入 JSON 数据的流程。"""

    def __init__(self, db):
        self.db = db

    def import_bookmarks_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入书签数据，跳过已存在的 URL。"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for cat_order, category in enumerate(data.get('categories', [])):
            cat_name = category.get('name', '未命名分类')
            self.db.add_category(plugin_id, cat_name, cat_order)
            for bm_order, website in enumerate(category.get('websites', [])):
                url = website.get('url', '')
                if self.db.bookmark_exists(plugin_id, url):
                    continue

                self.db.add_bookmark(
                    plugin_id=plugin_id,
                    name=website.get('name', ''),
                    url=url,
                    category_name=cat_name,
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
            self.db.add_category(plugin_id, cat_name)
            if not isinstance(commands, dict):
                continue

            for cmd_order, (cmd_name, cmd_data) in enumerate(commands.items()):
                if self.db.command_exists(plugin_id, cmd_name, cat_name):
                    continue

                if isinstance(cmd_data, dict):
                    content = cmd_data.get('content', '')
                    sub_title = cmd_data.get('sub_title', '')
                else:
                    content = str(cmd_data)
                    sub_title = ''

                self.db.add_command(
                    plugin_id=plugin_id,
                    name=cmd_name,
                    content=content,
                    category_name=cat_name,
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
            self.db.add_category(plugin_id, cat_name, cat_order)
            for app_order, app in enumerate(category.get('apps', [])):
                name = app.get('name', '')
                target_path = app.get('target_path', '')
                if self.db.app_exists(plugin_id, name, target_path):
                    continue

                self.db.add_app(
                    plugin_id=plugin_id,
                    name=name,
                    target_path=target_path,
                    category_name=cat_name,
                    icon_path=app.get('icon_path', ''),
                    arguments=app.get('arguments', ''),
                    notes=app.get('notes', ''),
                    sort_order=app_order
                )
                count += 1
        return count

