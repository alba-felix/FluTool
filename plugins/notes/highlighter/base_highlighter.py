"""
语法高亮器基类 - 包含通用语法高亮规则
"""

import re
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QFont


class BaseHighlighter(QSyntaxHighlighter):
    """语法高亮器基类"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []
        self._setup_common_rules()
    
    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
    
    def _setup_common_rules(self):
        """设置通用高亮规则"""
        
        # 数字 - 偏红色
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 158, 160))
        
        # 单引号和双引号及其内容 - 绿色
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 200, 0))
        
        # 方括号 - 紫色
        bracket_format = QTextCharFormat()
        bracket_format.setForeground(QColor(210, 48, 255))
        
        # 尖括号 - 紫色
        angle_bracket_format = QTextCharFormat()
        angle_bracket_format.setForeground(QColor(128, 10, 128))
        
        # HTTP/HTTPS连接 - 蓝色
        url_format = QTextCharFormat()
        url_format.setForeground(QColor(0, 120, 215))
        url_format.setFontUnderline(True)
        
        # 井号后内容 - 灰色
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)
        
        # 圆括号
        paren_format = QTextCharFormat()
        paren_format.setForeground(QColor(255, 215, 0))
        
        # 花括号 - 深蓝色
        curly_brace_format = QTextCharFormat()
        curly_brace_format.setForeground(QColor(0, 150, 255))
        
        # 十六进制颜色值 - 橙色
        hex_color_format = QTextCharFormat()
        hex_color_format.setForeground(QColor(255, 165, 0))
        
        # 添加通用规则
        # 数字规则
        self.highlighting_rules.append((r'\b\d+\b', number_format))
        self.highlighting_rules.append((r'\b\d+\.\d+\b', number_format))
        
        # 字符串规则
        self.highlighting_rules.append((r'"[^"]*"', string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))
        
        # 方括号规则
        self.highlighting_rules.append((r'\[', bracket_format))
        self.highlighting_rules.append((r'\]', bracket_format))
        
        # 尖括号规则
        self.highlighting_rules.append((r'<', angle_bracket_format))
        self.highlighting_rules.append((r'>', angle_bracket_format))
        
        # HTTP/HTTPS连接规则
        self.highlighting_rules.append((r'https?://[^\s]+', url_format))
        
        # 注释规则
        self.highlighting_rules.append((r'#[^\n]*', comment_format))
        
        # 圆括号规则
        self.highlighting_rules.append((r'\(', paren_format))
        self.highlighting_rules.append((r'\)', paren_format))
        
        # 花括号规则
        self.highlighting_rules.append((r'\{', curly_brace_format))
        self.highlighting_rules.append((r'\}', curly_brace_format))
        
        # 十六进制颜色值规则
        self.highlighting_rules.append((r'#[0-9a-fA-F]{6}\b', hex_color_format))
        self.highlighting_rules.append((r'#[0-9a-fA-F]{3}\b', hex_color_format))
        self.highlighting_rules.append((r'#[0-9a-fA-F]{8}\b', hex_color_format))
    
    def _setup_rules(self):
        """设置语言特定高亮规则（子类需要实现）"""
        pass