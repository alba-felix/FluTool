import difflib
from pathlib import Path
from typing import Optional, Tuple, List
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QSize, QEvent
from PyQt5.QtGui import QColor, QPalette, QPixmap, QPainter, QCursor, QIcon, QTextCursor, QTextCharFormat, QTextFormat, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QColorDialog,
    QGridLayout, QScrollArea, QFrame, QTabWidget,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox, QToolTip,
    QMenu, QAction, QApplication, QFileDialog, QTextEdit, QCheckBox,
    QComboBox, QStatusBar, QPlainTextEdit, QWidgetAction
)
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, ScrollArea, PrimaryPushButton, ToolButton,
    CardWidget, SpinBox, isDarkTheme, ComboBox, CheckBox, BodyLabel,
    FluentStyleSheet, IndeterminateProgressBar
)
from core import PluginInterface
from ui import CustomFluentIcon as CFIF


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
        
        # 背景色
        bg_color = QColor("#2d2d2d") if dark else QColor("#f0f0f0")
        painter.fillRect(event.rect(), bg_color)
        
        # 文字颜色
        text_color = QColor("#ffffff") if dark else QColor("#333333")
        painter.setPen(text_color)
        
        # 使用编辑器的字体
        painter.setFont(self.editor.font())
        
        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.editor.blockBoundingGeometry(block).translated(
            self.editor.contentOffset()).top())
        bottom = top + round(self.editor.blockBoundingRect(block).height())
        
        # 计算行号区域的有效宽度
        line_number_width = self.width() - 5
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                # 右对齐绘制行号
                painter.drawText(0, top, line_number_width, 
                               self.editor.fontMetrics().height(),
                               Qt.AlignRight | Qt.AlignTop, number)
            
            block = block.next()
            top = bottom
            bottom = top + round(self.editor.blockBoundingRect(block).height())
            block_number += 1


