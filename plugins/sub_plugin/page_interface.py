"""标签页接口 - 所有标签页必须实现此接口"""

from typing import Optional, Type
from PyQt5.QtWidgets import QWidget

from qfluentwidgets import FluentIcon as FIF


class TabPageInterface:
    """标签页接口 - 所有标签页必须实现此接口"""
    
    page_id: str = ""
    page_name: str = ""
    page_icon: Optional[FIF] = None
    
    @classmethod
    def create(cls, parent=None) -> QWidget:
        """创建标签页内容"""
        raise NotImplementedError
