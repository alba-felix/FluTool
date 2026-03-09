from typing import List, Dict, Any
import json
from .database import DatabaseManager


class PasswordManager(DatabaseManager):
    """
    密码管理器
    
    继承自 DatabaseManager，提供密码相关的数据库操作。
    """
    
    def add_password(self, plugin_id: str, username: str, password: str,
                     platform: str = '', category_name: str = None,
                     category_id: int = None,
                     email: str = '', notes: str = '', sort_order: int = 0) -> int:
        """添加密码"""
        with self.get_connection() as conn:
            # 如果传入了 category_id，直接使用；否则通过 category_name 查找
            if category_id is None and category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                "INSERT INTO passwords (plugin_id, category_id, platform, username, password, email, notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (plugin_id, category_id, platform, username, password, email, notes, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def password_exists(self, plugin_id: str, username: str, password: str) -> bool:
        """检查密码是否已存在"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM passwords WHERE plugin_id = ? AND username = ? AND password = ?",
                (plugin_id, username, password)
            )
            return cursor.fetchone() is not None
    
    def get_passwords(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取密码列表"""
        with self.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT p.*, c.name as category_name 
                       FROM passwords p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.plugin_id = ? AND p.category_id = ?
                       ORDER BY p.sort_order, p.id""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT p.*, c.name as category_name 
                       FROM passwords p 
                       LEFT JOIN categories c ON p.category_id = c.id 
                       WHERE p.plugin_id = ?
                       ORDER BY p.sort_order, p.id""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_password(self, plugin_id: str, password_id: int, **kwargs) -> bool:
        """更新密码"""
        allowed_fields = {'platform', 'username', 'password', 'email', 'notes', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, password_id]
        with self.get_connection() as conn:
            conn.execute(
                f"UPDATE passwords SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_password(self, plugin_id: str, password_id: int) -> bool:
        """删除密码"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM passwords WHERE plugin_id = ? AND id = ?",
                (plugin_id, password_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_passwords(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索密码"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """SELECT p.*, c.name as category_name 
                   FROM passwords p 
                   LEFT JOIN categories c ON p.category_id = c.id 
                   WHERE p.plugin_id = ? AND (p.platform LIKE ? OR p.username LIKE ? OR p.email LIKE ? OR p.notes LIKE ?)
                   ORDER BY p.sort_order, p.id""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def import_passwords_from_json(self, plugin_id: str, json_path: str) -> int:
        """从 JSON 文件导入密码数据"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for cat_order, category in enumerate(data.get('categories', [])):
            cat_name = category.get('name', '未命名分类')
            self.add_category(plugin_id, cat_name, cat_order)
            for pwd_order, password in enumerate(category.get('passwords', [])):
                username = password.get('username', '')
                pwd = password.get('password', '')
                if self.password_exists(plugin_id, username, pwd):
                    continue
                self.add_password(
                    plugin_id=plugin_id,
                    platform=password.get('platform', ''),
                    username=username,
                    password=pwd,
                    category_name=cat_name,
                    email=password.get('email', ''),
                    notes=password.get('notes', ''),
                    sort_order=pwd_order
                )
                count += 1
        return count