class CodeEditor(QPlainTextEdit):
    """带行号的代码编辑器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self._diff_selections = []  # 存储差异高亮
        
        # 连接信号
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        # 初始化
        self.update_line_number_area_width()
        
        # 设置等宽字体
        font = self.font()
        font.setFamily('Consolas')
        font.setPointSize(14)
        self.setFont(font)
    
    def set_diff_selections(self, selections):
        """设置差异高亮（不覆盖当前行高亮）"""
        self._diff_selections = selections
        self.highlight_current_line()
    
    def clear_diff_selections(self):
        """清除差异高亮"""
        self._diff_selections = []
    
    def line_number_area_width(self):
        """计算行号区域宽度"""
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        # 根据实际行数动态计算宽度，最少显示 3 个数字宽度
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
    
    def highlight_current_line(self):
        """高亮当前行（同时保留差异高亮）"""
        extra_selections = list(self._diff_selections)  # 先添加差异高亮
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#404040") if isDarkTheme() else QColor("#e8f2ff")
            
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)


class TextCompareWidget(QWidget):
    """文本对比插件界面"""
    PLUGIN_ID = "text_compare"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.diff_results = []
        self.current_diff_index = -1
        self.char_level_diffs = []  # 存储字符级差异
        self.init_ui()
        self.setup_style()
        
        # 监听主题变化
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self.on_theme_changed)
    
    def on_theme_changed(self, theme):
        """主题变化时重新设置样式"""
        self.setup_style()
        # 重新高亮差异
        if self.diff_results:
            self.highlight_differences()

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建最外层滚动区域
        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setObjectName("textCompareScrollArea")

        # 创建内容容器
        self._content_widget = QWidget()
        self._content_widget.setObjectName("textCompareContent")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        # 工具栏
        toolbar = self.create_toolbar()
        self._content_layout.addWidget(toolbar)

        # 分割器（两个文本编辑区域）
        splitter = self.create_text_areas()
        self._content_layout.addWidget(splitter, 1)

        # 状态栏
        self._status_bar = self.create_status_bar()
        self._content_layout.addWidget(self._status_bar)

        # 将内容容器添加到滚动区域
        self._scroll_area.setWidget(self._content_widget)

        main_layout.addWidget(self._scroll_area)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("textCompareToolbar")
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_layout.setSpacing(8)

        # 对比按钮
        self._compare_btn = PrimaryPushButton(FIF.SEARCH, "对比")
        self._compare_btn.clicked.connect(self.compare_texts)
        toolbar_layout.addWidget(self._compare_btn)

        # 清空按钮
        self._clear_btn = PushButton(FIF.DELETE, "清空")
        self._clear_btn.clicked.connect(self.clear_texts)
        toolbar_layout.addWidget(self._clear_btn)

        # 交换按钮
        self._swap_btn = PushButton(FIF.SYNC, "交换")
        self._swap_btn.clicked.connect(self.swap_texts)
        toolbar_layout.addWidget(self._swap_btn)

        # 复制差异按钮
        self._copy_diff_btn = PushButton(FIF.COPY, "复制差异")
        self._copy_diff_btn.clicked.connect(self.copy_differences)
        toolbar_layout.addWidget(self._copy_diff_btn)

        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator)

        # 上一处差异
        self._prev_diff_btn = PushButton(FIF.UP, "上一处")
        self._prev_diff_btn.clicked.connect(self.prev_diff)
        toolbar_layout.addWidget(self._prev_diff_btn)

        # 下一处差异
        self._next_diff_btn = PushButton(FIF.DOWN, "下一处")
        self._next_diff_btn.clicked.connect(self.next_diff)
        toolbar_layout.addWidget(self._next_diff_btn)

        # 分隔符
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator2)

        # 实时对比复选框
        self._realtime_check = CheckBox("实时对比")
        self._realtime_check.setChecked(True)
        toolbar_layout.addWidget(self._realtime_check)

        # 忽略空白复选框
        self._ignore_whitespace_check = CheckBox("忽略空白")
        self._ignore_whitespace_check.setChecked(True)
        toolbar_layout.addWidget(self._ignore_whitespace_check)

        # 分隔符
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator3)

        # 对比模式下拉框
        toolbar_layout.addWidget(BodyLabel(""))
        self._diff_mode_combo = ComboBox()
        self._diff_mode_combo.addItems(["智能对比", "仅字符", "仅整行"])
        self._diff_mode_combo.setCurrentIndex(0)
        toolbar_layout.addWidget(self._diff_mode_combo)

        # 显示模式下拉框
        toolbar_layout.addWidget(BodyLabel(""))
        self._display_mode_combo = ComboBox()
        self._display_mode_combo.addItems(["并排对比", "上下对比"])
        self._display_mode_combo.setCurrentIndex(0)
        toolbar_layout.addWidget(self._display_mode_combo)

        toolbar_layout.addStretch()

        return toolbar_widget

    def create_text_areas(self):
        """创建文本编辑区域"""
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("textCompareSplitter")

        # 左侧文本编辑器
        left_widget = QWidget()
        left_widget.setObjectName("leftTextWidget")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        left_label = BodyLabel("原文本")
        left_layout.addWidget(left_label)

        self._left_text = CodeEditor()
        self._left_text.setObjectName("leftTextEdit")
        self._left_text.setPlaceholderText("请输入或粘贴原文本...")
        self._left_text.textChanged.connect(self.on_text_changed)
        left_layout.addWidget(self._left_text)

        splitter.addWidget(left_widget)

        # 右侧文本编辑器
        right_widget = QWidget()
        right_widget.setObjectName("rightTextWidget")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        right_label = BodyLabel("新文本")
        right_layout.addWidget(right_label)

        self._right_text = CodeEditor()
        self._right_text.setObjectName("rightTextEdit")
        self._right_text.setPlaceholderText("请输入或粘贴新文本...")
        self._right_text.textChanged.connect(self.on_text_changed)
        right_layout.addWidget(self._right_text)

        splitter.addWidget(right_widget)

        # 设置左右各占一半（使用 1:1 的拉伸因子）
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # 延迟设置分割比例，确保在窗口显示后生效
        QTimer.singleShot(100, lambda: splitter.setSizes([1, 1]))

        return splitter

    def create_status_bar(self):
        """创建状态栏"""
        status_widget = QWidget()
        status_widget.setObjectName("textCompareStatus")
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self._status_label = BodyLabel("就绪")
        status_layout.addWidget(self._status_label)

        status_layout.addStretch()

        self._diff_count_label = BodyLabel("差异：0 处")
        status_layout.addWidget(self._diff_count_label)

        return status_widget

    def setup_style(self):
        """设置样式（支持主题）"""
        dark = isDarkTheme()
        
        if dark:
            bg_color = "#1e1e1e"
            text_color = "#ffffff"
            border_color = "#3d3d3d"
            editor_bg = "#252526"
        else:
            bg_color = "#f5f5f5"
            text_color = "#333333"
            border_color = "#d9d9d9"
            editor_bg = "#ffffff"

        # 工具栏
        toolbar = self.findChild(QWidget, "textCompareToolbar")
        if toolbar:
            toolbar.setStyleSheet(f"""
                QWidget#textCompareToolbar {{
                    background-color: {bg_color};
                    border-bottom: 1px solid {border_color};
                }}
            """)

        # 滚动区域
        self._scroll_area.setStyleSheet(f"""
            ScrollArea#textCompareScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea#textCompareScrollArea > QWidget {{
                background-color: {bg_color};
            }}
        """)

        # 内容容器
        self._content_widget.setStyleSheet(f"QWidget#textCompareContent{{background-color: {bg_color};}}")

        # 分割器
        splitter = self.findChild(QSplitter, "textCompareSplitter")
        if splitter:
            splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {border_color};
                    width: 1px;
                }}
            """)
            # 设置左右各占一半
            total_width = splitter.width()
            if total_width > 0:
                half_width = total_width // 2
                splitter.setSizes([half_width, half_width])
            else:
                # 如果宽度为 0，延迟设置
                QTimer.singleShot(200, lambda: splitter.setSizes([400, 400]))

        # 文本编辑器
        for text_edit in [self._left_text, self._right_text]:
            text_edit.setStyleSheet(f"""
                QPlainTextEdit {{
                    background-color: {editor_bg};
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    padding: 4px;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    font-size: 14px;
                }}
            """)
            # 更新行号区域样式
            if hasattr(text_edit, 'line_number_area'):
                text_edit.line_number_area.update_style()

        # 状态栏
        status = self.findChild(QWidget, "textCompareStatus")
        if status:
            status.setStyleSheet(f"""
                QWidget#textCompareStatus {{
                    background-color: {bg_color};
                    border-top: 1px solid {border_color};
                }}
            """)

    def on_text_changed(self):
        """文本变化时触发"""
        if self._realtime_check.isChecked():
            # 只有两侧都有内容时才触发对比
            left_text = self._left_text.toPlainText()
            right_text = self._right_text.toPlainText()
            
            if left_text.strip() and right_text.strip():
                QTimer.singleShot(1000, self.compare_texts)  # 延迟 1000ms 执行对比

    def compare_texts(self):
        """对比文本"""
        left_text = self._left_text.toPlainText()
        right_text = self._right_text.toPlainText()

        if not left_text and not right_text:
            self._status_label.setText("请输入文本")
            return

        try:
            self._status_label.setText("正在对比...")
            
            # 获取对比模式
            diff_mode = self._diff_mode_combo.currentText()
            ignore_whitespace = self._ignore_whitespace_check.isChecked()
            
            # 预处理文本（忽略空白）
            if ignore_whitespace:
                left_text_processed = self.normalize_whitespace(left_text)
                right_text_processed = self.normalize_whitespace(right_text)
            else:
                left_text_processed = left_text
                right_text_processed = right_text
            
            # 执行对比
            if diff_mode == "仅字符":
                self.diff_results = self.compare_by_char(left_text_processed, right_text_processed)
                self.char_level_diffs = self.get_char_level_highlights(left_text_processed, right_text_processed)
            elif diff_mode == "仅整行":
                self.diff_results = self.compare_by_line(left_text_processed, right_text_processed)
                self.char_level_diffs = []
            else:  # 智能对比
                self.diff_results = self.compare_smart(left_text_processed, right_text_processed)
                # 智能对比时获取字符级差异
                self.char_level_diffs = self.get_char_level_highlights_smart(
                    left_text_processed, right_text_processed
                )
            
            # 更新状态 - 修复这里的问题
            if self.diff_results:
                # 根据不同的数据结构计算差异数
                if isinstance(self.diff_results[0], dict):
                    diff_count = len([r for r in self.diff_results if r.get('tag') != 'equal'])
                else:
                    diff_count = len([r for r in self.diff_results if r[0] != 'equal'])
            else:
                diff_count = 0
                
            self._diff_count_label.setText(f"差异：{diff_count} 处")
            self._status_label.setText(f"对比完成，发现 {diff_count} 处差异")
            
            # 高亮差异
            self.highlight_differences()
            
            InfoBar.success(
                title="对比完成",
                content=f"发现 {diff_count} 处差异",
                parent=self,
                duration=2000
            )
        except Exception as e:
            import traceback
            error_msg = f"{type(e).__name__}: {str(e)}"
            traceback_str = traceback.format_exc()
            
            # 打印详细错误到控制台
            print(f"对比失败详细信息:")
            print(traceback_str)
            
            InfoBar.error(
                title="对比失败",
                content=error_msg if str(e) else f"{type(e).__name__}",
                parent=self,
                duration=3000
            )
            self._status_label.setText(f"对比失败: {error_msg}")
    
    def normalize_whitespace(self, text: str) -> str:
        """标准化空白字符"""
        import re
        # 将多个空白字符替换为单个空格
        text = re.sub(r'[ \t]+', ' ', text)
        # 移除行首行尾空白
        lines = [line.strip() for line in text.splitlines()]
        return '\n'.join(lines)

    def compare_by_char(self, text1: str, text2: str) -> List:
        """按字符对比 - 使用 difflib 优化"""
        # 使用 autojunk=False 提高对比精度
        differ = difflib.SequenceMatcher(None, text1, text2, autojunk=False)
        
        results = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            results.append({
                'tag': tag,
                'left_start': i1,
                'left_end': i2,
                'right_start': j1,
                'right_end': j2,
                'type': 'char',
                'left_text': text1[i1:i2] if i1 < len(text1) else '',
                'right_text': text2[j1:j2] if j1 < len(text2) else ''
            })
        return results

    def compare_by_line(self, text1: str, text2: str) -> List:
        """按行对比 - 使用 difflib.unified_diff 风格"""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
        # 使用 SequenceMatcher 进行精确对比
        differ = difflib.SequenceMatcher(None, lines1, lines2, autojunk=False)
        
        results = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            results.append({
                'tag': tag,
                'left_start': i1,
                'left_end': i2,
                'right_start': j1,
                'right_end': j2,
                'type': 'line',
                'left_lines': lines1[i1:i2] if i1 < len(lines1) else [],
                'right_lines': lines2[j1:j2] if j1 < len(lines2) else []
            })
        return results

    def compare_smart(self, text1: str, text2: str) -> List:
        """智能对比 - 使用 difflib.Differ 进行更精确的对比"""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
        # 使用 difflib.Differ 进行更详细的对比
        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))
        
        results = []
        left_line = 0
        right_line = 0
        
        i = 0
        while i < len(diff):
            line = diff[i]
            marker = line[0] if line else ' '
            
            if marker == ' ':
                # 相同行
                results.append({
                    'tag': 'equal',
                    'left_start': left_line,
                    'left_end': left_line + 1,
                    'right_start': right_line,
                    'right_end': right_line + 1,
                    'type': 'line',
                    'left_lines': [lines1[left_line]] if left_line < len(lines1) else [],
                    'right_lines': [lines2[right_line]] if right_line < len(lines2) else []
                })
                left_line += 1
                right_line += 1
            elif marker == '-':
                # 删除行
                results.append({
                    'tag': 'delete',
                    'left_start': left_line,
                    'left_end': left_line + 1,
                    'right_start': -1,
                    'right_end': -1,
                    'type': 'line',
                    'left_lines': [lines1[left_line]] if left_line < len(lines1) else [],
                    'right_lines': []
                })
                left_line += 1
            elif marker == '+':
                # 插入行
                results.append({
                    'tag': 'insert',
                    'left_start': -1,
                    'left_end': -1,
                    'right_start': right_line,
                    'right_end': right_line + 1,
                    'type': 'line',
                    'left_lines': [],
                    'right_lines': [lines2[right_line]] if right_line < len(lines2) else []
                })
                right_line += 1
            elif marker == '?':
                # 差异细节（跳过，由前一行处理）
                pass
            
            i += 1
        
        return results
    
    def get_char_level_highlights(self, text1: str, text2: str) -> dict:
        """获取字符级高亮信息"""
        differ = difflib.SequenceMatcher(None, text1, text2, autojunk=False)
        
        left_highlights = []
        right_highlights = []
        
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == 'delete':
                left_highlights.append({
                    'start': i1,
                    'end': i2,
                    'type': 'delete'
                })
            elif tag == 'insert':
                right_highlights.append({
                    'start': j1,
                    'end': j2,
                    'type': 'insert'
                })
            elif tag == 'replace':
                left_highlights.append({
                    'start': i1,
                    'end': i2,
                    'type': 'replace'
                })
                right_highlights.append({
                    'start': j1,
                    'end': j2,
                    'type': 'replace'
                })
        
        return {
            'left': left_highlights,
            'right': right_highlights
        }
    
    def get_char_level_highlights_smart(self, text1: str, text2: str) -> dict:
        """智能模式下的字符级高亮"""
        lines1 = text1.splitlines(keepends=True)
        lines2 = text2.splitlines(keepends=True)
        
        left_highlights = []
        right_highlights = []
        
        line_differ = difflib.SequenceMatcher(None, lines1, lines2, autojunk=False)
        
        left_pos = 0
        right_pos = 0
        
        for tag, i1, i2, j1, j2 in line_differ.get_opcodes():
            if tag == 'equal':
                # 相同的行，移动位置
                for i in range(i1, i2):
                    if i < len(lines1):
                        left_pos += len(lines1[i])
                for j in range(j1, j2):
                    if j < len(lines2):
                        right_pos += len(lines2[j])
                    
            elif tag == 'replace':
                # 对替换的行做进一步的字符级对比
                left_block_start = left_pos
                right_block_start = right_pos
                
                # 获取被替换的块
                left_block = ''.join(lines1[i1:i2]) if i1 < len(lines1) else ''
                right_block = ''.join(lines2[j1:j2]) if j1 < len(lines2) else ''
                
                # 更新位置
                left_pos += len(left_block)
                right_pos += len(right_block)
                
                # 如果块不为空，做字符级对比
                if left_block or right_block:
                    char_differ = difflib.SequenceMatcher(None, left_block, right_block, autojunk=False)
                    
                    for char_tag, ci1, ci2, cj1, cj2 in char_differ.get_opcodes():
                        if char_tag == 'delete':
                            left_highlights.append({
                                'start': left_block_start + ci1,
                                'end': left_block_start + ci2,
                                'type': 'delete'
                            })
                        elif char_tag == 'insert':
                            right_highlights.append({
                                'start': right_block_start + cj1,
                                'end': right_block_start + cj2,
                                'type': 'insert'
                            })
                        elif char_tag == 'replace':
                            left_highlights.append({
                                'start': left_block_start + ci1,
                                'end': left_block_start + ci2,
                                'type': 'replace'
                            })
                            right_highlights.append({
                                'start': right_block_start + cj1,
                                'end': right_block_start + cj2,
                                'type': 'replace'
                            })
                    
            elif tag == 'delete':
                # 删除的行
                left_block_start = left_pos
                left_block = ''.join(lines1[i1:i2]) if i1 < len(lines1) else ''
                left_pos += len(left_block)
                
                if left_block:
                    left_highlights.append({
                        'start': left_block_start,
                        'end': left_pos,
                        'type': 'delete'
                    })
                    
            elif tag == 'insert':
                # 插入的行
                right_block_start = right_pos
                right_block = ''.join(lines2[j1:j2]) if j1 < len(lines2) else ''
                right_pos += len(right_block)
                
                if right_block:
                    right_highlights.append({
                        'start': right_block_start,
                        'end': right_pos,
                        'type': 'insert'
                    })
        
        return {
            'left': left_highlights,
            'right': right_highlights
        }

    def highlight_differences(self):
        """高亮差异 - 优化版本，支持字符级精确高亮"""
        dark = isDarkTheme()
        
        # 定义颜色方案
        if dark:
            colors = {
                'delete_bg': QColor("#5e2e2e"),      # 深红色背景
                'delete_text': QColor("#ff6b6b"),    # 红色文字
                'insert_bg': QColor("#2e5e2e"),      # 深绿色背景
                'insert_text': QColor("#6bff6b"),    # 绿色文字
                'replace_bg': QColor("#5e4e2e"),     # 深橙色背景
                'replace_text': QColor("#ffb86b"),   # 橙色文字
            }
        else:
            colors = {
                'delete_bg': QColor("#ffebe9"),      # 浅红色背景
                'delete_text': QColor("#d73a49"),    # 红色文字
                'insert_bg': QColor("#e6ffed"),      # 浅绿色背景
                'insert_text': QColor("#28a745"),    # 绿色文字
                'replace_bg': QColor("#fff8dc"),     # 浅黄色背景
                'replace_text': QColor("#e36209"),   # 橙色文字
            }
        
        # 清除之前的差异高亮（使用新方法）
        self._left_text.clear_diff_selections()
        self._right_text.clear_diff_selections()
        
        # 调试信息
        print(f"char_level_diffs: {bool(self.char_level_diffs)}")
        if self.char_level_diffs:
            print(f"Left highlights: {len(self.char_level_diffs.get('left', []))}")
            print(f"Right highlights: {len(self.char_level_diffs.get('right', []))}")
            print(f"Sample left: {self.char_level_diffs.get('left', [])[:3]}")
            print(f"Sample right: {self.char_level_diffs.get('right', [])[:3]}")
        
        # 如果有字符级差异信息，使用字符级高亮
        if self.char_level_diffs:
            print("使用字符级高亮")
            self.apply_char_level_highlights(colors)
        else:
            # 否则使用行级高亮
            print("使用行级高亮")
            self.apply_line_level_highlights(colors)
    
    def apply_char_level_highlights(self, colors: dict):
        """应用字符级高亮"""
        left_highlights = self.char_level_diffs.get('left', [])
        right_highlights = self.char_level_diffs.get('right', [])
        
        left_selections = []
        right_selections = []
        
        # 左侧高亮
        for highlight in left_highlights:
            cursor = QTextCursor(self._left_text.document())
            cursor.setPosition(highlight['start'])
            cursor.setPosition(highlight['end'], QTextCursor.KeepAnchor)
            
            if cursor.hasSelection():
                selection = QTextEdit.ExtraSelection()
                diff_type = highlight['type']
                
                if diff_type == 'delete':
                    selection.format.setBackground(colors['delete_bg'])
                    selection.format.setForeground(colors['delete_text'])
                elif diff_type == 'replace':
                    selection.format.setBackground(colors['replace_bg'])
                    selection.format.setForeground(colors['replace_text'])
                
                selection.cursor = cursor
                left_selections.append(selection)
        
        # 右侧高亮
        for highlight in right_highlights:
            cursor = QTextCursor(self._right_text.document())
            cursor.setPosition(highlight['start'])
            cursor.setPosition(highlight['end'], QTextCursor.KeepAnchor)
            
            if cursor.hasSelection():
                selection = QTextEdit.ExtraSelection()
                diff_type = highlight['type']
                
                if diff_type == 'insert':
                    selection.format.setBackground(colors['insert_bg'])
                    selection.format.setForeground(colors['insert_text'])
                elif diff_type == 'replace':
                    selection.format.setBackground(colors['replace_bg'])
                    selection.format.setForeground(colors['replace_text'])
                
                selection.cursor = cursor
                right_selections.append(selection)
        
        # 应用所有高亮（使用新方法，保留当前行高亮）
        self._left_text.set_diff_selections(left_selections)
        self._right_text.set_diff_selections(right_selections)
    
    def apply_line_level_highlights(self, colors: dict):
        """应用行级高亮"""
        left_selections = []
        right_selections = []
        
        for diff in self.diff_results:
            tag = diff.get('tag')
            diff_type = diff.get('type', 'line')
            
            if tag == 'equal':
                continue
            
            if tag in ['delete', 'replace']:
                # 高亮左侧
                start_line = diff.get('left_start', 0)
                end_line = diff.get('left_end', 0)
                
                for line_num in range(start_line, end_line):
                    selection = self.create_line_highlight_selection(
                        self._left_text, 
                        line_num,
                        colors['delete_bg'] if tag == 'delete' else colors['replace_bg']
                    )
                    if selection:
                        left_selections.append(selection)
            
            if tag in ['insert', 'replace']:
                # 高亮右侧
                start_line = diff.get('right_start', 0)
                end_line = diff.get('right_end', 0)
                
                for line_num in range(start_line, end_line):
                    selection = self.create_line_highlight_selection(
                        self._right_text,
                        line_num,
                        colors['insert_bg'] if tag == 'insert' else colors['replace_bg']
                    )
                    if selection:
                        right_selections.append(selection)
        
        # 应用高亮（使用新方法，保留当前行高亮）
        self._left_text.set_diff_selections(left_selections)
        self._right_text.set_diff_selections(right_selections)
    
    def create_line_highlight_selection(self, text_edit, line_num: int, color: QColor):
        """创建行高亮选择"""
        try:
            cursor = text_edit.textCursor()
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down, QTextCursor.MoveAnchor, line_num)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
            
            if cursor.hasSelection() or cursor.block().text():
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(color)
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                selection.cursor = cursor
                return selection
        except:
            pass
        return None

    def clear_texts(self):
        """清空文本"""
        self._left_text.clear()
        self._right_text.clear()
        self.diff_results = []
        self.char_level_diffs = []
        self.current_diff_index = -1
        # 清除差异高亮
        self._left_text.clear_diff_selections()
        self._right_text.clear_diff_selections()
        self._diff_count_label.setText("差异：0 处")
        self._status_label.setText("已清空")

    def swap_texts(self):
        """交换文本"""
        left_text = self._left_text.toPlainText()
        right_text = self._right_text.toPlainText()
        
        self._left_text.setPlainText(right_text)
        self._right_text.setPlainText(left_text)
        
        # 如果有差异结果，重新对比
        if self.diff_results:
            self.compare_texts()
        
        self._status_label.setText("已交换文本")

    def copy_differences(self):
        """复制差异到剪贴板"""
        if not self.diff_results:
            InfoBar.warning(
                title="无差异",
                content="请先对比文本",
                parent=self,
                duration=2000
            )
            return
        
        # 生成差异报告
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("文本差异对比报告")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        diff_count = len([r for r in self.diff_results if r.get('tag') != 'equal'])
        report_lines.append(f"总计发现 {diff_count} 处差异")
        report_lines.append("")
        
        for i, diff in enumerate(self.diff_results, 1):
            tag = diff.get('tag')
            if tag == 'equal':
                continue
            
            report_lines.append(f"差异 #{i}:")
            report_lines.append(f"类型: {tag}")
            
            if tag in ['delete', 'replace']:
                left_start = diff.get('left_start', 0)
                left_end = diff.get('left_end', 0)
                report_lines.append(f"原文本位置: 行 {left_start + 1} - {left_end}")
            
            if tag in ['insert', 'replace']:
                right_start = diff.get('right_start', 0)
                right_end = diff.get('right_end', 0)
                report_lines.append(f"新文本位置: 行 {right_start + 1} - {right_end}")
            
            report_lines.append("-" * 60)
        
        report = "\n".join(report_lines)
        
        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setText(report)
        
        InfoBar.success(
            title="已复制",
            content="差异报告已复制到剪贴板",
            parent=self,
            duration=2000
        )

    def prev_diff(self):
        """上一处差异"""
        if not self.diff_results:
            InfoBar.warning(
                title="无差异",
                content="请先对比文本",
                parent=self,
                duration=2000
            )
            return
        
        # 过滤出非 equal 的差异
        diff_indices = [i for i, diff in enumerate(self.diff_results) if diff.get('tag') != 'equal']
        
        if not diff_indices:
            InfoBar.info(
                title="提示",
                content="没有差异",
                parent=self,
                duration=2000
            )
            return
        
        # 找到当前差异的前一个
        if self.current_diff_index == -1 or self.current_diff_index not in diff_indices:
            # 如果没有当前索引，从最后一个开始
            self.current_diff_index = diff_indices[-1]
        else:
            # 找到当前索引在diff_indices中的位置
            current_pos = diff_indices.index(self.current_diff_index)
            prev_pos = (current_pos - 1) % len(diff_indices)
            self.current_diff_index = diff_indices[prev_pos]
        
        # 跳转到差异位置
        self.jump_to_difference(self.current_diff_index)
        
        current_pos = diff_indices.index(self.current_diff_index)
        self._status_label.setText(f"第 {current_pos + 1}/{len(diff_indices)} 处差异")

    def next_diff(self):
        """下一处差异"""
        if not self.diff_results:
            InfoBar.warning(
                title="无差异",
                content="请先对比文本",
                parent=self,
                duration=2000
            )
            return
        
        # 过滤出非 equal 的差异
        diff_indices = [i for i, diff in enumerate(self.diff_results) if diff.get('tag') != 'equal']
        
        if not diff_indices:
            InfoBar.info(
                title="提示",
                content="没有差异",
                parent=self,
                duration=2000
            )
            return
        
        # 找到当前差异的下一个
        if self.current_diff_index == -1 or self.current_diff_index not in diff_indices:
            # 如果没有当前索引，从第一个开始
            self.current_diff_index = diff_indices[0]
        else:
            # 找到当前索引在diff_indices中的位置
            current_pos = diff_indices.index(self.current_diff_index)
            next_pos = (current_pos + 1) % len(diff_indices)
            self.current_diff_index = diff_indices[next_pos]
        
        # 跳转到差异位置
        self.jump_to_difference(self.current_diff_index)
        
        current_pos = diff_indices.index(self.current_diff_index)
        self._status_label.setText

class Plugin(PluginInterface):
    """文本对比插件"""
    PLUGIN_ID = "text_compare"
    PLUGIN_NAME = "文本对比"
    PLUGIN_ICON = CFIF.DIFFER
    PLUGIN_PRIORITY = 17

    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return TextCompareWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        pass
