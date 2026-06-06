from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class CodeBlock:
    language: str
    content: str

    def to_dict(self) -> dict:
        return {'language': self.language, 'content': self.content}

    @classmethod
    def from_dict(cls, data: dict) -> 'CodeBlock':
        return cls(language=data.get('language', ''), content=data.get('content', ''))


@dataclass
class Category:
    id: Optional[int] = None
    name: str = ''
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Category':
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        )


@dataclass
class Note:
    id: Optional[int] = None
    title: str = ''
    content: str = ''
    category_id: Optional[int] = None
    category_name: str = ''
    tags: List[str] = field(default_factory=list)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    remarks: str = ''
    images: List[str] = field(default_factory=list)
    is_archived: bool = False
    is_favorite: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    _formatter = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'tags': self.tags,
            'code_blocks': [cb.to_dict() for cb in self.code_blocks],
            'remarks': self.remarks,
            'images': self.images,
            'is_archived': self.is_archived,
            'is_favorite': self.is_favorite,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Note':
        tags = data.get('tags', [])
        if isinstance(tags, str):
            tags = json.loads(tags) if tags else []

        code_blocks_data = data.get('code_blocks', [])
        if isinstance(code_blocks_data, str):
            code_blocks_data = json.loads(code_blocks_data) if code_blocks_data else []
        code_blocks = [CodeBlock.from_dict(cb) for cb in code_blocks_data]

        images = data.get('images', [])
        if isinstance(images, str):
            images = json.loads(images) if images else []

        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            category_id=data.get('category_id'),
            category_name=data.get('category_name', ''),
            tags=tags,
            code_blocks=code_blocks,
            remarks=data.get('remarks', ''),
            images=images,
            is_archived=bool(data.get('is_archived', 0)),
            is_favorite=bool(data.get('is_favorite', 0)),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )

    @classmethod
    def _get_formatter(cls):
        if cls._formatter is None:
            from services.note_formatter_service import NoteFormatterService
            cls._formatter = NoteFormatterService()
        return cls._formatter

    def get_preview(self, max_lines: int = 2, max_chars: int = 100) -> str:
        """
        生成内容预览（向后兼容方法）
        
        实际逻辑委托给 NoteFormatterService
        """
        return self._get_formatter().get_preview(
            self.content,
            max_lines=max_lines,
            max_chars=max_chars
        )

    def get_relative_time(self) -> str:
        """
        获取相对时间描述（向后兼容方法）
        
        实际逻辑委托给 NoteFormatterService
        """
        return self._get_formatter().get_relative_time(self.created_at)