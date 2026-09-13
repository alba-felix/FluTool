"""标签页接口 - 所有标签页必须实现此接口"""

from typing import Optional
from PyQt5.QtWidgets import QWidget

from qfluentwidgets import FluentIcon as FIF


class TabPageInterface:
    """标签页接口 - 所有标签页必须实现此接口"""

    page_id: str = ""
    page_name: str = ""
    page_icon: Optional[FIF] = None

    @classmethod
    def create(cls, parent=None, core=None) -> QWidget:
        """创建标签页内容

        Args:
            parent: 父 widget
            core: AppCore 实例（可选，需要访问核心服务时传入）
        """
        raise NotImplementedError
