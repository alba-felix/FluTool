"""随手记语法高亮器 - 性能优化版本"""

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor


class HighlighterCache:
    """高亮器缓存 - 避免重复创建格式对象"""
    _formats = {}
    _patterns = {}
    
    @classmethod
    def get_format(cls, key: str, color: tuple, bold: bool = False, italic: bool = False, underline: bool = False) -> QTextCharFormat:
        """获取或创建格式对象"""
        cache_key = (key, color, bold, italic, underline)
        if cache_key not in cls._formats:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(*color))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            if italic:
                fmt.setFontItalic(True)
            if underline:
                fmt.setFontUnderline(True)
            cls._formats[cache_key] = fmt
        return cls._formats[cache_key]
    
    @classmethod
    def get_pattern(cls, pattern: str) -> QRegularExpression:
        """获取或创建正则表达式对象"""
        if pattern not in cls._patterns:
            cls._patterns[pattern] = QRegularExpression(pattern)
        return cls._patterns[pattern]


class BaseHighlighter(QSyntaxHighlighter):
    """基础高亮器 - 优化版本"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []
        self._setup_common_rules()

    def highlightBlock(self, text):
        """高亮文本块 - 使用缓存的正则表达式"""
        for pattern, fmt in self._rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

    def _setup_common_rules(self):
        """设置通用高亮规则 - 预编译正则表达式"""
        cache = HighlighterCache
        
        rules = [
            (r'\b\d+\b', cache.get_format('number', (255, 255, 0))),
            (r'\b\d+\.\d+\b', cache.get_format('number', (255, 255, 0))),
            (r'"[^"]*"', cache.get_format('string', (0, 255, 0))),
            (r"'[^']*'", cache.get_format('string', (0, 255, 0))),
            (r'\[', cache.get_format('bracket', (128, 0, 128))),
            (r'\]', cache.get_format('bracket', (128, 0, 128))),
            (r'<', cache.get_format('angle', (128, 0, 128))),
            (r'>', cache.get_format('angle', (128, 0, 128))),
            (r'https?://[^\s]+', cache.get_format('url', (0, 0, 255), underline=True)),
            (r'#[^\n]*', cache.get_format('comment', (128, 128, 128), italic=True)),
            (r'\(', cache.get_format('paren', (255, 255, 0))),
            (r'\)', cache.get_format('paren', (255, 255, 0))),
            (r'#[0-9a-fA-F]{6}\b', cache.get_format('hex_color', (255, 165, 0))),
            (r'#[0-9a-fA-F]{3}\b', cache.get_format('hex_color', (255, 165, 0))),
            (r'#[0-9a-fA-F]{8}\b', cache.get_format('hex_color', (255, 165, 0))),
        ]
        
        for pattern_str, fmt in rules:
            pattern = QRegularExpression(pattern_str)
            self._rules.append((pattern, fmt))


class PythonHighlighter(BaseHighlighter):
    """Python语法高亮器 - 优化版本"""

    _keywords = [
        'if', 'else', 'elif', 'for', 'while', 'break', 'continue',
        'try', 'except', 'finally', 'raise', 'with',
        'def', 'class', 'return', 'yield', 'lambda',
        'import', 'from', 'as',
        'and', 'or', 'not', 'in', 'is',
        'True', 'False', 'None',
        'pass', 'del', 'global', 'nonlocal', 'assert',
        'async', 'await'
    ]
    
    _keyword_pattern = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()

    def _setup_rules(self):
        """设置Python特定语法高亮规则"""
        cache = HighlighterCache
        
        keyword_fmt = cache.get_format('py_keyword', (255, 165, 0), bold=True)
        function_fmt = cache.get_format('py_function', (0, 150, 255))
        class_fmt = cache.get_format('py_class', (0, 150, 255), bold=True)
        string_fmt = cache.get_format('py_string', (0, 200, 100))
        comment_fmt = cache.get_format('py_comment', (128, 128, 128), italic=True)
        number_fmt = cache.get_format('py_number', (200, 100, 255))
        
        keyword_pattern_str = r'\b(' + '|'.join(self._keywords) + r')\b'
        self._rules.append((QRegularExpression(keyword_pattern_str), keyword_fmt))
        
        self._rules.extend([
            (QRegularExpression(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\()'), function_fmt),
            (QRegularExpression(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)'), class_fmt),
            (QRegularExpression(r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)'), function_fmt),
            (QRegularExpression(r'"[^"]*"'), string_fmt),
            (QRegularExpression(r"'[^']*'"), string_fmt),
            (QRegularExpression(r'"""[\s\S]*?"""'), string_fmt),
            (QRegularExpression(r"'''[\s\S]*?'''"), string_fmt),
            (QRegularExpression(r'#[^\n]*'), comment_fmt),
            (QRegularExpression(r'\b\d+\b'), number_fmt),
            (QRegularExpression(r'\b\d+\.\d+\b'), number_fmt),
            (QRegularExpression(r'\b0x[0-9a-fA-F]+\b'), number_fmt),
        ])


class BashHighlighter(BaseHighlighter):
    """Bash脚本高亮器 - 优化版本"""

    _keywords = [
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()

    def _setup_rules(self):
        """设置Bash特定语法高亮规则"""
        cache = HighlighterCache
        
        keyword_fmt = cache.get_format('bash_keyword', (255, 165, 0), bold=True)
        function_fmt = cache.get_format('bash_function', (0, 150, 255))
        string_fmt = cache.get_format('bash_string', (0, 200, 100))
        variable_fmt = cache.get_format('bash_variable', (255, 100, 100))
        comment_fmt = cache.get_format('bash_comment', (128, 128, 128), italic=True)
        
        keyword_pattern_str = r'\b(' + '|'.join(self._keywords) + r')\b'
        self._rules.append((QRegularExpression(keyword_pattern_str), keyword_fmt))
        
        self._rules.extend([
            (QRegularExpression(r'\$[a-zA-Z_][a-zA-Z0-9_]*'), variable_fmt),
            (QRegularExpression(r'\$\{[^\}]+\}'), variable_fmt),
            (QRegularExpression(r'"[^"]*"'), string_fmt),
            (QRegularExpression(r"'[^']*'"), string_fmt),
            (QRegularExpression(r'#[^\n]*'), comment_fmt),
            (QRegularExpression(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?==)'), function_fmt),
        ])


class NotebookHighlighter(QSyntaxHighlighter):
    """随手记智能高亮器 - 优化版本"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._base_rules = self._create_base_rules()
        self._snippet_patterns = [
            (QRegularExpression(r'```python\n[\s\S]*?\n```'), 'python'),
            (QRegularExpression(r'```py\n[\s\S]*?\n```'), 'python'),
            (QRegularExpression(r'```bash\n[\s\S]*?\n```'), 'bash'),
            (QRegularExpression(r'```sh\n[\s\S]*?\n```'), 'bash'),
            (QRegularExpression(r'```shell\n[\s\S]*?\n```'), 'bash'),
            (QRegularExpression(r'`[^`\n]+`'), 'inline'),
        ]
        self._python_rules = self._create_python_rules()
        self._bash_rules = self._create_bash_rules()
        self._inline_fmt = HighlighterCache.get_format('inline', (255, 200, 100))

    def _create_base_rules(self):
        """创建基础高亮规则"""
        cache = HighlighterCache
        return [
            (QRegularExpression(r'\b\d+\b'), cache.get_format('base_num', (255, 255, 0))),
            (QRegularExpression(r'\b\d+\.\d+\b'), cache.get_format('base_num', (255, 255, 0))),
            (QRegularExpression(r'"[^"]*"'), cache.get_format('base_str', (0, 255, 0))),
            (QRegularExpression(r"'[^']*'"), cache.get_format('base_str', (0, 255, 0))),
            (QRegularExpression(r'#[^\n]*'), cache.get_format('base_comment', (128, 128, 128), italic=True)),
        ]

    def _create_python_rules(self):
        """创建Python高亮规则"""
        cache = HighlighterCache
        keywords = ['if', 'else', 'elif', 'for', 'while', 'break', 'continue',
                   'try', 'except', 'finally', 'raise', 'with',
                   'def', 'class', 'return', 'yield', 'lambda',
                   'import', 'from', 'as', 'and', 'or', 'not', 'in', 'is',
                   'True', 'False', 'None', 'pass', 'del', 'global', 'nonlocal', 'assert']
        
        keyword_pattern = QRegularExpression(r'\b(' + '|'.join(keywords) + r')\b')
        return [
            (keyword_pattern, cache.get_format('snip_py_kw', (255, 165, 0), bold=True)),
            (QRegularExpression(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\()'), cache.get_format('snip_py_func', (0, 150, 255))),
            (QRegularExpression(r'"[^"]*"'), cache.get_format('snip_py_str', (0, 200, 100))),
            (QRegularExpression(r"'[^']*'"), cache.get_format('snip_py_str', (0, 200, 100))),
            (QRegularExpression(r'#[^\n]*'), cache.get_format('snip_py_comment', (128, 128, 128), italic=True)),
        ]

    def _create_bash_rules(self):
        """创建Bash高亮规则"""
        cache = HighlighterCache
        keywords = ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done',
                   'case', 'esac', 'function', 'export', 'source', 'alias',
                   'cd', 'echo', 'read', 'printf', 'grep', 'sed', 'awk', 'find',
                   'chmod', 'mkdir', 'rm', 'cp', 'mv', 'sudo', 'git', 'docker', 'true', 'false']
        
        keyword_pattern = QRegularExpression(r'\b(' + '|'.join(keywords) + r')\b')
        return [
            (keyword_pattern, cache.get_format('snip_bash_kw', (255, 165, 0), bold=True)),
            (QRegularExpression(r'\$[a-zA-Z_][a-zA-Z0-9_]*'), cache.get_format('snip_bash_var', (255, 100, 100))),
            (QRegularExpression(r'"[^"]*"'), cache.get_format('snip_bash_str', (0, 200, 100))),
            (QRegularExpression(r"'[^']*'"), cache.get_format('snip_bash_str', (0, 200, 100))),
            (QRegularExpression(r'#[^\n]*'), cache.get_format('snip_bash_comment', (128, 128, 128), italic=True)),
        ]

    def highlightBlock(self, text):
        """高亮文本块"""
        for pattern, fmt in self._base_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
        
        for pattern, lang in self._snippet_patterns:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()
                snippet = match.capturedTexts()[0] if match.capturedTexts() else text[start:start+length]
                
                if lang == 'python':
                    self._apply_rules(snippet, start, self._python_rules)
                elif lang == 'bash':
                    self._apply_rules(snippet, start, self._bash_rules)
                elif lang == 'inline':
                    self.setFormat(start, length, self._inline_fmt)

    def _apply_rules(self, text: str, offset: int, rules: list):
        """应用高亮规则"""
        for pattern, fmt in rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(offset + match.capturedStart(), match.capturedLength(), fmt)
