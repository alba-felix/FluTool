from typing import List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QWidget, QTextEdit, QTabWidget, QMenu
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QTextCursor
from qfluentwidgets import MessageBoxBase, SubtitleLabel, PushButton, CaptionLabel, ComboBox, Pivot, isDarkTheme, qconfig, Theme

from ..models.note import CodeBlock
from ..highlighter.factory import HighlighterFactory


def _get_code_style():
    """根据主题获取代码样式"""
    if isDarkTheme():
        return '''
            QTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
            }
        '''
    else:
        return '''
            QTextEdit {
                background: #f8f8f8;
                color: #333333;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        '''


def _get_header_style():
    """根据主题获取标题样式"""
    if isDarkTheme():
        return 'color: #569cd6; padding: 4px 0;'
    else:
        return 'color: #0078d4; padding: 4px 0;'


class CodeTextEdit(QTextEdit):
    """自定义代码显示文本框，使用原生 QMenu 右键菜单"""

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        cursor = self.textCursor()
        has_selection = cursor.hasSelection()

        copy_action = menu.addAction("复制")
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(has_selection)

        select_all_action = menu.addAction("全选")
        select_all_action.triggered.connect(self.selectAll)

        menu.exec_(event.globalPos())


class CodeViewer(MessageBoxBase):
    """代码块查看器 - 支持查看多段代码"""
    
    def __init__(self, code_blocks: List[CodeBlock], title: str = '\u4ee3\u7801\u5757\u67e5\u770b', parent=None):
        super().__init__(parent)
        self._code_blocks = code_blocks
        self._title = title
        self._current_index = 0
        self._highlighters = []
        self._code_edits = []
        self._headers = []
        self._init_ui()
        self._connect_signals()
        self._show_code(0)

    def _init_ui(self):
        self.titleLabel = SubtitleLabel(self._title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.pivot = Pivot(self)
        self.pivot.setFixedHeight(36)
        
        for i, code_block in enumerate(self._code_blocks):
            label = f'{i + 1}. {code_block.language}'
            self.pivot.addItem(routeKey=str(i), text=label, onClick=lambda checked=False, idx=i: self._show_code(idx))
        
        if len(self._code_blocks) > 1:
            self.pivot.addItem(routeKey='all', text='\u67e5\u770b\u5168\u90e8', onClick=lambda: self._show_all_codes())
        
        self.viewLayout.addWidget(self.pivot)

        self.code_display = CodeTextEdit()
        self.code_display.setReadOnly(True)
        self.code_display.setFont(QFont('Consolas', 11))
        self.code_display.setMinimumSize(700, 450)
        self.code_display.setStyleSheet(_get_code_style())
        self.viewLayout.addWidget(self.code_display)

        self.all_codes_widget = QWidget()
        self.all_codes_layout = QVBoxLayout(self.all_codes_widget)
        self.all_codes_layout.setContentsMargins(0, 0, 0, 0)
        self.all_codes_layout.setSpacing(12)
        
        self.all_codes_scroll = QScrollArea()
        self.all_codes_scroll.setWidgetResizable(True)
        self.all_codes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.all_codes_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.all_codes_scroll.setWidget(self.all_codes_widget)
        self.all_codes_scroll.setMinimumSize(700, 450)
        self.all_codes_scroll.hide()
        
        self.viewLayout.addWidget(self.all_codes_scroll)

        info_layout = QHBoxLayout()
        self.language_label = CaptionLabel('\u8bed\u8a00: -')
        info_layout.addWidget(self.language_label)

        info_layout.addStretch()

        self.lines_label = CaptionLabel('\u884c\u6570: 0')
        info_layout.addWidget(self.lines_label)

        self.chars_label = CaptionLabel('\u5b57\u7b26\u6570: 0')
        info_layout.addWidget(self.chars_label)
        
        self.copy_btn = PushButton('\u590d\u5236\u5f53\u524d')
        self.copy_btn.setFixedHeight(28)
        self.copy_btn.clicked.connect(self._copy_code)
        info_layout.addWidget(self.copy_btn)
        
        self.copy_all_btn = PushButton('\u590d\u5236\u5168\u90e8')
        self.copy_all_btn.setFixedHeight(28)
        self.copy_all_btn.clicked.connect(self._copy_all_codes)
        info_layout.addWidget(self.copy_all_btn)

        self.viewLayout.addLayout(info_layout)

        self.yesButton.setText('\u5173\u95ed')
        self.cancelButton.hide()

    def _connect_signals(self):
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme: Theme):
        """主题变化时更新样式"""
        self.code_display.setStyleSheet(_get_code_style())
        
        for code_edit in self._code_edits:
            code_edit.setStyleSheet(_get_code_style())
        
        for header in self._headers:
            header.setStyleSheet(_get_header_style())

    def _show_code(self, index: int):
        """显示单个代码块"""
        if not self._code_blocks or index < 0 or index >= len(self._code_blocks):
            return

        self._current_index = index
        code_block = self._code_blocks[index]

        self.code_display.show()
        self.all_codes_scroll.hide()
        
        self.pivot.setCurrentItem(str(index))

        self.code_display.setPlainText(code_block.content)

        self._highlighters.clear()
        
        highlighter = HighlighterFactory.create(code_block.language, self.code_display.document())
        self._highlighters.append(highlighter)

        self.language_label.setText(f'\u8bed\u8a00: {code_block.language}')
        lines = code_block.content.count('\n') + 1
        self.lines_label.setText(f'\u884c\u6570: {lines}')
        self.chars_label.setText(f'\u5b57\u7b26\u6570: {len(code_block.content)}')

    def _show_all_codes(self):
        """显示所有代码块"""
        self.code_display.hide()
        self.all_codes_scroll.show()
        
        self.pivot.setCurrentItem('all')
        
        while self.all_codes_layout.count():
            item = self.all_codes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._code_edits.clear()
        self._headers.clear()
        
        self._highlighters.clear()
        
        total_lines = 0
        total_chars = 0
        
        for i, code_block in enumerate(self._code_blocks):
            header = QLabel(f'\u4ee3\u7801\u5757 {i + 1}: {code_block.language}')
            header.setFont(QFont('Microsoft YaHei', 11, QFont.Bold))
            header.setStyleSheet(_get_header_style())
            self.all_codes_layout.addWidget(header)
            self._headers.append(header)
            
            code_edit = CodeTextEdit()
            code_edit.setReadOnly(True)
            code_edit.setFont(QFont('Consolas', 10))
            code_edit.setPlainText(code_block.content)
            code_edit.setStyleSheet(_get_code_style())
            
            lines = code_block.content.count('\n') + 1
            height = min(max(lines * 20 + 30, 100), 400)
            code_edit.setFixedHeight(height)
            
            highlighter = HighlighterFactory.create(code_block.language, code_edit.document())
            self._highlighters.append(highlighter)
            
            self.all_codes_layout.addWidget(code_edit)
            self._code_edits.append(code_edit)
            
            total_lines += lines
            total_chars += len(code_block.content)
        
        self.all_codes_layout.addStretch()
        
        self.language_label.setText(f'\u5171 {len(self._code_blocks)} \u4e2a\u4ee3\u7801\u5757')
        self.lines_label.setText(f'\u603b\u884c\u6570: {total_lines}')
        self.chars_label.setText(f'\u603b\u5b57\u7b26\u6570: {total_chars}')

    def _copy_code(self):
        """复制当前代码块"""
        if not self._code_blocks:
            return

        code_block = self._code_blocks[self._current_index]
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(code_block.content)

        self._show_copy_success('\u5f53\u524d\u4ee3\u7801\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f')

    def _copy_all_codes(self):
        """复制所有代码块"""
        if not self._code_blocks:
            return
        
        all_code = []
        for i, code_block in enumerate(self._code_blocks):
            all_code.append(f'// ===== \u4ee3\u7801\u5757 {i + 1}: {code_block.language} =====')
            all_code.append(code_block.content)
            all_code.append('')
        
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText('\n'.join(all_code))
        
        self._show_copy_success('\u6240\u6709\u4ee3\u7801\u5df2\u590d\u5236\u5230\u526a\u8d34\u677f')

    def _show_copy_success(self, message: str):
        """显示复制成功提示"""
        from qfluentwidgets import InfoBar, InfoBarPosition
        InfoBar.success(
            title='\u6210\u529f',
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )