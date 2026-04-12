from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Dict, Any
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class TableConfig:
    """表配置"""
    table_name: str
    primary_key: str = 'id'
    plugin_field: str = 'plugin_id'
    has_category: bool = True
    category_field: str = 'category_id'
    searchable_fields: Optional[List[str]] = None
    allowed_fields: Optional[List[str]] = None


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
    
    def search(self, plugin_id: str, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索记录"""
        if not self.config.searchable_fields:
            return []
        
        conditions = [f"t.{self.config.plugin_field} = ?"]
        params = [plugin_id]
        
        # 为每个可搜索字段添加 LIKE 条件
        like_conditions = []
        for field in self.config.searchable_fields:
            like_conditions.append(f"t.{field} LIKE ?")
            params.append(f'%{keyword}%')
        
        if like_conditions:
            conditions.append(f"({' OR '.join(like_conditions)})")
        
        sql = f"""
            SELECT t.*, c.name as category_name 
            FROM {self.config.table_name} t 
            LEFT JOIN categories c ON t.{self.config.category_field} = c.id 
            WHERE {' AND '.join(conditions)}
            ORDER BY t.sort_order, t.id
            LIMIT ?
        """
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
