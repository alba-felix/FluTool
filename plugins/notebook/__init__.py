"""随手记插件 - 笔记编辑功能"""

from typing import Optional, List, Dict, Any
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFileDialog
from qfluentwidgets import (
    LineEdit, ComboBox, SpinBox, PushButton, ToolButton, 
    SearchLineEdit, InfoBar, InfoBarPosition, MessageBox, MessageBoxBase
)
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface
from ui import CustomFluentIcon as CFIF
from core import SearchResult
from plugins.notebook.service import NotebookService
from .sidebar import NotebookSidebar
from .toolbar import NotebookToolBar
from .editor import NotebookEditor
from .quick_replace import QuickReplacePanel
from .text_processor import TextProcessor


class NotebookWidget(QWidget):
    """随手记主组件"""
    
    note_saved = pyqtSignal()
    note_deleted = pyqtSignal()

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.PLUGIN_ID = "notebook"
        self.service = NotebookService(self.PLUGIN_ID)
        self._current_note_id = None
        self._quick_replace_visible = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置 UI"""
        self.setObjectName("notebookWidget")
        self.setStyleSheet("NotebookWidget{background: transparent;}")

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        from qfluentwidgets import ScrollArea as FluentScrollArea
        self._main_scroll_area = FluentScrollArea()
        self._main_scroll_area.setWidgetResizable(True)
        self._main_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._main_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._main_scroll_area.setObjectName("mainScrollArea")
        self._main_scroll_area.setStyleSheet("""
            ScrollArea#mainScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea#mainScrollArea {
                background: transparent;
                border: none;
            }
            ScrollArea QWidget#qt_scrollarea_viewport,
            QScrollArea QWidget#qt_scrollarea_viewport {
                background: transparent;
            }
        """)
        
        self._content_widget = QWidget()
        self._content_widget.setObjectName("contentWidget")
        self._content_widget.setStyleSheet("QWidget#contentWidget{background: transparent;}")
        self._content_layout = QHBoxLayout(self._content_widget)
        self._content_layout.setSpacing(0)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        
        self._main_splitter = QSplitter(Qt.Horizontal)
        self._main_splitter.setHandleWidth(1)
        self._main_splitter.setObjectName("notebookMainSplitter")
        
        self._main_splitter.setStyleSheet("""
            QSplitter#notebookMainSplitter {
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 5px;
                background: transparent;
            }
            QSplitter::handle {
                background: rgba(0, 0, 0, 0.06);
                width: 1px;
            }
        """)

        self._left_splitter = QSplitter(Qt.Horizontal)
        self._left_splitter.setHandleWidth(1)
        self._left_splitter.setObjectName("notebookLeftSplitter")

        self._sidebar = NotebookSidebar(self)
        self._sidebar.setStyleSheet("""
            NotebookSidebar {
                background: transparent;
                border-right: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        self._left_splitter.addWidget(self._sidebar)

        self._editor_container = QWidget()
        self._editor_container.setObjectName("editorContainer")
        self._editor_container.setStyleSheet("""
            QWidget#editorContainer {
                background: transparent;
            }
        """)
        self._editor_layout = QVBoxLayout(self._editor_container)
        self._editor_layout.setSpacing(0)
        self._editor_layout.setContentsMargins(0, 0, 0, 0)

        self._toolbar = NotebookToolBar(self)
        self._toolbar.setStyleSheet("""
            NotebookToolBar {
                background: transparent;
                border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        
        from qfluentwidgets import ScrollArea as FluentScrollArea
        self._toolbar_scroll_area = FluentScrollArea()
        self._toolbar_scroll_area.setWidgetResizable(True)
        self._toolbar_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._toolbar_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._toolbar_scroll_area.setFixedHeight(40)
        self._toolbar_scroll_area.setObjectName("toolbarScrollArea")
        self._toolbar_scroll_area.setStyleSheet("""
            ScrollArea#toolbarScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea#toolbarScrollArea {
                background: transparent;
                border: none;
            }
            ScrollArea QWidget#qt_scrollarea_viewport,
            QScrollArea QWidget#qt_scrollarea_viewport {
                background: transparent;
            }
        """)
        self._toolbar_scroll_area.setWidget(self._toolbar)
        
        self._editor_layout.addWidget(self._toolbar_scroll_area)

        from qfluentwidgets import ScrollArea
        self._editor_scroll_area = ScrollArea()
        self._editor_scroll_area.setWidgetResizable(True)
        self._editor_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._editor_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._editor_scroll_area.setStyleSheet("""
            ScrollArea {
                background: transparent;
                border: none;
            }
            ScrollArea:focus {
                background: transparent;
                border: none;
                outline: none;
            }
            ScrollArea QWidget#qt_scrollarea_viewport {
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
            }
        """)
        
        self._editor = NotebookEditor(self)
        self._editor.setStyleSheet("""
            NotebookEditor {
                background: transparent;
            }
            NotebookEditor:focus {
                background: transparent;
            }
            NotebookEditor #notebookEditorViewport {
                background: transparent;
            }
            TextEdit {
                background: transparent;
                border: none;
                padding: 10px;
            }
        """)
        self._editor_scroll_area.setWidget(self._editor)
        self._editor_layout.addWidget(self._editor_scroll_area)

        self._left_splitter.addWidget(self._editor_container)
        self._left_splitter.setStretchFactor(0, 0)
        self._left_splitter.setStretchFactor(1, 1)
        self._left_splitter.setSizes([250, 800])

        self._quick_replace_panel = QuickReplacePanel(self)
        self._quick_replace_panel.setFixedWidth(280)
        self._quick_replace_panel.hide()

        self._main_splitter.addWidget(self._left_splitter)
        self._main_splitter.addWidget(self._quick_replace_panel)
        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 0)

        self._content_layout.addWidget(self._main_splitter)
        
        self._main_scroll_area.setWidget(self._content_widget)
        
        main_layout.addWidget(self._main_scroll_area)
    
    def _connect_signals(self):
        """连接信号"""
        self._sidebar.note_selected.connect(self._load_note)
        self._sidebar.note_created.connect(self._create_new_note)
        self._sidebar.note_deleted.connect(self._delete_note_by_id)
        self._sidebar.note_renamed.connect(self._rename_note)
        self._sidebar.note_exported.connect(self._export_note_by_id)

        self._toolbar.new_note_signal.connect(self._create_new_note)
        self._toolbar.save_note_signal.connect(self._save_note)
        self._toolbar.delete_note_signal.connect(self._delete_note)
        self._toolbar.format_note_signal.connect(self._format_note)
        self._toolbar.doc_info_signal.connect(self._show_doc_info)
        self._toolbar.find_signal.connect(self._find_text)
        self._toolbar.replace_signal.connect(self._replace_text)
        self._toolbar.export_note_signal.connect(self._export_note)
        self._toolbar.font_changed.connect(self._change_font)
        self._toolbar.font_size_changed.connect(self._change_font_size)
        self._toolbar.wrap_toggled.connect(self._toggle_wrap)
        self._toolbar.quick_replace_toggled.connect(self._toggle_quick_replace)
        self._toolbar.list_toggled.connect(self._toggle_list)

        self._editor.enter_pressed.connect(self._on_enter_pressed)
        self._editor.alt_enter_pressed.connect(self._on_alt_enter_pressed)
        self._editor.save_signal.connect(self._save_note)

        self._quick_replace_panel.replace_triggered.connect(self._execute_quick_replace)

        # 监听数据恢复事件，实现热刷新
        if hasattr(self, 'core') and self.core and hasattr(self.core, 'event_bus'):
            self.core.event_bus.listen("data_restored", lambda _: self._on_data_restored())

    def _on_data_restored(self):
        """数据恢复后刷新"""
        self._current_note_id = None
        self._editor.clear()
        self.load_data()
    
    def load_data(self):
        """加载数据"""
        self._sidebar.load_notes(self.service.list_notes())
    
    def _load_note(self, note_id: int):
        """加载笔记"""
        note = self.service.get_note(note_id)
        if not note:
            return
        self._current_note_id = note_id
        self._editor.set_content(note['content'])
        self._toolbar.set_note_type(note.get('note_type', 'markdown'))
        self._editor._editor.setLineWrapMode(1)
        self._toolbar.set_wrap_state(True)
    
    def _create_new_note(self):
        """创建新笔记"""
        self._current_note_id = None
        self._editor.clear()
        self._toolbar.set_note_type('markdown')
        self._toolbar.set_wrap_state(True)
    
    def _save_note(self):
        """保存笔记"""
        from qfluentwidgets import MessageBoxBase, LineEdit
        from PyQt5.QtWidgets import QVBoxLayout
        from datetime import datetime

        content = self._editor.get_content()
        note_type = self._toolbar.get_note_type()

        if self._current_note_id:
            note = self.service.get_note(self._current_note_id)
            current_title = note['title'] if note else ""

            self.service.update_note(
                self._current_note_id,
                content=content,
                note_type=note_type
            )
            InfoBar.success("保存成功", f"笔记 '{current_title}' 已更新", parent=self)
            self._sidebar.load_notes(self.service.list_notes())
            self.note_saved.emit()
            # 记录操作日志
            if self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("UPDATE", f"更新笔记: {current_title}")
            return

        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("保存笔记")

        name_layout = QVBoxLayout()
        name_layout.setSpacing(12)
        self._save_name_edit = LineEdit()
        self._save_name_edit.setPlaceholderText("输入笔记名称（留空则使用当前时间）")
        name_layout.addWidget(self._save_name_edit)

        dialog.viewLayout.addLayout(name_layout)
        dialog.widget.setMinimumWidth(450)

        if dialog.exec():
            title = self._save_name_edit.text().strip()
            if not title:
                title = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            note_id = self.service.add_note(
                title=title,
                content=content,
                note_type=note_type
            )
            self._current_note_id = note_id
            InfoBar.success("创建成功", f"笔记 '{title}' 已创建", parent=self)

            self._sidebar.load_notes(self.service.list_notes())
            self.note_saved.emit()
            # 记录操作日志
            if self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("CREATE", f"创建笔记: {title}")
    
    def _delete_note(self):
        """删除笔记"""
        if not self._current_note_id:
            InfoBar.warning("提示", "没有可删除的笔记", parent=self)
            return

        box = MessageBox("删除笔记", "确定要删除当前笔记吗？", self)
        if box.exec():
            # 获取笔记标题用于日志
            note = self.service.get_note(self._current_note_id)
            note_title = note['title'] if note else ""

            self.service.delete_note(self._current_note_id)
            self._current_note_id = None
            self._editor.clear()
            self._sidebar.load_notes(self.service.list_notes())
            InfoBar.success("删除成功", "笔记已删除", parent=self)
            self.note_deleted.emit()
            # 记录操作日志
            if self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("DELETE", f"删除笔记: {note_title}")

    def _delete_note_by_id(self, note_id: int):
        """通过ID删除笔记"""
        box = MessageBox("删除笔记", "确定要删除该笔记吗？", self)
        if box.exec():
            # 获取笔记标题用于日志
            note = self.service.get_note(note_id)
            note_title = note['title'] if note else ""

            self.service.delete_note(note_id)
            if self._current_note_id == note_id:
                self._current_note_id = None
                self._editor.clear()
            self._sidebar.load_notes(self.service.list_notes())
            InfoBar.success("删除成功", "笔记已删除", parent=self)
            self.note_deleted.emit()
            # 记录操作日志
            if self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("DELETE", f"删除笔记: {note_title}")

    def _rename_note(self, note_id: int, new_title: str):
        """重命名笔记"""
        if self.service.note_exists(new_title):
            InfoBar.warning("提示", "已存在同名笔记", parent=self)
            return

        self.service.update_note(note_id, title=new_title)
        self._sidebar.update_note_title(note_id, new_title)
        InfoBar.success("重命名成功", f"笔记已重命名为 '{new_title}'", parent=self)
        # 记录操作日志
        if self.core and hasattr(self.core, 'logger'):
            self.core.logger.log_operation("UPDATE", f"重命名笔记为: {new_title}")
    
    def _format_note(self, format_type: str):
        """格式化笔记"""
        content = self._editor.get_content()
        
        if format_type == "ul":
            self._toggle_unordered_list()
        elif format_type == "ol":
            self._toggle_ordered_list()
        elif format_type == "format":
            self._format_code()
    
    def _toggle_unordered_list(self):
        """切换无序列表"""
        cursor = self._editor._editor.textCursor()
        selected_text = cursor.selectedText()
        
        if selected_text:
            lines = selected_text.split('\u2029')
            new_lines = []
            all_have_bullet = all(line.startswith('● ') for line in lines if line.strip())
            
            for line in lines:
                if all_have_bullet and line.startswith('● '):
                    new_lines.append(line[2:])
                elif not all_have_bullet and not line.startswith('● '):
                    new_lines.append('● ' + line)
                else:
                    new_lines.append(line)
            cursor.insertText('\n'.join(new_lines))
        else:
            cursor.select(cursor.LineUnderCursor)
            line = cursor.selectedText()
            if line.startswith('● '):
                cursor.insertText(line[2:])
            else:
                cursor.insertText('● ' + line)
    
    def _toggle_ordered_list(self):
        """切换有序列表"""
        cursor = self._editor._editor.textCursor()
        selected_text = cursor.selectedText()
        
        if selected_text:
            lines = selected_text.split('\u2029')
            new_lines = []
            all_numbered = True
            for i, line in enumerate(lines, 1):
                if line.strip() and not line.startswith(f'{i}. '):
                    all_numbered = False
                    break
            
            if all_numbered:
                for i, line in enumerate(lines, 1):
                    prefix = f'{i}. '
                    if line.startswith(prefix):
                        new_lines.append(line[len(prefix):])
                    else:
                        new_lines.append(line)
            else:
                for i, line in enumerate(lines, 1):
                    prefix = f'{i}. '
                    if not line.startswith(prefix):
                        new_lines.append(prefix + line)
                    else:
                        new_lines.append(line)
            cursor.insertText('\n'.join(new_lines))
        else:
            cursor.select(cursor.LineUnderCursor)
            line = cursor.selectedText()
            if line and len(line) >= 3 and line[0].isdigit() and line[1] == '.' and line[2] == ' ':
                cursor.insertText(line[3:])
            else:
                cursor.insertText('1. ' + line)
    
    def _format_code(self):
        """格式化代码"""
        note_type = self._toolbar.get_note_type()
        content = self._editor.get_content()
        
        try:
            if note_type == 'json':
                import json
                formatted = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
                self._editor.set_content(formatted)
            elif note_type == 'sql':
                try:
                    import sqlparse
                    formatted = sqlparse.format(content, reindent=True, indent_width=4)
                    self._editor.set_content(formatted)
                except ImportError:
                    InfoBar.warning("提示", "请安装 sqlparse 库: pip install sqlparse", parent=self)
            elif note_type == 'xml':
                try:
                    import xml.dom.minidom
                    dom = xml.dom.minidom.parseString(content)
                    formatted = dom.toprettyxml(indent="  ")
                    self._editor.set_content(formatted)
                except Exception as e:
                    InfoBar.error("格式化失败", str(e), parent=self)
            elif note_type == 'html':
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    formatted = soup.prettify()
                    self._editor.set_content(formatted)
                except ImportError:
                    InfoBar.warning("提示", "请安装 beautifulsoup4 库: pip install beautifulsoup4", parent=self)
            else:
                InfoBar.info("提示", f"暂不支持 {note_type} 格式化", parent=self)
        except Exception as e:
            InfoBar.error("格式化失败", str(e), parent=self)
    
    def _show_doc_info(self):
        """显示文档信息"""
        content = self._editor.get_content()
        char_count = len(content)
        char_no_space = len(content.replace(' ', '').replace('\t', '').replace('\n', ''))
        line_count = len(content.splitlines())
        word_count = len(content.split())
        
        created_at = ""
        updated_at = ""
        note = self.service.get_note(self._current_note_id)
        if note:
            created_at = note.get('created_at', '')
            updated_at = note.get('updated_at', '')
        
        info_text = f"""字符数：{char_count}
