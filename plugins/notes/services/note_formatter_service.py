"""
笔记格式化服务模块
提供笔记内容的格式化和展示相关功能
"""
from datetime import datetime
from typing import Optional


class NoteFormatterService:
    """
    笔记格式化服务类
    
    负责笔记内容的格式化、预览生成、时间格式化等展示相关功能
    
    属性:
        _default_max_lines: 默认预览行数
        _default_max_chars: 默认预览字符数
    """
    
    def __init__(
        self,
        default_max_lines: int = 2,
        default_max_chars: int = 100
    ):
        self._default_max_lines = default_max_lines
        self._default_max_chars = default_max_chars
    
    def get_preview(
        self,
        content: str,
        max_lines: Optional[int] = None,
        max_chars: Optional[int] = None
    ) -> str:
        """
        生成内容预览文本
        
        参数:
            content: 笔记内容
            max_lines: 最大行数
            max_chars: 最大字符数
            
        返回:
            预览文本
        """
        if not content:
            return ''
        
        max_lines = max_lines or self._default_max_lines
        max_chars = max_chars or self._default_max_chars
        
        lines = content.strip().split('\n')
        preview_lines = lines[:max_lines]
        preview = '\n'.join(preview_lines)
        
        if len(preview) > max_chars:
            preview = preview[:max_chars] + '...'
        
        if len(lines) > max_lines:
            preview += '...'
        
        return preview
    
    def get_relative_time(self, dt: Optional[datetime]) -> str:
        """
        获取相对时间描述
        
        参数:
            dt: 时间对象
            
        返回:
            相对时间描述字符串
        """
        if not dt:
            return ''
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f'{years}年前'
        elif diff.days > 30:
            months = diff.days // 30
            return f'{months}个月前'
        elif diff.days > 0:
            return f'{diff.days}天前'
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f'{hours}小时前'
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f'{minutes}分钟前'
        else:
            return '刚刚'
    
    def get_formatted_title(self, title: str, max_length: int = 50) -> str:
        """
        格式化标题
        
        参数:
            title: 原始标题
            max_length: 最大长度
            
        返回:
            格式化后的标题
        """
        if not title:
            return '无标题'
        
        title = title.strip()
        
        if len(title) > max_length:
            return title[:max_length] + '...'
        
        return title
    
    def get_tags_display(self, tags: list, max_tags: int = 3) -> str:
        """
        获取标签显示文本
        
        参数:
            tags: 标签列表
            max_tags: 最大显示标签数
            
        返回:
            标签显示文本
        """
        if not tags:
            return ''
        
        display_tags = tags[:max_tags]
        result = ' '.join(f'#{tag}' for tag in display_tags)
        
        if len(tags) > max_tags:
            result += f' +{len(tags) - max_tags}'
        
        return result
    
    def get_status_text(
        self,
        is_favorite: bool = False,
        is_archived: bool = False
    ) -> str:
        """
        获取状态文本
        
        参数:
            is_favorite: 是否收藏
            is_archived: 是否归档
            
        返回:
            状态文本
        """
        statuses = []
        if is_favorite:
            statuses.append('已收藏')
        if is_archived:
            statuses.append('已归档')
        return ' · '.join(statuses) if statuses else ''
    
    def get_word_count(self, content: str) -> int:
        """
        获取字数统计
        
        参数:
            content: 内容
            
        返回:
            字数
        """
        if not content:
            return 0
        return len(content.strip())
    
    def get_reading_time(self, content: str, words_per_minute: int = 300) -> int:
        """
        估算阅读时间（分钟）
        
        参数:
            content: 内容
            words_per_minute: 每分钟阅读字数
            
        返回:
            预计阅读时间（分钟）
        """
        word_count = self.get_word_count(content)
        if word_count == 0:
            return 0
        return max(1, word_count // words_per_minute)