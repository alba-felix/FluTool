"""DeepSeek JSON对话处理工具"""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import html as html_module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFrame,
    QListWidget, QListWidgetItem, QLabel
)
from PyQt5.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    PushButton, BodyLabel, isDarkTheme,
    FluentIcon as FIF, InfoBar, InfoBarPosition,
    LineEdit, TextEdit, CaptionLabel, ToolButton,
    ListWidget, IndeterminateProgressRing, SearchLineEdit,
    StrongBodyLabel, SubtitleLabel, MessageBoxBase
)

from plugins.text_tools.page_interface import TabPageInterface


class SearchResultPopup(MessageBoxBase):
    """搜索结果弹窗"""
    
    result_selected = pyqtSignal(object)
    
    def __init__(self, results: List[Dict[str, Any]], keyword: str, parent=None):
        super().__init__(parent)
        self.results = results
        self.keyword = keyword
        self._all_results = results.copy()
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        # 隐藏底部按钮
        self.buttonGroup.hide()
        
        # 标题栏
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        title_label = SubtitleLabel("搜索对话", self)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        close_btn = ToolButton(FIF.CLOSE, self)
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        self.viewLayout.addLayout(title_layout)
        
        # 搜索框和按钮
        search_layout = QHBoxLayout()
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("输入关键词后按Enter或点击搜索...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self._do_search)
        search_layout.addWidget(self.search_input, 1)
        
        search_btn = PushButton("搜索", self)
        search_btn.setFixedHeight(40)
        search_btn.setFixedWidth(70)
        search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(search_btn)
        
        self.viewLayout.addLayout(search_layout)
        
        # 结果计数
        self._count_label = CaptionLabel("请输入关键词后按Enter或点击搜索", self)
        self.viewLayout.addWidget(self._count_label)
        
        # 结果列表
        self.result_list = ListWidget(self)
        self.result_list.setFrameShape(ListWidget.NoFrame)
        self.result_list.itemClicked.connect(self._on_result_clicked)
        self.viewLayout.addWidget(self.result_list)
        
        self.widget.setMinimumWidth(550)
        self.widget.setMinimumHeight(400)
        self.widget.setMaximumHeight(500)
        
        self.search_input.setFocus()
    
    def _apply_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                ListWidget {
                    background-color: #2d2d2d;
                    border: none;
                }
                ListWidget::item {
                    padding: 8px 12px;
                    border-bottom: 1px solid #3d3d3d;
                }
                ListWidget::item:hover {
                    background-color: #3d3d3d;
                }
                ListWidget::item:selected {
                    background-color: #009faa;
                }
            """)
        else:
            self.setStyleSheet("""
                ListWidget {
                    background-color: #ffffff;
                    border: none;
                }
                ListWidget::item {
                    padding: 8px 12px;
                    border-bottom: 1px solid #f0f0f0;
                }
                ListWidget::item:hover {
                    background-color: #f5f5f5;
                }
                ListWidget::item:selected {
                    background-color: #009faa;
                    color: #ffffff;
                }
            """)
    
    def _do_search(self):
        """执行搜索"""
        keyword = self.search_input.text().strip()
        
        if not keyword:
            self._count_label.setText("请输入关键词后按Enter或点击搜索")
            self.result_list.clear()
            return
        
        self.keyword = keyword
        filtered = []
        keyword_lower = keyword.lower()
        
        for item in self._all_results:
            conv = item.get('conversation', {})
            title = conv.get('title', '').lower()
            preview = item.get('preview', '').lower()
            
            if keyword_lower in title or keyword_lower in preview:
                filtered.append(item)
        
        if filtered:
            self._count_label.setText(f"找到 {len(filtered)} 轮对话")
        else:
            self._count_label.setText("未找到匹配的对话")
        
        self._display_results(filtered)
    
    def _display_results(self, results: List[Dict[str, Any]]):
        self.result_list.clear()
        for item in results:
            conv = item.get('conversation', {})
            round_num = item.get('round', 0)
            title = conv.get('title', '无标题')
            
            # 创建列表项
            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, item)
            
            # 使用自定义 widget
            widget = QWidget(self.result_list)
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(0, 4, 0, 4)
            layout.setSpacing(2)
            
            # 标题行
            title_layout = QHBoxLayout()
            title_label = StrongBodyLabel(title, self.result_list)
            title_layout.addWidget(title_label)
            
            if round_num > 0:
                round_label = CaptionLabel(f"第{round_num}轮", self.result_list)
                round_label.setStyleSheet("color: #009faa;")
                title_layout.addWidget(round_label)
            
            title_layout.addStretch()
            layout.addLayout(title_layout)
            
            # 预览内容（高亮关键词）
            preview = item.get('preview', '')
            if preview:
                preview_label = CaptionLabel(self._highlight_keyword(preview), self.result_list)
                preview_label.setWordWrap(True)
                preview_label.setTextFormat(Qt.RichText)
                layout.addWidget(preview_label)
            
            widget.setLayout(layout)
            
            # 设置大小
            list_item.setSizeHint(widget.sizeHint())
            self.result_list.addItem(list_item)
            self.result_list.setItemWidget(list_item, widget)
    
    def _highlight_keyword(self, text: str) -> str:
        """高亮关键词"""
        if not self.keyword:
            return text
        escaped = re.escape(self.keyword)
        pattern = re.compile(f'({escaped})', re.IGNORECASE)
        return pattern.sub(r'<b style="background-color: #ffeb3b; color: #000; padding: 1px 2px; border-radius: 2px;">\1</b>', text)
    
    def _on_result_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            self.result_selected.emit(data)
            self.close()


class DeepSeekToolPage(TabPageInterface):
    """DeepSeek JSON对话处理页面"""
    
    page_id = "deepseek_json"
    page_name = "DeepSeek对话"
    
    @classmethod
    def create(cls, parent=None) -> QWidget:
        return DeepSeekToolWidget(parent)


class MarkdownRenderer:
    """简单的 Markdown 渲染器，将 Markdown 转换为 HTML"""

    def __init__(self, colors: Dict[str, str]):
        self._colors = colors
        self._in_code_block = False
        self._code_block_lines = []
        self._code_block_language = ""
        self._in_table = False
        self._table_rows: List[List[str]] = []
        self._table_alignments: List[str] = []

    def render(self, text: str) -> str:
        """将 Markdown 文本渲染为 HTML"""
        if not text:
            return ""

        lines = text.split("\n")
        html_parts = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 处理代码块
            if line.strip().startswith("```"):
                # 先结束可能存在的表格
                if self._in_table:
                    html_parts.append(self._render_table())
                    self._in_table = False
                    self._table_rows = []
                    self._table_alignments = []

                if self._in_code_block:
                    lang = self._code_block_language or "plaintext"
                    code_content = "\n".join(self._code_block_lines)
                    code_content = self._escape_html(code_content)
                    html_parts.append(
                        f'<pre style="background-color: #1a1a2e; color: #d4d4d4; padding: 12px; border-radius: 6px; margin: 8px 0; overflow-x: auto; border: 1px solid #333;">'
                        f'<code style="font-family: Consolas, Monaco, monospace; font-size: 12px; line-height: 1.5; color: #d4d4d4;">{code_content}</code>'
                        f'</pre>'
                    )
                    self._in_code_block = False
                    self._code_block_lines = []
                    self._code_block_language = ""
                else:
                    self._in_code_block = True
                    lang = line.strip()[3:].strip()
                    self._code_block_language = lang
                i += 1
                continue

            # 如果在代码块中，收集代码行
            if self._in_code_block:
                self._code_block_lines.append(line)
                i += 1
                continue

            # 检测表格行（以 | 开头或包含 | 的行）
            if line.strip().startswith("|") and "|" in line:
                # 检查是否是分隔行（如 |---|---|）
                separator_match = re.match(r'^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$', line)
                if separator_match and self._table_rows:
                    # 解析对齐方式
                    self._table_alignments = []
                    for cell in line.strip().split("|")[1:-1] if line.strip().startswith("|") else line.strip().split("|"):
                        cell = cell.strip()
                        if cell.startswith(":") and cell.endswith(":"):
                            self._table_alignments.append("center")
                        elif cell.endswith(":"):
                            self._table_alignments.append("right")
                        else:
                            self._table_alignments.append("left")
                    i += 1
                    continue

                # 普通表格行
                cells = [c.strip() for c in line.strip().split("|")]
                if cells and cells[0] == "":
                    cells = cells[1:]
                if cells and cells[-1] == "":
                    cells = cells[:-1]
                if cells:  # 非空行
                    self._table_rows.append([self._render_inline(c) for c in cells])
                    self._in_table = True
                i += 1
                continue
            else:
                # 非表格行，如果之前在表格中，先输出表格
                if self._in_table:
                    html_parts.append(self._render_table())
                    self._in_table = False
                    self._table_rows = []
                    self._table_alignments = []

            # 处理标题
            if line.startswith("#### "):
                html_parts.append(f'<h4 style="margin: 10px 0 4px 0; font-size: 14px;">{self._render_inline(line[5:])}</h4>')
            elif line.startswith("### "):
                html_parts.append(f'<h3 style="margin: 12px 0 6px 0; font-size: 15px;">{self._render_inline(line[4:])}</h3>')
            elif line.startswith("## "):
                html_parts.append(f'<h2 style="margin: 14px 0 8px 0; font-size: 17px;">{self._render_inline(line[3:])}</h2>')
            elif line.startswith("# "):
                html_parts.append(f'<h1 style="margin: 16px 0 10px 0; font-size: 20px;">{self._render_inline(line[2:])}</h1>')
            # 处理分隔线
            elif line.strip() == "---" or line.strip() == "***":
                html_parts.append(f'<hr style="border: none; border-top: 1px solid {self._colors.get("border", "#555")}; margin: 12px 0;">')
            # 处理列表项
            elif line.strip().startswith("- ") or line.strip().startswith("* "):
                content = line.strip()[2:]
                rendered = self._render_inline(content)
                html_parts.append(f'<div style="margin-left: 20px; padding: 2px 0;">• {rendered}</div>')
            elif line.strip().startswith("1. ") or line.strip().startswith("2. ") or line.strip().startswith("3. "):
                idx = line.strip()[0]
                content = line.strip()[3:]
                rendered = self._render_inline(content)
                html_parts.append(f'<div style="margin-left: 20px; padding: 2px 0;">{idx}. {rendered}</div>')
            # 处理引用
            elif line.strip().startswith("> "):
                rendered = self._render_inline(line.strip()[2:])
                html_parts.append(f'<div style="border-left: 3px solid #009faa; padding: 4px 12px; margin: 4px 0; color: {self._colors["text_secondary"]};">{rendered}</div>')
            # 处理普通段落
            elif line.strip():
                rendered = self._render_inline(line)
                html_parts.append(f'<div style="padding: 2px 0; line-height: 1.6; margin-bottom: 4px;">{rendered}</div>')
            else:
                html_parts.append('<div style="height: 4px;"></div>')

            i += 1

        # 处理未结束的表格
        if self._in_table:
            html_parts.append(self._render_table())

        # 如果还有未闭合的代码块
        if self._in_code_block and self._code_block_lines:
            lang = self._code_block_language or "plaintext"
            code_content = "\n".join(self._code_block_lines)
            code_content = self._escape_html(code_content)
            html_parts.append(
                f'<pre style="background-color: #1a1a2e; color: #d4d4d4; padding: 12px; border-radius: 6px; margin: 8px 0; overflow-x: auto; border: 1px solid #333;">'
                f'<code style="font-family: Consolas, Monaco, monospace; font-size: 12px; line-height: 1.5; color: #d4d4d4;">{code_content}</code>'
                f'</pre>'
            )

        return "\n".join(html_parts)

    def _render_table(self) -> str:
        """渲染 HTML 表格"""
        if not self._table_rows:
            return ""

        border_color = self._colors.get("border", "#555")
        is_dark = self._colors.get("bg_frame") != "#ffffff"
        header_bg = "#3a3a3a" if is_dark else "#f5f5f5"

        html = '<table style="border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px;">'

        # 表头（第一行）
        if self._table_rows:
            html += '<thead>'
            html += '<tr>'
            for j, cell in enumerate(self._table_rows[0]):
                align = self._table_alignments[j] if j < len(self._table_alignments) else "left"
                html += f'<th style="border: 1px solid {border_color}; padding: 8px 12px; text-align: {align}; background-color: {header_bg}; font-weight: 600;">{cell}</th>'
            html += '</tr>'
            html += '</thead>'

        # 表体
        if len(self._table_rows) > 1:
            html += '<tbody>'
            for i, row in enumerate(self._table_rows[1:]):
                bg = self._colors.get("bg_frame") if i % 2 == 0 else self._colors.get("bg_user")
                html += '<tr>'
                for j, cell in enumerate(row):
                    align = self._table_alignments[j] if j < len(self._table_alignments) else "left"
                    html += f'<td style="border: 1px solid {border_color}; padding: 6px 12px; text-align: {align}; background-color: {bg};">{cell}</td>'
                html += '</tr>'
            html += '</tbody>'

        html += '</table>'
        return html

    def _render_inline(self, text: str) -> str:
        """渲染行内 Markdown 元素"""
        # 行内代码（优先处理，避免被其他规则干扰）
        text = re.sub(r'`([^`]+)`', lambda m: f'<code style="background-color: #1a1a2e; color: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-family: Consolas, Monaco, monospace; font-size: 11px;">{m.group(1)}</code>', text)
        # 粗体
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        # 斜体
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # 链接
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color: #009faa; text-decoration: none;">\1</a>', text)
        # 删除线
        text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
        return text

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        return text


class DeepSeekToolWidget(QWidget):
    """DeepSeek JSON对话处理工具界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._filtered_data: List[Dict[str, Any]] = []
        self._search_results: List[Dict[str, Any]] = []
        self._current_display_data: Optional[Dict[str, Any]] = None  # 当前显示的数据
        self._current_display_type: str = ""  # conversation 或 round
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # 标题、搜索和按钮区域（一行）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        
        title_label = BodyLabel("DeepSeek对话处理", self)
        header_layout.addWidget(title_label)
        
        # 搜索按钮 - 点击弹出搜索弹窗
        self._search_btn = ToolButton(FIF.SEARCH, self)
        self._search_btn.setFixedSize(40, 40)
        self._search_btn.clicked.connect(self._open_search_popup)
        header_layout.addWidget(self._search_btn)
        
        header_layout.addStretch()
        
        load_btn = PushButton("加载JSON", self)
        load_btn.setIcon(FIF.FOLDER)
        load_btn.clicked.connect(self._load_json)
        header_layout.addWidget(load_btn)
        
        clear_btn = PushButton("清空", self)
        clear_btn.setIcon(FIF.DELETE)
        clear_btn.clicked.connect(self._clear_data)
        header_layout.addWidget(clear_btn)
        
        layout.addLayout(header_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal, self)
        
        # 左侧：对话列表
        left_frame = QFrame(self)
        left_frame.setObjectName("leftFrame")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(2)
        
        self._conversation_tree = QTreeWidget()
        self._conversation_tree.setObjectName("conversationTree")
        self._conversation_tree.setHeaderLabel("对话列表")
        self._conversation_tree.itemClicked.connect(self._on_conversation_clicked)
        self._conversation_tree.setMinimumWidth(280)
        left_layout.addWidget(self._conversation_tree)
        
        splitter.addWidget(left_frame)
        
        # 右侧：对话内容
        right_frame = QFrame(self)
        right_frame.setObjectName("rightFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)
        
        # 占位提示（初始显示）
        self._placeholder_label = BodyLabel("请加载DeepSeek导出的conversations.json文件", self)
        self._placeholder_label.setAlignment(Qt.AlignCenter)
        self._placeholder_label.setStyleSheet("color: #888; font-size: 14px;")
        right_layout.addWidget(self._placeholder_label)
        
        self._content_text = TextEdit()
        self._content_text.setObjectName("contentText")
        self._content_text.setReadOnly(True)
        self._content_text.setMinimumWidth(400)
        self._content_text.hide()  # 初始隐藏
        right_layout.addWidget(self._content_text)
        
        splitter.addWidget(right_frame)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter, 1)
        
        # 连接主题变化信号
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self._on_theme_changed)
        
        self._apply_style()
    
    def _on_theme_changed(self, theme):
        """主题变化时重新应用样式"""
        self._apply_style()
        self.update()
        # 重新渲染当前显示的内容
        self._refresh_current_display()
    
    def _refresh_current_display(self):
        """重新渲染当前显示的内容"""
        if not self._current_display_data:
            return
        
        if self._current_display_type == "conversation":
            self._display_conversation(self._current_display_data)
        elif self._current_display_type == "round":
            self._display_round(self._current_display_data)
    
    def _apply_style(self):
        """应用样式 - 根据主题动态设置颜色"""
        if isDarkTheme():
            tree_style = """
                QTreeWidget#conversationTree {
                    background-color: #2d2d2d;
                    border: none;
                    color: #ffffff;
                }
                QTreeWidget#conversationTree::item {
                    padding: 4px;
                    border-radius: 4px;
                    color: #ffffff;
                }
                QTreeWidget#conversationTree::item:hover {
                    background-color: #3d3d3d;
                }
                QTreeWidget#conversationTree::item:selected {
                    background-color: #009faa;
                    color: #ffffff;
                }
                QTreeWidget#conversationTree QHeaderView::section {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: none;
                    padding: 4px;
                }
                QTreeWidget#conversationTree QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 12px;
                    margin: 0;
                }
                QTreeWidget#conversationTree QScrollBar::handle:vertical {
                    background-color: #5d5d5d;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QTreeWidget#conversationTree QScrollBar::handle:vertical:hover {
                    background-color: #7d7d7d;
                }
                QTreeWidget#conversationTree QScrollBar::add-line:vertical,
                QTreeWidget#conversationTree QScrollBar::sub-line:vertical {
                    height: 0;
                }
                QTreeWidget#conversationTree QScrollBar::add-page:vertical,
                QTreeWidget#conversationTree QScrollBar::sub-page:vertical {
                    background: none;
                }
            """
            
            text_style = """
                QTextEdit#contentText {
                    background-color: #1e1e1e;
                    border: none;
                    color: #ffffff;
                }
            """
            
            frame_style = """
                QFrame#leftFrame, QFrame#rightFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
            """
            
            self._conversation_tree.setStyleSheet(tree_style)
            self._content_text.setStyleSheet(text_style)
            self.setStyleSheet(frame_style)
            # 更新占位标签颜色
            self._placeholder_label.setStyleSheet("color: #888888; font-size: 14px;")
        else:
            tree_style = """
                QTreeWidget#conversationTree {
                    background-color: #ffffff;
                    border: none;
                    color: #333333;
                }
                QTreeWidget#conversationTree::item {
                    padding: 4px;
                    border-radius: 4px;
                    color: #333333;
                }
                QTreeWidget#conversationTree::item:hover {
                    background-color: #f0f0f0;
                }
                QTreeWidget#conversationTree::item:selected {
                    background-color: #009faa;
                    color: #ffffff;
                }
                QTreeWidget#conversationTree QHeaderView::section {
                    background-color: #ffffff;
                    color: #333333;
                    border: none;
                    padding: 4px;
                }
                QTreeWidget#conversationTree QScrollBar:vertical {
                    background-color: #ffffff;
                    width: 12px;
                    margin: 0;
                }
                QTreeWidget#conversationTree QScrollBar::handle:vertical {
                    background-color: #c0c0c0;
                    border-radius: 6px;
                    min-height: 20px;
                }
                QTreeWidget#conversationTree QScrollBar::handle:vertical:hover {
                    background-color: #a0a0a0;
                }
                QTreeWidget#conversationTree QScrollBar::add-line:vertical,
                QTreeWidget#conversationTree QScrollBar::sub-line:vertical {
                    height: 0;
                }
                QTreeWidget#conversationTree QScrollBar::add-page:vertical,
                QTreeWidget#conversationTree QScrollBar::sub-page:vertical {
                    background: none;
                }
            """
            
            text_style = """
                QTextEdit#contentText {
                    background-color: #fafafa;
                    border: none;
                    color: #333333;
                }
            """
            
            frame_style = """
                QFrame#leftFrame, QFrame#rightFrame {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """
            
            self._conversation_tree.setStyleSheet(tree_style)
            self._content_text.setStyleSheet(text_style)
            self.setStyleSheet(frame_style)
    
    def _load_json(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择DeepSeek JSON文件", "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            
            self._filtered_data = self._data.copy()
            self._populate_tree()
            
            # 隐藏占位标签，显示内容区域
            self._placeholder_label.hide()
            self._content_text.show()
            
            InfoBar.success(
                title="加载成功",
                content=f"已加载 {len(self._data)} 个对话",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="加载失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _clear_data(self):
        self._data = []
        self._filtered_data = []
        self._search_results = []
        self._current_display_data = None
        self._current_display_type = ""
        self._conversation_tree.clear()
        self._content_text.clear()
        # 显示占位标签，隐藏内容区域
        self._placeholder_label.show()
        self._content_text.hide()
    
    def _open_search_popup(self):
        """打开搜索弹窗"""
        if not self._data:
            InfoBar.warning(
                title="提示",
                content="请先加载JSON文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
            return
        
        # 获取所有搜索结果
        all_results = self._search_in_all()
        
        popup = SearchResultPopup(all_results, "", self)
        popup.result_selected.connect(self._on_search_result_selected)
        popup.exec()
    
    def _search_in_all(self) -> List[Dict[str, Any]]:
        """搜索所有对话"""
        results = []
        for conv in self._data:
            title = conv.get('title', '')
            mapping = conv.get('mapping', {})
            rounds = self._parse_conversation_rounds(mapping)
            
            # 检查标题
            for idx, round_data in enumerate(rounds, 1):
                user_content = round_data.get('user', '')
                assistant_content = round_data.get('assistant', '')
                
                # 获取用户内容的前200字作为预览
                preview = user_content[:200] if user_content else assistant_content[:200]
                
                results.append({
                    'conversation': conv,
                    'round': idx,
                    'preview': preview,
                })
        
        return results
    
    def _on_search_result_selected(self, result_data: Dict[str, Any]):
        """搜索结果选中 - 跳转到对应内容"""
        conv = result_data.get('conversation', {})
        round_num = result_data.get('round', 0)
        
        # 显示该对话
        self._display_conversation(conv)
        
        # 高亮显示左侧树中的对应节点
        self._highlight_tree_node(conv, round_num)
    
    def _highlight_tree_node(self, conv: Dict[str, Any], round_num: int):
        """在树中高亮对应节点"""
        # 展开树并找到对应节点
        for i in range(self._conversation_tree.topLevelItemCount()):
            conv_item = self._conversation_tree.topLevelItem(i)
            conv_data = conv_item.data(0, Qt.UserRole)
            
            if isinstance(conv_data, dict) and conv_data.get('title') == conv.get('title'):
                # 找到对应对话
                self._conversation_tree.setCurrentItem(conv_item)
                
                if round_num > 0 and round_num <= conv_item.childCount():
                    round_item = conv_item.child(round_num - 1)
                    if round_item:
                        self._conversation_tree.setCurrentItem(round_item)
                        self._conversation_tree.scrollToItem(round_item)
                
                self._conversation_tree.setFocus()
                break
    
    def _populate_tree(self):
        self._conversation_tree.clear()
        
        for conv in self._filtered_data:
            conv_item = QTreeWidgetItem(self._conversation_tree)
            conv_item.setText(0, conv.get('title', '无标题'))
            conv_item.setData(0, Qt.UserRole, conv)
            
            # 解析对话轮次
            mapping = conv.get('mapping', {})
            rounds = self._parse_conversation_rounds(mapping)
            
            for idx, round_data in enumerate(rounds, 1):
                round_item = QTreeWidgetItem(conv_item)
                round_item.setText(0, f"第{idx}次")
                round_item.setData(0, Qt.UserRole, round_data)
        
        self._conversation_tree.expandAll()
    
    def _parse_conversation_rounds(self, mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析对话轮次"""
        rounds = []
        root = mapping.get('root', {})
        if not root:
            return rounds
        
        current_node = root
        round_data = {'user': '', 'assistant': ''}
        
        while current_node:
            children = current_node.get('children', [])
            if not children:
                break
            
            for child_id in children:
                child_node = mapping.get(child_id, {})
                message = child_node.get('message', {})
                fragments = message.get('fragments', [])
                
                for fragment in fragments:
                    frag_type = fragment.get('type', '')
                    content = fragment.get('content', '')
                    
                    if frag_type == 'REQUEST':
                        round_data['user'] = content
                    elif frag_type == 'RESPONSE':
                        round_data['assistant'] = content
                        rounds.append(round_data.copy())
                        round_data = {'user': '', 'assistant': ''}
                
                current_node = child_node
                break
        
        return rounds
    
    def _on_conversation_clicked(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.UserRole)
        
        if isinstance(data, dict):
            if 'mapping' in data:
                self._display_conversation(data)
            elif 'user' in data or 'assistant' in data:
                self._display_round(data)
    
    def _get_theme_colors(self) -> Dict[str, str]:
        """获取当前主题的颜色配置"""
        if isDarkTheme():
            return {
                'bg_frame': '#2d2d2d',
                'bg_user': '#3a3a3a',
                'bg_ai': '#1e1e1e',
                'text': '#ffffff',
                'text_secondary': '#aaaaaa',
                'text_user_label': '#4CAF50',
                'text_ai_label': '#2196F3',
                'border': '#3d3d3d',
            }
        else:
            return {
                'bg_frame': '#ffffff',
                'bg_user': '#f5f5f5',
                'bg_ai': '#e8f4f5',
                'text': '#333333',
                'text_secondary': '#888888',
                'text_user_label': '#2E7D32',
                'text_ai_label': '#1565C0',
                'border': '#e0e0e0',
            }
    
    def _render_markdown(self, text: str, colors: Dict[str, str]) -> str:
        """使用 Markdown 渲染器渲染文本"""
        renderer = MarkdownRenderer(colors)
        return renderer.render(text)
    
    def _display_conversation(self, conv: Dict[str, Any]):
        """显示完整对话 - 渲染为 Markdown 预览"""
        # 保存当前显示的数据
        self._current_display_data = conv
        self._current_display_type = "conversation"
        
        title = conv.get('title', '无标题')
        inserted_at = conv.get('inserted_at', '')
        updated_at = conv.get('updated_at', '')
        colors = self._get_theme_colors()
        
        html = f"""
        <div style="padding: 12px; color: {colors['text']}; font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;">
            <h2 style="margin: 0 0 4px 0; font-size: 18px; font-weight: 600; color: {colors['text']};">{title}</h2>
            <p style="color: {colors['text_secondary']}; font-size: 12px; margin: 0 0 16px 0;">
                创建: {inserted_at[:19] if inserted_at else '未知'} | 更新: {updated_at[:19] if updated_at else '未知'}
            </p>
            <hr style="border: none; border-top: 1px solid {colors['border']}; margin: 0 0 16px 0;">
        """
        
        mapping = conv.get('mapping', {})
        rounds = self._parse_conversation_rounds(mapping)
        
        for idx, round_data in enumerate(rounds, 1):
            user_content = round_data.get('user', '')
            assistant_content = round_data.get('assistant', '')
            
            # 使用 Markdown 渲染
            user_html = self._render_markdown(user_content, colors)
            ai_html = self._render_markdown(assistant_content, colors)
            
            html += f"""
            <div style="margin-bottom: 20px;">
                <h3 style="color: {colors['text']}; font-size: 15px; margin: 0 0 12px 0; font-weight: 600;">第{idx}次对话</h3>
                <div style="background: {colors['bg_user']}; padding: 14px; border-radius: 8px; margin-bottom: 10px;">
                    <p style="color: {colors['text_user_label']}; font-weight: 600; margin: 0 0 8px 0; font-size: 13px;">用户</p>
                    <div style="color: {colors['text']}; line-height: 1.7;">{user_html}</div>
                </div>
                <div style="background: {colors['bg_ai']}; padding: 14px; border-radius: 8px;">
                    <p style="color: {colors['text_ai_label']}; font-weight: 600; margin: 0 0 8px 0; font-size: 13px;">AI</p>
                    <div style="color: {colors['text']}; line-height: 1.7;">{ai_html}</div>
                </div>
            </div>
            """
        
        html += "</div>"
        self._content_text.setHtml(html)
    
    def _display_round(self, round_data: Dict[str, str]):
        """显示单轮对话 - 渲染为 Markdown 预览"""
        # 保存当前显示的数据
        self._current_display_data = round_data
        self._current_display_type = "round"
        
        user_content = round_data.get('user', '')
        assistant_content = round_data.get('assistant', '')
        colors = self._get_theme_colors()
        
        # 使用 Markdown 渲染
        user_html = self._render_markdown(user_content, colors)
        ai_html = self._render_markdown(assistant_content, colors)
        
        html = f"""
        <div style="padding: 12px; color: {colors['text']}; font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;">
            <div style="background: {colors['bg_user']}; padding: 16px; border-radius: 8px; margin-bottom: 14px;">
                <p style="color: {colors['text_user_label']}; font-weight: 600; font-size: 14px; margin: 0 0 10px 0;">用户提问</p>
                <div style="color: {colors['text']}; line-height: 1.7;">{user_html}</div>
            </div>
            <div style="background: {colors['bg_ai']}; padding: 16px; border-radius: 8px;">
                <p style="color: {colors['text_ai_label']}; font-weight: 600; font-size: 14px; margin: 0 0 10px 0;">AI回答</p>
                <div style="color: {colors['text']}; line-height: 1.7;">{ai_html}</div>
            </div>
        </div>
        """
        
        self._content_text.setHtml(html)