字符数(不含空白)：{char_no_space}
单词数：{word_count}
行数：{line_count}
创建时间：{created_at}
更新时间：{updated_at}"""
        
        InfoBar.info(
            title="文档信息",
            content=info_text,
            orient=Qt.Vertical,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def _find_text(self):
        """查找文本"""
        from qfluentwidgets import MessageBoxBase
        from PyQt5.QtWidgets import QVBoxLayout
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("查找")
        
        layout = QVBoxLayout()
        find_edit = LineEdit()
        find_edit.setPlaceholderText("输入要查找的内容")
        layout.addWidget(find_edit)
        dialog.viewLayout.addLayout(layout)
        
        dialog.yesButtonText = "查找"
        dialog.cancelButtonText = "取消"
        
        if dialog.exec():
            text = find_edit.text()
            if text:
                found = self._editor._editor.find(text)
                if found:
                    InfoBar.success("查找成功", f"找到 '{text}'", parent=self)
                else:
                    InfoBar.warning("未找到", f"未找到 '{text}'", parent=self)
    
    def _replace_text(self):
        """替换文本"""
        from qfluentwidgets import MessageBoxBase, LineEdit
        from PyQt5.QtWidgets import QVBoxLayout
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("替换")
        
        layout = QVBoxLayout()
        find_edit = LineEdit()
        find_edit.setPlaceholderText("查找内容")
        replace_edit = LineEdit()
        replace_edit.setPlaceholderText("替换为")
        layout.addWidget(find_edit)
        layout.addWidget(replace_edit)
        dialog.viewLayout.addLayout(layout)
        
        dialog.yesButtonText = "替换全部"
        dialog.cancelButtonText = "取消"
        
        if dialog.exec():
            find_text = find_edit.text()
            replace_text = replace_edit.text()
            if find_text:
                content = self._editor.get_content()
                new_content = content.replace(find_text, replace_text)
                self._editor.set_content(new_content)
                count = content.count(find_text)
                InfoBar.success("替换完成", f"已替换 {count} 处", parent=self)
    
    def _export_note(self):
        """导出笔记"""
        if not self._current_note_id:
            InfoBar.warning("提示", "请先选择要导出的笔记", parent=self)
            return
        
        note = self.service.get_note(self._current_note_id)
        if note:
            self._do_export_note(note)
    
    def _export_note_by_id(self, note_id: int):
        """通过ID导出笔记"""
        note = self.service.get_note(note_id)
        if note:
            self._do_export_note(note)
    
    def _do_export_note(self, note: dict):
        """执行导出"""
        from qfluentwidgets import ComboBox
        from PyQt5.QtWidgets import QVBoxLayout
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("导出笔记")
        
        export_layout = QVBoxLayout()
        format_combo = ComboBox()
        format_combo.addItems(["TXT", "Markdown", "HTML"])
        export_layout.addWidget(format_combo)
        
        dialog.viewLayout.addLayout(export_layout)
        
        if dialog.exec():
            format_type = format_combo.currentText()
            content = note['content']
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存文件", note['title'],
                f"{format_type} 文件 (*.{format_type.lower()})"
            )
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    InfoBar.success("导出成功", f"已保存到 {file_path}", parent=self)
                except Exception as e:
                    InfoBar.error("导出失败", str(e), parent=self)
    
    def _change_font(self, font_family: str):
        """更改字体"""
        self._editor.set_font_family(font_family)
    
    def _change_font_size(self, size: int):
        """更改字体大小"""
        self._editor.set_font_size(size)
    
    def _toggle_wrap(self, wrapped: bool):
        """切换自动换行"""
        self._editor._editor.setLineWrapMode(1 if wrapped else 0)
    
    def _toggle_quick_replace(self, visible: bool):
        """切换快捷替换面板"""
        self._quick_replace_visible = visible
        if visible:
            self._quick_replace_panel.show()
            self._main_splitter.setSizes([self.width() - 280, 280])
        else:
            self._quick_replace_panel.hide()
    
    def _toggle_list(self, visible: bool):
        """切换列表显示"""
        if visible:
            self._sidebar.show()
            self._left_splitter.setSizes([250, self._left_splitter.width() - 250])
        else:
            self._sidebar.hide()
    
    def _execute_quick_replace(self):
        """执行快捷替换"""
        options = self._quick_replace_panel.get_options()
        
        if not any(options.values()):
            InfoBar.warning("提示", "请至少选择一个替换选项", parent=self)
            return
        
        cursor = self._editor._editor.textCursor()
        selected_text = cursor.selectedText()
        
        if selected_text:
            content = selected_text.replace('\u2029', '\n')
            result = TextProcessor.process(content, options)
            cursor.insertText(result)
        else:
            content = self._editor.get_content()
            result = TextProcessor.process(content, options)
            self._editor.set_content(result)
        
        InfoBar.success("替换完成", "快捷替换已执行", parent=self)
    
    def _on_enter_pressed(self):
        """处理 Enter 键 - 触发保存（首次保存弹出命名对话框）"""
        self._save_note()
    
    def _on_alt_enter_pressed(self):
        """处理 Alt+Enter 键 - 换行"""
        # Alt+Enter 已经在编辑器中处理为换行
        pass


class Plugin(PluginInterface):
    """随手记插件"""
    
    PLUGIN_ID = "notebook"
    PLUGIN_NAME = "随手记"
    PLUGIN_ICON = CFIF.NOTEBOOK
    PLUGIN_PRIORITY = 6
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        self._widget = None
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        self._widget = NotebookWidget(self.core, parent)
        return self._widget
    
    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        self._widget.load_data()
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        service = NotebookService(self.PLUGIN_ID)
        results = []
        notes = service.search_notes(query)
        for note in notes[:20]:
            content_preview = note.get('content', '')[:100] + '...' if len(note.get('content', '')) > 100 else note.get('content', '')
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=note['title'],
                description=content_preview,
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in note['title'].lower() else 0.5,
                action=lambda note_id=note['id']: self._navigate_to_note(note_id),
                metadata={'note_id': note['id']}
            )
            results.append(result)
        return results
    
    def _navigate_to_note(self, note_id: int):
        if self._widget:
            self._widget._load_note(note_id)
            self._widget._sidebar.select_note(note_id)
