"""JSON 语法高亮器，基于 QSyntaxHighlighter，深浅主题自适应配色"""

import collections
import re

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from qfluentwidgets import isDarkTheme, qconfig

# 单次交替正则扫描全部 token，named group 区分类型；键名（冒号前瞻）优先于普通字符串
_MEGA_PATTERN = re.compile(
    r'(?P<key>"(?:\\.|[^"\\])*"(?=\s*:))'
    r'|(?P<string>"(?:\\.|[^"\\])*")'
    r'|(?P<number>-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)'
    r'|(?P<keyword>\b(?:true|false|null)\b)'
    r'|(?P<punct>[{}\[\],:])'
)
# 超过该行数时主题切换改为分批重高亮，避免阻塞 UI
_BATCH_THRESHOLD = 150
# 每批重高亮的行数（约 40ms，不阻塞事件循环）
_BATCH_SIZE = 40
# 超过该行数时主题切换不再刷新高亮颜色（大文本避免后台耗时）
_MAX_HIGHLIGHT_LINES = 500


def _make_fmt(color: QColor, bold: bool = False) -> QTextCharFormat:
    """构造带指定前景色的字符格式"""
    fmt = QTextCharFormat()
    fmt.setForeground(color)
    if bold:
        fmt.setFontWeight(QFont.Bold)
    return fmt


class JsonHighlighter(QSyntaxHighlighter):
    """JSON 语法高亮器：键、字符串、数字、关键字、标点分色显示

    性能说明：Qt 5 的 rehighlight() 会对每个 block 强制重新排版，
    大文本下会阻塞界面。本实现每行一次性 setFormat() 并缓存格式对象。
    主题切换时：<=150 行整篇重高亮；150~500 行分批 rehighlightBlock
    后台刷新；>500 行只更新配色、不整篇刷新，切换本身毫秒级返回。
    """

    def __init__(self, document):
        super().__init__(document)
        self._formats: dict = {}
        self._pending_blocks = collections.deque()
        self._update_colors(isDarkTheme())
        qconfig.themeChangedFinished.connect(self._on_theme_changed)

    def _update_colors(self, dark: bool) -> None:
        """按主题更新配色（参照 VS Code 默认 JSON 配色），格式对象缓存复用"""
        colors = {
            "key": QColor("#9cdcfe" if dark else "#0b6fb8"),
            "string": QColor("#ce9178" if dark else "#a31515"),
            "number": QColor("#b5cea8" if dark else "#098658"),
            "keyword": QColor("#569cd6" if dark else "#0000ff"),
            "punct": QColor("#d4d4d4" if dark else "#333333"),
        }
        self._formats = {
            "key": _make_fmt(colors["key"], True),
            "string": _make_fmt(colors["string"]),
            "number": _make_fmt(colors["number"]),
            "keyword": _make_fmt(colors["keyword"]),
            "punct": _make_fmt(colors["punct"]),
        }

    def _on_theme_changed(self) -> None:
        """主题切换后更新配色；大文本分批重高亮避免阻塞 UI"""
        self._update_colors(isDarkTheme())
        if self.document().blockCount() > _MAX_HIGHLIGHT_LINES:
            # 超限大文本：只更新后续新内容的配色，不整篇刷新，切换瞬间完成
            return
        self._pending_blocks.clear()
        if self.document().blockCount() <= _BATCH_THRESHOLD:
            self.rehighlight()
            return
        # 中量文本：入队全部 block，分批 rehighlightBlock，切换即刻返回
        block = self.document().firstBlock()
        while block.isValid():
            self._pending_blocks.append(block)
            block = block.next()
        QTimer.singleShot(0, self._process_pending_blocks)

    def _process_pending_blocks(self) -> None:
        """后台分批重高亮一个文本块队列"""
        for _ in range(_BATCH_SIZE):
            if not self._pending_blocks:
                return
            self.rehighlightBlock(self._pending_blocks.popleft())
        QTimer.singleShot(0, self._process_pending_blocks)

    def highlightBlock(self, text: str) -> None:
        """单行高亮：一次扫描后合并相邻同色段，逐段 setFormat 写入"""
        # 合并相邻同色段，减少 setFormat 调用（PyQt 边界转换开销大）
        segments = []
        for match in _MEGA_PATTERN.finditer(text):
            fmt = self._formats[match.lastgroup]
            if segments and segments[-1][1] == match.start() and segments[-1][2] is fmt:
                start, length, _ = segments[-1]
                segments[-1] = (start, length + match.end() - match.start(), fmt)
            else:
                segments.append((match.start(), match.end() - match.start(), fmt))
        for start, length, fmt in segments:
            self.setFormat(start, length, fmt)
