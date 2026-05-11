"""应用启动器插件业务服务。"""

from typing import Any, Dict, List, Optional

from storage import DatabaseManager


class AppLauncherService:
    """封装应用启动器插件的数据访问。"""

    def __init__(self, plugin_id: str, db: Optional[DatabaseManager] = None):
        self.plugin_id = plugin_id
        self.db = db or DatabaseManager()

    def list_categories(self) -> List[Dict[str, Any]]:
        """获取分类列表。"""
        return self.db.get_categories(self.plugin_id)

    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取分类。"""
        return next((category for category in self.list_categories() if category.get("id") == category_id), None)

    def get_or_create_category(self, name: str) -> int:
        """获取或创建分类。"""
        category = next((item for item in self.list_categories() if item.get("name") == name), None)
        if category:
            return category["id"]
        return self.add_category(name)

    def add_category(self, name: str, **kwargs) -> int:
        """添加分类。"""
        category_id = self.db.add_category(self.plugin_id, name)
        if kwargs:
            self.update_category(category_id, **kwargs)
        return category_id

    def update_category(self, category_id: int, name: str = None, **kwargs) -> bool:
        """更新分类。"""
        return self.db.update_category(self.plugin_id, category_id, name=name, **kwargs)

    def update_category_sort_orders(self, category_ids: List[int]) -> bool:
        """更新分类排序。"""
        return self.db.update_category_sort_orders(self.plugin_id, category_ids)

    def delete_category(self, category_id: int) -> bool:
        """删除分类。"""
        return self.db.delete_category(self.plugin_id, category_id)

    def list_apps(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取应用列表。"""
        return self.db.get_apps(self.plugin_id, category_id)

    def add_app(self, name: str, target_path: str, category_id: Optional[int] = None,
                icon_path: str = "", arguments: str = "", notes: str = "") -> int:
        """添加应用。"""
        return self.db.add_app(
            plugin_id=self.plugin_id,
            name=name,
            target_path=target_path,
            category_id=category_id,
            icon_path=icon_path,
            arguments=arguments,
            notes=notes,
        )

    def update_app(self, app_id: int, **kwargs) -> bool:
        """更新应用。"""
        return self.db.update_app(self.plugin_id, app_id, **kwargs)

    def delete_app(self, app_id: int) -> bool:
        """删除应用。"""
        return self.db.delete_app(self.plugin_id, app_id)

    def search_apps(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索应用。"""
        return self.db.search_apps(self.plugin_id, keyword)

    def batch_update_apps(self, app_ids: List[int], **kwargs) -> int:
        """批量更新应用。"""
        return self.db.batch_update_apps(self.plugin_id, app_ids, **kwargs)

    def batch_delete_apps(self, app_ids: List[int]) -> int:
        """批量删除应用。"""
        return self.db.batch_delete_apps(self.plugin_id, app_ids)

    def app_exists(self, name: str, target_path: str) -> bool:
        """检查应用是否存在。"""
        return self.db.app_exists(self.plugin_id, name, target_path)

    def list_recent_apps(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近启动的应用。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM app_launcher
                WHERE plugin_id = ? AND last_launch_time IS NOT NULL
                ORDER BY last_launch_time DESC
                LIMIT ?
                """,
                (self.plugin_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_favorite_apps(self) -> List[Dict[str, Any]]:
        """获取收藏应用。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM app_launcher
                WHERE plugin_id = ? AND is_favorite = 1
                ORDER BY name
                """,
                (self.plugin_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def record_launch(self, app_id: int) -> bool:
        """记录应用启动次数和时间。"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE app_launcher
                SET launch_count = launch_count + 1,
                    last_launch_time = CURRENT_TIMESTAMP
                WHERE plugin_id = ? AND id = ?
                """,
                (self.plugin_id, app_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def set_favorite(self, app_id: int, is_favorite: bool) -> bool:
        """设置收藏状态。"""
        return self.update_app(app_id, is_favorite=1 if is_favorite else 0)
