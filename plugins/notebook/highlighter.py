"""随手记语法高亮器 - 性能优化版本"""

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor


class HighlighterCache:
    _formats = {}
    _patterns = {}

    @classmethod
    def get_format(cls, key: str, color: tuple, bold: bool = False, italic: bool = False, underline: bool = False) -> QTextCharFormat:
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
        if pattern not in cls._patterns:
            cls._patterns[pattern] = QRegularExpression(pattern)
        return cls._patterns[pattern]


class BaseHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class PythonHighlighter(BaseHighlighter):
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

    _keyword_regex = QRegularExpression(r'\b(' + '|'.join(_keywords) + r')\b')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()

    def _setup_rules(self):
        cache = HighlighterCache
        p = cache.get_pattern
        f = cache.get_format

        self._rules = [
            (PythonHighlighter._keyword_regex, f('py_keyword', (255, 165, 0), bold=True)),
            (p(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\()'), f('py_function', (0, 150, 255))),
            (p(r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)'), f('py_class', (0, 150, 255), bold=True)),
            (p(r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)'), f('py_function', (0, 150, 255))),
            (p(r'"[^"]*"'), f('py_string', (0, 200, 100))),
            (p(r"'[^']*'"), f('py_string', (0, 200, 100))),
            (p(r'"""[\s\S]*?"""'), f('py_string', (0, 200, 100))),
            (p(r"'''[\s\S]*?'''"), f('py_string', (0, 200, 100))),
            (p(r'#[^\n]*'), f('py_comment', (128, 128, 128), italic=True)),
            (p(r'\b\d+(?:\.\d+)?\b'), f('py_number', (200, 100, 255))),
            (p(r'\b0x[0-9a-fA-F]+\b'), f('py_number', (200, 100, 255))),
        ]


class BashHighlighter(BaseHighlighter):
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

    _keyword_regex = QRegularExpression(r'\b(' + '|'.join(_keywords) + r')\b')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_rules()

    def _setup_rules(self):
        cache = HighlighterCache
        p = cache.get_pattern
        f = cache.get_format

        self._rules = [
            (BashHighlighter._keyword_regex, f('bash_keyword', (255, 165, 0), bold=True)),
            (p(r'\$[a-zA-Z_][a-zA-Z0-9_]*'), f('bash_variable', (255, 100, 100))),
            (p(r'\$\{[^\}]+\}'), f('bash_variable', (255, 100, 100))),
            (p(r'"[^"]*"'), f('bash_string', (0, 200, 100))),
            (p(r"'[^']*'"), f('bash_string', (0, 200, 100))),
            (p(r'#[^\n]*'), f('bash_comment', (128, 128, 128), italic=True)),
            (p(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?==)'), f('bash_function', (0, 150, 255))),
        ]


class NotebookHighlighter(QSyntaxHighlighter):
    _python_keyword_regex = PythonHighlighter._keyword_regex
    _bash_keyword_regex = BashHighlighter._keyword_regex

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_snippet_matchers()
        self._base_rules = self._create_base_rules()
        self._python_rules = self._create_python_rules()
        self._bash_rules = self._create_bash_rules()
        self._inline_fmt = HighlighterCache.get_format('inline', (255, 200, 100))

    def _init_snippet_matchers(self):
        p = HighlighterCache.get_pattern
        self._snippet_matchers = [
            (p(r'```python\n[\s\S]*?\n```'), 'python'),
            (p(r'```py\n[\s\S]*?\n```'), 'python'),
            (p(r'```bash\n[\s\S]*?\n```'), 'bash'),
            (p(r'```sh\n[\s\S]*?\n```'), 'bash'),
            (p(r'```shell\n[\s\S]*?\n```'), 'bash'),
            (p(r'`[^`\n]+`'), 'inline'),
        ]

    def _create_base_rules(self):
        cache = HighlighterCache
        p = cache.get_pattern
        f = cache.get_format
        return [
            (p(r'\b\d+(?:\.\d+)?\b'), f('base_num', (255, 255, 0))),
            (p(r'"[^"]*"'), f('base_str', (0, 255, 0))),
            (p(r"'[^']*'"), f('base_str', (0, 255, 0))),
            (p(r'#[^\n]*'), f('base_comment', (128, 128, 128), italic=True)),
        ]

    def _create_python_rules(self):
        cache = HighlighterCache
        p = cache.get_pattern
        f = cache.get_format
        return [
            (NotebookHighlighter._python_keyword_regex, f('snip_py_kw', (255, 165, 0), bold=True)),
            (p(r'\b[a-zA-Z_][a-zA-Z0-9_]*(?=\()'), f('snip_py_func', (0, 150, 255))),
            (p(r'"[^"]*"'), f('snip_py_str', (0, 200, 100))),
            (p(r"'[^']*'"), f('snip_py_str', (0, 200, 100))),
            (p(r'#[^\n]*'), f('snip_py_comment', (128, 128, 128), italic=True)),
        ]

    def _create_bash_rules(self):
        cache = HighlighterCache
        p = cache.get_pattern
        f = cache.get_format
        return [
            (NotebookHighlighter._bash_keyword_regex, f('snip_bash_kw', (255, 165, 0), bold=True)),
            (p(r'\$[a-zA-Z_][a-zA-Z0-9_]*'), f('snip_bash_var', (255, 100, 100))),
            (p(r'"[^"]*"'), f('snip_bash_str', (0, 200, 100))),
            (p(r"'[^']*'"), f('snip_bash_str', (0, 200, 100))),
            (p(r'#[^\n]*'), f('snip_bash_comment', (128, 128, 128), italic=True)),
        ]

    def highlightBlock(self, text):
        for pattern, fmt in self._base_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        for pattern, lang in self._snippet_matchers:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                start = match.capturedStart()
                length = match.capturedLength()

                if lang == 'python':
                    self._apply_rules(match.captured(0), start, self._python_rules)
                elif lang == 'bash':
                    self._apply_rules(match.captured(0), start, self._bash_rules)
                elif lang == 'inline':
                    self.setFormat(start, length, self._inline_fmt)

    def _apply_rules(self, text: str, offset: int, rules: list):
        for pattern, fmt in rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(offset + match.capturedStart(), match.capturedLength(), fmt)
