from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class TableConfig:
    """表配置

    Attributes:
        table_name: 数据库表名
        primary_key: 主键字段名，默认 'id'
        plugin_field: 插件 ID 字段名，设置 None 表示该表无插件隔离
        has_category: 是否有分类关联
        category_field: 分类关联的外键字段名
        searchable_fields: 可搜索字段列表
        allowed_fields: 允许插入/更新的字段列表
        search_order_by: 搜索结果的默认排序，如 'pinned DESC, id DESC'
        search_joins: 搜索时的额外 JOIN 子句列表
        search_select: 自定义 SELECT 字段，覆盖默认的 t.*
    """
    table_name: str
    primary_key: str = 'id'
    plugin_field: str = 'plugin_id'
    has_category: bool = True
    category_field: str = 'category_id'
    searchable_fields: Optional[List[str]] = None
    allowed_fields: Optional[List[str]] = None
    search_order_by: Optional[str] = None
    search_joins: Optional[List[str]] = None
    search_select: Optional[str] = None


class BaseRepository(ABC):
    """泛型仓储基类"""

    def __init__(self, db_manager, config: TableConfig):
        self.db = db_manager
        self.config = config

    def add(self, **kwargs) -> int:
        """添加记录"""
        # 过滤允许的字段
        if self.config.allowed_fields:
            filtered = {k: v for k, v in kwargs.items()
                       if k in self.config.allowed_fields}
        else:
            filtered = kwargs

        if not filtered:
            raise ValueError("No valid fields provided for insert")

        # 构建插入语句
        columns = ', '.join(filtered.keys())
        placeholders = ', '.join(['?'] * len(filtered))
        sql = f"INSERT INTO {self.config.table_name} ({columns}) VALUES ({placeholders})"

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, list(filtered.values()))
            conn.commit()
            return cursor.lastrowid

    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据 ID 获取记录"""
        sql = f"SELECT * FROM {self.config.table_name} WHERE {self.config.primary_key} = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (record_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_by_plugin(self, plugin_id: str, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """根据插件 ID 获取记录"""
        if category_id is not None and self.config.has_category:
            sql = f"""
                SELECT t.*, c.name as category_name
                FROM {self.config.table_name} t
                LEFT JOIN categories c ON t.{self.config.category_field} = c.id
                WHERE t.{self.config.plugin_field} = ? AND t.{self.config.category_field} = ?
                ORDER BY t.sort_order, t.id
            """
            params = (plugin_id, category_id)
        else:
            sql = f"""
                SELECT t.*, c.name as category_name
                FROM {self.config.table_name} t
                LEFT JOIN categories c ON t.{self.config.category_field} = c.id
                WHERE t.{self.config.plugin_field} = ?
                ORDER BY t.sort_order, t.id
            """
            params = (plugin_id,)

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def update(self, record_id: int, **kwargs) -> bool:
        """更新记录"""
        if self.config.allowed_fields:
            filtered = {k: v for k, v in kwargs.items()
                       if k in self.config.allowed_fields}
        else:
            filtered = kwargs

        if not filtered:
            return False

        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE {self.config.table_name}
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE {self.config.primary_key} = ?
        """
        values = list(filtered.values()) + [record_id]

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, record_id: int) -> bool:
        """删除记录"""
        sql = f"DELETE FROM {self.config.table_name} WHERE {self.config.primary_key} = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (record_id,))
            conn.commit()
            return cursor.rowcount > 0

    def search(self, plugin_id: str = None, keyword: str = "", limit: int = 20,
               order_by: str = None) -> List[Dict[str, Any]]:
        """搜索记录

        当 plugin_id 为 None 时不按插件过滤（适用于无插件隔离或全局搜索）。
        搜索逻辑由 TableConfig 配置驱动，子类通常无需重写。

        Args:
            plugin_id: 插件 ID，None 表示不过滤插件
            keyword: 搜索关键词
            limit: 返回结果数上限
            order_by: 自定义排序，可覆盖 config.search_order_by

        Returns:
            搜索结果列表（每项为行字典）
        """
        if not self.config.searchable_fields:
            return []

        # 构建 SELECT 字段
        select_fields = self.config.search_select or "t.*"
        if self.config.has_category:
            select_fields += ", c.name as category_name"

        sql = f"SELECT {select_fields} FROM {self.config.table_name} t"

        # 添加分类表 JOIN
        if self.config.has_category:
            sql += f" LEFT JOIN categories c ON t.{self.config.category_field} = c.id"

        # 添加自定义 JOIN
        if self.config.search_joins:
            for join in self.config.search_joins:
                sql += f" {join}"

        # 构建 WHERE 条件
        conditions = []
        params = []

        # 插件过滤
        if plugin_id is not None and self.config.plugin_field is not None:
            conditions.append(f"t.{self.config.plugin_field} = ?")
            params.append(plugin_id)

        # 搜索关键词
        if keyword:
            like_conditions = []
            for field in self.config.searchable_fields:
                like_conditions.append(f"t.{field} LIKE ?")
                params.append(f'%{keyword}%')
            if like_conditions:
                conditions.append(f"({' OR '.join(like_conditions)})")

        if conditions:
            sql += f" WHERE {' AND '.join(conditions)}"

        # 排序
        if order_by:
            sql += f" ORDER BY {order_by}"
        elif self.config.search_order_by:
            sql += f" ORDER BY {self.config.search_order_by}"
        else:
            sql += " ORDER BY t.sort_order, t.id"

        # 限制结果数量
        sql += " LIMIT ?"
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取所有记录"""
        sql = f"SELECT * FROM {self.config.table_name} ORDER BY {self.config.primary_key} LIMIT ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (limit,))
            return [dict(row) for row in cursor.fetchall()]