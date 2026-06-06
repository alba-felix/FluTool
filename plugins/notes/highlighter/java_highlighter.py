"""
Java语法高亮器
"""

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QTextCharFormat, QFont, QColor

from .base_highlighter import BaseHighlighter


class JavaHighlighter(BaseHighlighter):
    """Java语法高亮器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()
    
    def _setup_rules(self):
        """设置Java特定语法高亮规则"""
        
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
        
        # 注解格式 - 金色
        annotation_format = QTextCharFormat()
        annotation_format.setForeground(QColor(255, 200, 100))
        
        # Java关键字列表
        java_keywords = [
            # 访问控制
            'public', 'private', 'protected',
            # 类相关
            'class', 'interface', 'extends', 'implements', 'abstract', 'final',
            # 方法相关
            'static', 'void', 'return', 'native', 'synchronized',
            # 控制流
            'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default',
            'break', 'continue', 'return',
            # 异常处理
            'try', 'catch', 'finally', 'throw', 'throws',
            # 类型
            'int', 'long', 'short', 'byte', 'float', 'double', 'boolean', 'char',
            # 其他
            'new', 'this', 'super', 'import', 'package', 'instanceof',
            'final', 'const', 'volatile', 'transient', 'strictfp',
            'enum', 'assert', 'goto', 'true', 'false', 'null'
        ]
        
        # 添加Java关键字规则
        for keyword in java_keywords:
            self.highlighting_rules.append((f'\\b{keyword}\\b', keyword_format))
        
        # 添加函数调用规则
        self.highlighting_rules.append((r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\()', function_format))
        
        # 添加类名规则
        self.highlighting_rules.append((r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', class_format))
        self.highlighting_rules.append((r'\binterface\s+([a-zA-Z_][a-zA-Z0-9_]*)', class_format))
        
        # 添加字符串规则
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))
        
        # 添加注释规则
        self.highlighting_rules.append((r'//[^\n]*', comment_format))
        self.highlighting_rules.append((r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/', comment_format))
        
        # 添加数字规则
        self.highlighting_rules.append((r'\b[0-9]+\b', number_format))
        self.highlighting_rules.append((r'\b[0-9]+\.[0-9]+[fFdD]?\b', number_format))
        self.highlighting_rules.append((r'\b0x[0-9a-fA-F]+\b', number_format))
        self.highlighting_rules.append((r'\b[0-9]+[lL]\b', number_format))
        
        # 添加运算符规则
        self.highlighting_rules.append((r'[+\-*/%=<>!&|^~?:]', operator_format))
        
        # 添加注解规则
        self.highlighting_rules.append((r'@[a-zA-Z_][a-zA-Z0-9_]*', annotation_format))