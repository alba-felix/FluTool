"""
随手记语法高亮器
包含基础高亮规则和语言特定高亮规则
"""

from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor


class BaseHighlighter(QSyntaxHighlighter):
    """基础高亮器 - 包含通用语法高亮规则"""

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

        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 255, 0))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 255, 0))

        bracket_format = QTextCharFormat()
        bracket_format.setForeground(QColor(128, 0, 128))

        angle_bracket_format = QTextCharFormat()
        angle_bracket_format.setForeground(QColor(128, 0, 128))

        url_format = QTextCharFormat()
        url_format.setForeground(QColor(0, 0, 255))
        url_format.setFontUnderline(True)

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)

        paren_format = QTextCharFormat()
        paren_format.setForeground(QColor(255, 255, 0))

        hex_color_format = QTextCharFormat()
        hex_color_format.setForeground(QColor(255, 165, 0))

        self.highlighting_rules.append((r'\b\d+\b', number_format))
        self.highlighting_rules.append((r'\b\d+\.\d+\b', number_format))

        self.highlighting_rules.append((r'"[^"]*"', string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))

        self.highlighting_rules.append((r'\[', bracket_format))
        self.highlighting_rules.append((r'\]', bracket_format))

        self.highlighting_rules.append((r'<', angle_bracket_format))
        self.highlighting_rules.append((r'>', angle_bracket_format))

        self.highlighting_rules.append((r'https?://[^\s]+', url_format))

        self.highlighting_rules.append((r'#[^\n]*', comment_format))

        self.highlighting_rules.append((r'\(', paren_format))
        self.highlighting_rules.append((r'\)', paren_format))

        self.highlighting_rules.append((r'#[0-9a-fA-F]{6}\b', hex_color_format))
        self.highlighting_rules.append((r'#[0-9a-fA-F]{3}\b', hex_color_format))
        self.highlighting_rules.append((r'#[0-9a-fA-F]{8}\b', hex_color_format))


