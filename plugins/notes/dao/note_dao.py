import json
from typing import List, Optional
from datetime import datetime

from .database import Database
from ..models.note import Note, CodeBlock


class NoteDAO:
    def __init__(self, db: Database = None):
        self.db = db or Database.get_instance()

    def _row_to_note(self, row) -> Note:
        tags = json.loads(row['tags']) if row['tags'] else []
        code_blocks_data = json.loads(row['code_blocks']) if row['code_blocks'] else []
        code_blocks = [CodeBlock.from_dict(cb) for cb in code_blocks_data]
        images = json.loads(row['images']) if row['images'] else []

        return Note(
            id=row['id'],
            title=row['title'],
            content=row['content'],
            category_id=row['category_id'],
            category_name=row['category_name'] or '',
            tags=tags,
            code_blocks=code_blocks,
            remarks=row['remarks'] or '',
            images=images,
            is_archived=bool(row['is_archived']),
            is_favorite=bool(row['is_favorite']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

    def get_all(self, include_archived: bool = False) -> List[Note]:
        query = '''
            SELECT n.*, c.name as category_name
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
        '''
        if not include_archived:
            query += ' WHERE n.is_archived = 0'
        query += ' ORDER BY n.updated_at DESC'

        cursor = self.db.execute(query)
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def get_by_id(self, note_id: int) -> Optional[Note]:
        query = '''
            SELECT n.*, c.name as category_name
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE n.id = ?
        '''
        cursor = self.db.execute(query, (note_id,))
        row = cursor.fetchone()
        return self._row_to_note(row) if row else None

    def get_by_category(self, category_id: int, include_archived: bool = False) -> List[Note]:
        if category_id <= 0:
            return []
        query = '''
            SELECT n.*, c.name as category_name
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE n.category_id = ?
        '''
        params = [category_id]
        if not include_archived:
            query += ' AND n.is_archived = 0'
        query += ' ORDER BY n.updated_at DESC'

        cursor = self.db.execute(query, tuple(params))
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def get_favorites(self) -> List[Note]:
        query = '''
            SELECT n.*, c.name as category_name
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE n.is_favorite = 1 AND n.is_archived = 0
            ORDER BY n.updated_at DESC
        '''
        cursor = self.db.execute(query)
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def get_archived(self) -> List[Note]:
        query = '''
            SELECT n.*, c.name as category_name
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE n.is_archived = 1
            ORDER BY n.updated_at DESC
        '''
        cursor = self.db.execute(query)
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def search(self, keyword: str) -> List[Note]:
        if not keyword or not keyword.strip():
            return []
        query = '''
            SELECT n.*, c.name as category_name
            FROM notes n
            LEFT JOIN categories c ON n.category_id = c.id
            WHERE n.is_archived = 0 AND (
                n.title LIKE ? OR
                n.content LIKE ? OR
                n.tags LIKE ? OR
                n.remarks LIKE ?
            )
            ORDER BY n.updated_at DESC
        '''
        pattern = f'%{keyword}%'
        cursor = self.db.execute(query, (pattern, pattern, pattern, pattern))
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def add(self, note: Note) -> Optional[int]:
        query = '''
            INSERT INTO notes (title, content, category_id, tags, code_blocks, remarks, images, is_archived, is_favorite)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        try:
            cursor = self.db.execute(query, (
                note.title,
                note.content,
                note.category_id,
                json.dumps(note.tags),
                json.dumps([cb.to_dict() for cb in note.code_blocks]),
                note.remarks,
                json.dumps(note.images),
                1 if note.is_archived else 0,
                1 if note.is_favorite else 0
            ))
            self.db.commit()
            return cursor.lastrowid
        except Exception:
            return None

    def update(self, note: Note) -> bool:
        if note.id is None:
            return False
        query = '''
            UPDATE notes SET
                title = ?, content = ?, category_id = ?, tags = ?,
                code_blocks = ?, remarks = ?, images = ?,
                is_archived = ?, is_favorite = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        try:
            cursor = self.db.execute(query, (
                note.title,
                note.content,
                note.category_id,
                json.dumps(note.tags),
                json.dumps([cb.to_dict() for cb in note.code_blocks]),
                note.remarks,
                json.dumps(note.images),
                1 if note.is_archived else 0,
                1 if note.is_favorite else 0,
                note.id
            ))
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def delete(self, note_id: int) -> bool:
        if note_id <= 0:
            return False
        try:
            cursor = self.db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def toggle_favorite(self, note_id: int) -> bool:
        if note_id <= 0:
            return False
        try:
            cursor = self.db.execute(
                "UPDATE notes SET is_favorite = NOT is_favorite, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (note_id,)
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def toggle_archive(self, note_id: int) -> bool:
        if note_id <= 0:
            return False
        try:
            cursor = self.db.execute(
                "UPDATE notes SET is_archived = NOT is_archived, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (note_id,)
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def set_category(self, note_id: int, category_id: Optional[int]) -> bool:
        if note_id <= 0:
            return False
        try:
            cursor = self.db.execute(
                "UPDATE notes SET category_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (category_id, note_id)
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception:
            return False

    def count_by_category(self, category_id: int) -> int:
        if category_id <= 0:
            return 0
        cursor = self.db.execute(
            "SELECT COUNT(*) FROM notes WHERE category_id = ? AND is_archived = 0",
            (category_id,)
        )
        return cursor.fetchone()[0]

    def get_images(self, note_id: int) -> List[str]:
        cursor = self.db.execute("SELECT images FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if row and row['images']:
            return json.loads(row['images'])
        return []