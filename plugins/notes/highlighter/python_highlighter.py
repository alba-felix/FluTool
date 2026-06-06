"""
Python语法高亮器
"""

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QTextCharFormat, QFont, QColor

from .base_highlighter import BaseHighlighter


class PythonHighlighter(BaseHighlighter):
    """Python语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()
    
    def _setup_rules(self):
        """设置Python特定语法高亮规则"""
        
        # 关键字格式 - 橙色
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))
        keyword_format.setFontWeight(QFont.Bold)
        
        # 函数名格式 - 蓝色
        function_format = QTextCharFormat()
        function_format.setForeground(QColor(102, 153, 255))
        
        # 类名格式 - 蓝色
        class_format = QTextCharFormat()
        class_format.setForeground(QColor(102, 153, 255))
        class_format.setFontWeight(QFont.Bold)
        
        # 字符串格式 - 绿色
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 200, 0))
        
        # 注释格式 - 灰色
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)
        
        # 数字格式 - 紫色
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(200, 100, 200))
        
        # 运算符格式 - 蓝色
        operator_format = QTextCharFormat()
        operator_format.setForeground(QColor(100, 150, 255))
        
        # 装饰器格式 - 金色
        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor(255, 200, 100))
        
        # Python关键字列表
        python_keywords = [
            # 控制流
            'if', 'else', 'elif', 'for', 'while', 'break', 'continue',
            'try', 'except', 'finally', 'raise', 'with',
            # 函数和类
            'def', 'class', 'return', 'yield', 'lambda',
            # 导入
            'import', 'from', 'as',
            # 逻辑操作
            'and', 'or', 'not', 'in', 'is',
            # 特殊值
            'True', 'False', 'None',
            # 其他
            'pass', 'del', 'global', 'nonlocal', 'assert', 'async', 'await'
        ]
        
        # 添加Python关键字规则
        for keyword in python_keywords:
            self.highlighting_rules.append((f'\\b{keyword}\\b', keyword_format))
        
        # 添加函数调用规则
        self.highlighting_rules.append((r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\()', function_format))
        
        # 添加类名规则
        self.highlighting_rules.append((r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', class_format))
        
        # 添加函数定义规则
        self.highlighting_rules.append((r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)', function_format))
        
        # 添加字符串规则
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))
        self.highlighting_rules.append((r'"""[^"]*"""', string_format))
        self.highlighting_rules.append((r"'''[^']*'''", string_format))
        
        # 添加注释规则
        self.highlighting_rules.append((r'#[^\n]*', comment_format))
        
        # 添加数字规则
        self.highlighting_rules.append((r'\b[0-9]+\b', number_format))
        self.highlighting_rules.append((r'\b[0-9]+\.[0-9]+\b', number_format))
        self.highlighting_rules.append((r'\b0x[0-9a-fA-F]+\b', number_format))
        
        # 添加运算符规则
        self.highlighting_rules.append((r'[+\-*/%=<>!&|^~]', operator_format))
        
        # 添加装饰器规则
        self.highlighting_rules.append((r'@[a-zA-Z_][a-zA-Z0-9_]*', decorator_format))