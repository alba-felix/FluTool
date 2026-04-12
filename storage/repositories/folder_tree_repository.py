from typing import Optional, List, Dict, Any
import json
from .base import BaseRepository, TableConfig


class FolderTreeRepository(BaseRepository):
    """文件夹树规则仓储"""
    
    def __init__(self, db_manager):
        config = TableConfig(
            table_name='folder_tree_rules',
            primary_key='id',
            plugin_field=None,  # 没有 plugin_id 字段
            has_category=False,
            searchable_fields=['rule_name'],
            allowed_fields=['rule_name', 'exclude_items']
        )
        super().__init__(db_manager, config)
    
    def add(self, rule_name: str, exclude_items: list) -> int:
        """添加文件夹树规则"""
        sql = """
            INSERT INTO folder_tree_rules (rule_name, exclude_items) 
            VALUES (?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (rule_name, json.dumps(exclude_items)))
            conn.commit()
            return cursor.lastrowid
    
    def get_by_name(self, rule_name: str) -> Optional[Dict[str, Any]]:
        """根据规则名获取规则"""
        sql = "SELECT * FROM folder_tree_rules WHERE rule_name = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (rule_name,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get('exclude_items'):
                    result['exclude_items'] = json.loads(result['exclude_items'])
                return result
            return None
    
    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有文件夹树规则"""
        sql = "SELECT * FROM folder_tree_rules ORDER BY id"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql)
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result.get('exclude_items'):
                    result['exclude_items'] = json.loads(result['exclude_items'])
                results.append(result)
            return results
    
    def update_by_name(self, rule_name: str, exclude_items: list) -> bool:
        """根据规则名更新规则"""
        sql = """
            UPDATE folder_tree_rules 
            SET exclude_items = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE rule_name = ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (json.dumps(exclude_items), rule_name))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_by_name(self, rule_name: str) -> bool:
        """根据规则名删除规则"""
        sql = "DELETE FROM folder_tree_rules WHERE rule_name = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (rule_name,))
            conn.commit()
            return cursor.rowcount > 0
    
    def exists(self, rule_name: str) -> bool:
        """检查规则是否存在"""
        sql = "SELECT 1 FROM folder_tree_rules WHERE rule_name = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (rule_name,))
            return cursor.fetchone() is not None
    
    def search(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索文件夹树规则"""
        sql = """
            SELECT id, rule_name, exclude_items 
            FROM folder_tree_rules 
            WHERE rule_name LIKE ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (f'%{keyword}%',))
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result.get('exclude_items'):
                    result['exclude_items'] = json.loads(result['exclude_items'])
                results.append(result)
            return results
