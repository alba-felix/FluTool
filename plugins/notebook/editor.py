"""随手记编辑器 - 文本编辑区域"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PyQt5.QtGui import QColor, QKeyEvent, QPainter
from qfluentwidgets import isDarkTheme, qconfig

from .highlighter import NotebookHighlighter


class LineNumberArea(QWidget):
    """行号显示区域"""
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.update_style()
    
    def update_style(self):
        """更新样式"""
        dark = isDarkTheme()
        if dark:
            self.setStyleSheet("background-color: #2d2d2d; border-right: 1px solid #3d3d3d;")
        else:
            self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")
    
    def paintEvent(self, event):
        """绘制行号"""
        painter = QPainter(self)
        dark = isDarkTheme()
        
        bg_color = QColor("#2d2d2d") if dark else QColor("#f0f0f0")
        painter.fillRect(event.rect(), bg_color)
        
        text_color = QColor("#ffffff") if dark else QColor("#333333")
        painter.setPen(text_color)
        
        painter.setFont(self.editor.font())
        
        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()).top())
        bottom = top + round(self.editor.blockBoundingRect(block).height())
        
        line_number_width = self.width() - 5
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, line_number_width, 
                               self.editor.fontMetrics().height(),
                               Qt.AlignRight | Qt.AlignTop, number)
            
            block = block.next()
            top = bottom
            bottom = top + round(self.editor.blockBoundingRect(block).height())
            block_number += 1


class NotebookEditor(QWidget):
    """编辑器组件"""
    
    # 自定义信号
    enter_pressed = pyqtSignal()  # Enter 键按下
    alt_enter_pressed = pyqtSignal()  # Alt+Enter 按下
    save_signal = pyqtSignal()  # Ctrl+S

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

        # 文本编辑器
        self._editor = CustomTextEdit(self)
        self._editor.setPlaceholderText("开始输入笔记内容...")
        self._editor.setObjectName("noteTextEdit")
        # 连接信号
        self._editor.enter_pressed.connect(self.enter_pressed.emit)
        self._editor.alt_enter_pressed.connect(self.alt_enter_pressed.emit)
        self._editor.save_signal.connect(self.save_signal.emit)
        
        # 设置样式
        self._update_editor_style()
        
        # 移除聚焦时的边框
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
        """设置字体大小"""
        font = self._editor.font()
        font.setPointSize(size)
        self._editor.setFont(font)


class CustomTextEdit(QPlainTextEdit):
    """自定义 TextEdit，支持快捷键和行号"""
    
    enter_pressed = pyqtSignal()
    alt_enter_pressed = pyqtSignal()
    save_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)

        self.update_line_number_area_width()

        self.highlighter = NotebookHighlighter(self.document())
    
    def line_number_area_width(self):
        """计算行号区域宽度"""
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        return 20 + self.fontMetrics().horizontalAdvance('9') * max(3, digits)
    
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
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_S:
                self.save_signal.emit()
                event.accept()
                return

        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() == Qt.AltModifier:
                self.alt_enter_pressed.emit()
                event.accept()
                return
            else:
                super().keyPressEvent(event)
                return

        super().keyPressEvent(event)
