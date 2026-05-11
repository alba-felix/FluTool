from typing import List, Dict, Any, Optional
from .base import BaseRepository, TableConfig


class QuickCopyRepository:
    """快速复制仓储（包含卡片和项目）"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    # ============ 卡片操作 ============
    
    def add_card(self, title: str, sort_order: int = 0) -> int:
        """添加快速复制卡片"""
        sql = "INSERT INTO quick_copy_cards (title, sort_order) VALUES (?, ?)"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (title, sort_order))
            conn.commit()
            return cursor.lastrowid
    
    def get_cards(self) -> List[Dict[str, Any]]:
        """获取所有快速复制卡片"""
        sql = "SELECT * FROM quick_copy_cards ORDER BY sort_order, id"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql)
            return [dict(row) for row in cursor.fetchall()]

    def get_cards_with_items(self) -> List[Dict[str, Any]]:
        """一次性获取所有快速复制卡片及其内容项"""
        sql = """
            SELECT
                c.id AS card_id,
                c.title AS card_title,
                c.sort_order AS card_sort_order,
                c.created_at AS card_created_at,
                c.updated_at AS card_updated_at,
                i.id AS item_id,
                i.content AS item_content,
                i.sort_order AS item_sort_order,
                i.created_at AS item_created_at
            FROM quick_copy_cards c
            LEFT JOIN quick_copy_items i ON i.card_id = c.id
            ORDER BY c.sort_order, c.id, i.sort_order, i.id
        """
        cards = {}
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql)
            for row in cursor.fetchall():
                card_id = row["card_id"]
                if card_id not in cards:
                    cards[card_id] = {
                        "id": card_id,
                        "title": row["card_title"],
                        "sort_order": row["card_sort_order"],
                        "created_at": row["card_created_at"],
                        "updated_at": row["card_updated_at"],
                        "items": []
                    }

                if row["item_id"] is None:
                    continue

                cards[card_id]["items"].append({
                    "id": row["item_id"],
                    "card_id": card_id,
                    "content": row["item_content"],
                    "sort_order": row["item_sort_order"],
                    "created_at": row["item_created_at"]
                })

        return list(cards.values())
    
    def update_card(self, card_id: int, **kwargs) -> bool:
        """更新快速复制卡片"""
        allowed_fields = {'title', 'sort_order'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not filtered:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE quick_copy_cards 
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """
        values = list(filtered.values()) + [card_id]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_card(self, card_id: int) -> bool:
        """删除快速复制卡片并清理内容项"""
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM quick_copy_items WHERE card_id = ?", (card_id,))
            cursor = conn.execute("DELETE FROM quick_copy_cards WHERE id = ?", (card_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    # ============ 项目操作 ============
    
    def add_item(self, card_id: int, content: str, sort_order: int = 0) -> int:
        """添加快速复制项"""
        sql = """
            INSERT INTO quick_copy_items (card_id, content, sort_order) 
            VALUES (?, ?, ?)
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (card_id, content, sort_order))
            conn.commit()
            return cursor.lastrowid
    
    def get_items(self, card_id: int) -> List[Dict[str, Any]]:
        """获取快速复制项"""
        sql = """
            SELECT * FROM quick_copy_items 
            WHERE card_id = ? 
            ORDER BY sort_order, id
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (card_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_item(self, item_id: int, **kwargs) -> bool:
        """更新快速复制项"""
        allowed_fields = {'content', 'sort_order'}
        filtered = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not filtered:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in filtered.keys())
        sql = f"""
            UPDATE quick_copy_items 
            SET {set_clause}
            WHERE id = ?
        """
        values = list(filtered.values()) + [item_id]
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_item(self, item_id: int) -> bool:
        """删除快速复制项"""
        sql = "DELETE FROM quick_copy_items WHERE id = ?"
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (item_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索快速复制内容"""
        sql = """
            SELECT i.id, i.card_id, i.content, c.title as card_title 
            FROM quick_copy_items i 
            JOIN quick_copy_cards c ON i.card_id = c.id 
            WHERE i.content LIKE ? OR c.title LIKE ?
            ORDER BY i.id DESC 
            LIMIT ?
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(sql, (f'%{keyword}%', f'%{keyword}%', limit))
            return [dict(row) for row in cursor.fetchall()]