class PythonHighlighter(BaseHighlighter):
    """Python语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()

    def _setup_rules(self):
        """设置Python特定语法高亮规则"""

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))
        keyword_format.setFontWeight(QFont.Bold)

        function_format = QTextCharFormat()
        function_format.setForeground(QColor(0, 150, 255))

        class_format = QTextCharFormat()
        class_format.setForeground(QColor(0, 150, 255))
        class_format.setFontWeight(QFont.Bold)

        py_string_format = QTextCharFormat()
        py_string_format.setForeground(QColor(0, 200, 100))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)

        number_format = QTextCharFormat()
        number_format.setForeground(QColor(200, 100, 255))

        python_keywords = [
            'if', 'else', 'elif', 'for', 'while', 'break', 'continue',
            'try', 'except', 'finally', 'raise', 'with',
            'def', 'class', 'return', 'yield', 'lambda',
            'import', 'from', 'as',
            'and', 'or', 'not', 'in', 'is',
            'True', 'False', 'None',
            'pass', 'del', 'global', 'nonlocal', 'assert',
            'async', 'await'
        ]

        for keyword in python_keywords:
            self.highlighting_rules.append((f'\\b{keyword}\\b', keyword_format))

        self.highlighting_rules.append((r'\b[a-zA-Z_][a-zA-Z0-9_]*\(', function_format))
        self.highlighting_rules.append((r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)', class_format))
        self.highlighting_rules.append((r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)', function_format))

        self.highlighting_rules.append((r'"[^"]*"', py_string_format))
        self.highlighting_rules.append((r"'[^']*'", py_string_format))
        self.highlighting_rules.append((r'"""[^"""]*"""', py_string_format))
        self.highlighting_rules.append((r"'''[^''']*'''", py_string_format))

        self.highlighting_rules.append((r'#[^\n]*', comment_format))

        self.highlighting_rules.append((r'\b\d+\b', number_format))
        self.highlighting_rules.append((r'\b\d+\.\d+\b', number_format))
        self.highlighting_rules.append((r'\b0x[0-9a-fA-F]+\b', number_format))


class BashHighlighter(BaseHighlighter):
    """Bash脚本高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()

    def _setup_rules(self):
        """设置Bash特定语法高亮规则"""

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))
        keyword_format.setFontWeight(QFont.Bold)

        function_format = QTextCharFormat()
        function_format.setForeground(QColor(0, 150, 255))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 200, 100))

        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor(255, 100, 100))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)

        bash_keywords = [
            'if', 'then', 'else', 'elif', 'fi',
            'for', 'while', 'do', 'done',
            'case', 'esac',
            'function', 'return',
            'in', 'select', 'until',
            'export', 'source', 'alias', 'unalias',
            'cd', 'pwd', 'ls', 'echo', 'printf', 'read',
            'grep', 'sed', 'awk', 'find', 'xargs',
            'chmod', 'chown', 'mkdir', 'rm', 'cp', 'mv', 'touch',
            'sudo', 'apt', 'yum', 'dnf', 'pacman', 'brew',
            'ssh', 'scp', 'rsync', 'curl', 'wget',
            'git', 'docker', 'kubectl',
            'true', 'false'
        ]

        for keyword in bash_keywords:
            self.highlighting_rules.append((f'\\b{keyword}\\b', keyword_format))

        self.highlighting_rules.append((r'\$[a-zA-Z_][a-zA-Z0-9_]*', variable_format))
        self.highlighting_rules.append((r'\$\{[^\}]+\}', variable_format))

        self.highlighting_rules.append((r'"[^"]*"', string_format))
        self.highlighting_rules.append((r"'[^']*'", string_format))

        self.highlighting_rules.append((r'#[^\n]*', comment_format))

        self.highlighting_rules.append((r'\b[a-zA-Z_][a-zA-Z0-9_]*=', function_format))


class NotebookHighlighter(QSyntaxHighlighter):
    """随手记智能高亮器 - 根据内容片段自动检测语言类型"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.base = BaseHighlighter(parent)
        self.python = PythonHighlighter(parent)
        self.bash = BashHighlighter(parent)
        self._rules = []
        self._setup_rules()

    def _setup_rules(self):
        """设置代码片段检测规则"""
        self._rules = [
            (r'```python\n[\s\S]*?\n```', 'python'),
            (r'```py\n[\s\S]*?\n```', 'python'),
            (r'```bash\n[\s\S]*?\n```', 'bash'),
            (r'```sh\n[\s\S]*?\n```', 'bash'),
            (r'```shell\n[\s\S]*?\n```', 'bash'),
            (r'`[^`\n]+`', 'inline'),
        ]

    def highlightBlock(self, text):
        """高亮文本块 - 先应用基础高亮，再处理代码片段"""
        self.base.highlightBlock(text)
        self._highlight_snippets(text)

    def _highlight_snippets(self, text):
        """高亮代码片段"""
        for pattern, lang in self._rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                snippet = text[index:index + length]

                if lang == 'python':
                    self._apply_python_highlight(snippet, index)
                elif lang == 'bash':
                    self._apply_bash_highlight(snippet, index)
                elif lang == 'inline':
                    self._apply_inline_highlight(snippet, index)

                index = expression.indexIn(text, index + length)

    def _apply_python_highlight(self, snippet, offset):
        """应用Python高亮到代码片段"""
        clean_code = self._strip_fence(snippet)
        if not clean_code:
            return

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))
        keyword_format.setFontWeight(QFont.Bold)

        function_format = QTextCharFormat()
        function_format.setForeground(QColor(0, 150, 255))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 200, 100))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)

        python_keywords = [
            'if', 'else', 'elif', 'for', 'while', 'break', 'continue',
            'try', 'except', 'finally', 'raise', 'with',
            'def', 'class', 'return', 'yield', 'lambda',
            'import', 'from', 'as',
            'and', 'or', 'not', 'in', 'is',
            'True', 'False', 'None',
            'pass', 'del', 'global', 'nonlocal', 'assert'
        ]

        for keyword in python_keywords:
            pattern = f'\\b{keyword}\\b'
            expr = QRegExp(pattern)
            idx = expr.indexIn(clean_code)
            while idx >= 0:
                length = expr.matchedLength()
                self.setFormat(offset + idx, length, keyword_format)
                idx = expr.indexIn(clean_code, idx + length)

        func_expr = QRegExp(r'\b[a-zA-Z_][a-zA-Z0-9_]*\(')
        idx = func_expr.indexIn(clean_code)
        while idx >= 0:
            length = func_expr.matchedLength()
            self.setFormat(offset + idx, length, function_format)
            idx = func_expr.indexIn(clean_code, idx + length)

        for pattern, fmt in [
            (r'"[^"]*"', string_format),
            (r"'[^']*'", string_format),
            (r'#[^\n]*', comment_format),
        ]:
            expr = QRegExp(pattern)
            idx = expr.indexIn(clean_code)
            while idx >= 0:
                length = expr.matchedLength()
                self.setFormat(offset + idx, length, fmt)
                idx = expr.indexIn(clean_code, idx + length)

    def _apply_bash_highlight(self, snippet, offset):
        """应用Bash高亮到代码片段"""
        clean_code = self._strip_fence(snippet)
        if not clean_code:
            return

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(255, 165, 0))
        keyword_format.setFontWeight(QFont.Bold)

        variable_format = QTextCharFormat()
        variable_format.setForeground(QColor(255, 100, 100))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 200, 100))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))
        comment_format.setFontItalic(True)

        bash_keywords = [
            'if', 'then', 'else', 'elif', 'fi',
            'for', 'while', 'do', 'done',
            'case', 'esac', 'function',
            'export', 'source', 'alias',
            'cd', 'echo', 'read', 'printf',
            'grep', 'sed', 'awk', 'find',
            'chmod', 'mkdir', 'rm', 'cp', 'mv',
            'sudo', 'git', 'docker',
            'true', 'false'
        ]

        for keyword in bash_keywords:
            pattern = f'\\b{keyword}\\b'
            expr = QRegExp(pattern)
            idx = expr.indexIn(clean_code)
            while idx >= 0:
                length = expr.matchedLength()
                self.setFormat(offset + idx, length, keyword_format)
                idx = expr.indexIn(clean_code, idx + length)

        var_expr = QRegExp(r'\$[a-zA-Z_][a-zA-Z0-9_]*')
        idx = var_expr.indexIn(clean_code)
        while idx >= 0:
            length = var_expr.matchedLength()
            self.setFormat(offset + idx, length, variable_format)
            idx = var_expr.indexIn(clean_code, idx + length)

        for pattern, fmt in [
            (r'"[^"]*"', string_format),
            (r"'[^']*'", string_format),
            (r'#[^\n]*', comment_format),
        ]:
            expr = QRegExp(pattern)
            idx = expr.indexIn(clean_code)
            while idx >= 0:
                length = expr.matchedLength()
                self.setFormat(offset + idx, length, fmt)
                idx = expr.indexIn(clean_code, idx + length)

    def _apply_inline_highlight(self, snippet, offset):
        """应用行内代码高亮"""
        inline_format = QTextCharFormat()
        inline_format.setForeground(QColor(255, 200, 100))
        inline_format.setBackground(QColor(50, 50, 50))
        self.setFormat(offset, len(snippet), inline_format)

    def _strip_fence(self, code):
        """去除代码 fences"""
        lines = code.split('\n')
        if len(lines) <= 2:
            return code
        return '\n'.join(lines[1:-1] if lines[0].startswith('```') else lines)
