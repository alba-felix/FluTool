"""随手记编辑器 - 文本编辑区域 - 性能优化版本"""

from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt5.QtGui import QColor, QKeyEvent, QPainter, QFont, QFontMetrics
from qfluentwidgets import isDarkTheme, qconfig

from .highlighter import NotebookHighlighter


class StyleCache:
    """样式缓存"""
    _dark_bg = None
    _dark_text = None
    _light_bg = None
    _light_text = None
    
    @classmethod
    def get_colors(cls, dark: bool):
        """获取缓存的颜色"""
        if dark:
            if cls._dark_bg is None:
                cls._dark_bg = QColor("#2d2d2d")
                cls._dark_text = QColor("#ffffff")
            return cls._dark_bg, cls._dark_text
        else:
            if cls._light_bg is None:
                cls._light_bg = QColor("#f0f0f0")
                cls._light_text = QColor("#333333")
            return cls._light_bg, cls._light_text


class LineNumberArea(QWidget):
    """行号显示区域 - 性能优化版本"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self._cached_font = None
        self._cached_fm = None
        self._last_font_size = 0
        self.update_style()

    def update_style(self):
        """更新样式"""
        dark = isDarkTheme()
        if dark:
            self.setStyleSheet("background-color: #2d2d2d; border-right: 1px solid #3d3d3d;")
        else:
            self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")

    def paintEvent(self, event):
        """绘制行号 - 优化版本"""
        painter = QPainter(self)
        dark = isDarkTheme()
        
        bg_color, text_color = StyleCache.get_colors(dark)
        painter.fillRect(event.rect(), bg_color)
        painter.setPen(text_color)
        
        font = self.editor.font()
        if self._cached_font != font:
            self._cached_font = font
            self._cached_fm = QFontMetrics(font)
        fm = self._cached_fm
        
        painter.setFont(font)
        
        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()).top())
        bottom = top + round(self.editor.blockBoundingRect(block).height())
        
        line_number_width = self.width() - 5
        font_height = fm.height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, line_number_width, 
                               font_height,
                               Qt.AlignRight | Qt.AlignTop, number)
            
            block = block.next()
            top = bottom
            bottom = top + round(self.editor.blockBoundingRect(block).height())
            block_number += 1


class NotebookEditor(QWidget):
    """编辑器组件 - 性能优化版本"""
    
    enter_pressed = pyqtSignal()
    alt_enter_pressed = pyqtSignal()
    save_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notebookEditor")
        self._setup_ui()
        qconfig.themeChanged.connect(self.on_theme_changed)

    def on_theme_changed(self):
        """主题变化时更新样式"""
        self._editor.line_number_area.update_style()
        self._update_editor_style()

    def _update_editor_style(self):
        """更新编辑器样式"""
        dark = isDarkTheme()
        if dark:
            text_color = "#e6e6e6"
            placeholder_color = "#a0a0a0"
        else:
            text_color = "#333333"
            placeholder_color = "#808080"
        
        self._editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                border: none;
                padding: 10px;
                outline: none;
                color: {text_color};
            }}
            QPlainTextEdit:focus {{
                background: transparent;
                border: none;
            }}
            QPlainTextEdit:hover {{
                background: transparent;
            }}
            QPlainTextEdit #noteTextEdit {{
                background: transparent;
            }}
            QPlainTextEdit #noteTextEdit:focus {{
                background: transparent;
            }}
            QPlainTextEdit #noteTextEdit:hover {{
                background: transparent;
            }}
            QPlainTextEdit::placeholder {{
                color: {placeholder_color};
            }}
        """)

    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setObjectName("notebookEditorLayout")

        self._editor = CustomTextEdit(self)
        self._editor.setPlaceholderText("开始输入笔记内容...（按Enter保存，按Alt+Enter换行）")
        self._editor.setObjectName("noteTextEdit")
        self._editor.enter_pressed.connect(self.enter_pressed.emit)
        self._editor.alt_enter_pressed.connect(self.alt_enter_pressed.emit)
        self._editor.save_signal.connect(self.save_signal.emit)
        
        self._update_editor_style()
        self.set_font_size(13)
        self._editor.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self._editor)

    def get_content(self) -> str:
        """获取内容"""
        return self._editor.toPlainText()

    def set_content(self, content: str):
        """设置内容"""
        self._editor.setPlainText(content)

    def clear(self):
        """清空内容"""
        self._editor.clear()
        
    def set_font_family(self, family: str):
        """设置字体"""
        font = self._editor.font()
        font.setFamily(family)
        self._editor.setFont(font)
    
    def set_font_size(self, size: int):
        """设置字体大小 - 只设置内容字体，不影响行号"""
        from PyQt5.QtGui import QTextCharFormat
        
        cursor = self._editor.textCursor()
        cursor.select(cursor.Document)
        
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        cursor.mergeCharFormat(fmt)
        self._editor.setCurrentCharFormat(fmt)


class CustomTextEdit(QPlainTextEdit):
    """自定义 TextEdit，支持快捷键和行号 - 性能优化版本"""
    
    enter_pressed = pyqtSignal()
    alt_enter_pressed = pyqtSignal()
    save_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self._cached_width = None
        self._last_block_count = 0

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        self.update_line_number_area_width()
        self.highlighter = NotebookHighlighter(self.document())
        
        # 设置 Fluent 风格滚动条
        self._setup_scrollbar_style()
    
    def _setup_scrollbar_style(self):
        """设置 Fluent 风格滚动条"""
        scrollbar_style = """
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(150, 150, 150, 0.5);
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(150, 150, 150, 0.5);
                border-radius: 5px;
                min-width: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(150, 150, 150, 0.8);
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(150, 150, 150, 0.8);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(scrollbar_style)
    
    def line_number_area_width(self):
        """计算行号区域宽度 - 优化版本"""
        block_count = self.blockCount()
        if block_count == self._last_block_count and self._cached_width is not None:
            return self._cached_width
        
        self._last_block_count = block_count
        digits = 1
        max_value = max(1, block_count)
        while max_value >= 10:
            max_value //= 10
            digits += 1
        
        self._cached_width = 20 + self.fontMetrics().horizontalAdvance('9') * max(3, digits)
        return self._cached_width
    
    def update_line_number_area_width(self, _=0):
        """更新行号区域宽度"""
        width = self.line_number_area_width()
        self.setViewportMargins(width, 0, 0, 0)
        self.line_number_area.setFixedWidth(width)
    
    def update_line_number_area(self, rect, dy):
        """更新行号区域"""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()
    
    def resizeEvent(self, event):
        """调整大小事件"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
    
    def keyPressEvent(self, event: QKeyEvent):
        """处理按键事件"""
        # Ctrl+S 保存
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_S:
            self.save_signal.emit()
            event.accept()
            return

        # Enter 或 Return 键
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Alt+Enter 换行
            if event.modifiers() & Qt.AltModifier:
                # 插入换行符
                cursor = self.textCursor()
                cursor.insertText("\n")
                self.setTextCursor(cursor)
                event.accept()
                return
            else:
                # Enter 键触发保存（首次保存弹出命名对话框，或覆盖保存）
                self.enter_pressed.emit()
                event.accept()
                return

        super().keyPressEvent(event)
