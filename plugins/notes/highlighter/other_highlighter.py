"""
其他语言高亮器 - 使用通用语法高亮规则
"""
from ..highlighter.base_highlighter import BaseHighlighter


class OtherHighlighter(BaseHighlighter):
    """其他语言高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_common_rules()