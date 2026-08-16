from typing import List, Optional
from datetime import datetime

from .database import Database
from ..models.note import Category


class CategoryDAO:
    def __init__(self, db: Database = None):
        self.db = db or Database.get_instance()

    def get_all(self) -> List[Category]:
        cursor = self.db.execute(
            "SELECT id, name, created_at FROM categories ORDER BY sort_order ASC, created_at ASC"
        )
        categories = []
        for row in cursor.fetchall():
            categories.append(Category(
                id=row['id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
            ))
        return categories

    def reorder(self, ordered_ids: List[int]) -> bool:
        """按给定 ID 顺序更新分类排序

        Args:
            ordered_ids: 分类 ID 列表，顺序即最终展示顺序

        Returns:
            是否全部更新成功
        """
        try:
            for index, category_id in enumerate(ordered_ids):
                cursor = self.db.execute(
                    "UPDATE categories SET sort_order = ? WHERE id = ?",
                    (index, category_id)
                )
            self.db.commit()
            return True
        except Exception:
            return False

    def get_max_sort_order(self) -> int:
        """获取当前最大排序值"""
        cursor = self.db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM categories")
        return cursor.fetchone()[0]

    def get_by_id(self, category_id: int) -> Optional[Category]:
        cursor = self.db.execute(
            "SELECT id, name, created_at FROM categories WHERE id = ?",
            (category_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Category(
            id=row['id'],
            name=row['name'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

    def get_by_name(self, name: str) -> Optional[Category]:
        cursor = self.db.execute(
            "SELECT id, name, created_at FROM categories WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return Category(
            id=row['id'],
            name=row['name'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

    def add(self, name: str) -> Optional[int]:
        try:
            cursor = self.db.execute(
                "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                (name, self.get_max_sort_order() + 1)
            )
            self.db.commit()
            return cursor.lastrowid
        except Exception:
            return None

    def update(self, category_id: int, name: str) -> bool:
        try:
            cursor = self.db.execute(
                "UPDATE categories SET name = ? WHERE id = ?",
                (name, category_id)
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def delete(self, category_id: int) -> bool:
        try:
            cursor = self.db.execute(
                "DELETE FROM categories WHERE id = ?",
                (category_id,)
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def exists(self, name: str) -> bool:
        cursor = self.db.execute(
            "SELECT COUNT(*) FROM categories WHERE name = ?",
            (name,)
        )
        return cursor.fetchone()[0] > 0

    def get_default_category(self) -> Optional[Category]:
        return self.get_by_name('默认')