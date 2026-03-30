"""随手记插件 - 笔记编辑功能"""

from typing import Optional, List, Dict, Any
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
from qfluentwidgets import (
    LineEdit, ComboBox, SpinBox, PushButton, ToolButton, 
    SearchLineEdit, InfoBar, InfoBarPosition, MessageBox, MessageBoxBase
)
from qfluentwidgets import FluentIcon as FIF

from core import PluginInterface
from storage import DatabaseManager
from ui import CustomFluentIcon as CFIF
from .sidebar import NotebookSidebar
from .toolbar import NotebookToolBar
from .editor import NotebookEditor


class NotebookDatabase:
    """随手记数据库操作类"""
    
    def __init__(self):
        """初始化数据库连接"""
        from storage import DatabaseManager
        self.db = DatabaseManager()
    
    def add_note(self, plugin_id: str, title: str, content: str,
                 category_name: str = None, note_type: str = 'markdown',
                 sort_order: int = 0) -> int:
        """添加笔记"""
        with self.db.get_connection() as conn:
            category_id = None
            if category_name:
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE plugin_id = ? AND name = ?",
                    (plugin_id, category_name)
                )
                row = cursor.fetchone()
                if row:
                    category_id = row['id']
            cursor = conn.execute(
                """INSERT INTO notebook (plugin_id, category_id, title, content, note_type, sort_order) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (plugin_id, category_id, title, content, note_type, sort_order)
            )
            conn.commit()
            return cursor.lastrowid
    
    def note_exists(self, plugin_id: str, title: str) -> bool:
        """检查笔记是否存在"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM notebook WHERE plugin_id = ? AND title = ?",
                (plugin_id, title)
            )
            return cursor.fetchone() is not None
    
    def get_notes(self, plugin_id: str, category_id: int = None) -> List[Dict[str, Any]]:
        """获取笔记列表"""
        with self.db.get_connection() as conn:
            if category_id:
                cursor = conn.execute(
                    """SELECT n.*, c.name as category_name 
                       FROM notebook n 
                       LEFT JOIN categories c ON n.category_id = c.id 
                       WHERE n.plugin_id = ? AND n.category_id = ?
                       ORDER BY n.sort_order, n.id DESC""",
                    (plugin_id, category_id)
                )
            else:
                cursor = conn.execute(
                    """SELECT n.*, c.name as category_name 
                       FROM notebook n 
                       LEFT JOIN categories c ON n.category_id = c.id 
                       WHERE n.plugin_id = ?
                       ORDER BY n.sort_order, n.id DESC""",
                    (plugin_id,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    def update_note(self, plugin_id: str, note_id: int, **kwargs) -> bool:
        """更新笔记"""
        allowed_fields = {'title', 'content', 'note_type', 'category_id', 'sort_order'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [plugin_id, note_id]
        with self.db.get_connection() as conn:
            conn.execute(
                f"UPDATE notebook SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE plugin_id = ? AND id = ?",
                values
            )
            conn.commit()
            return True
    
    def delete_note(self, plugin_id: str, note_id: int) -> bool:
        """删除笔记"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM notebook WHERE plugin_id = ? AND id = ?",
                (plugin_id, note_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def search_notes(self, plugin_id: str, keyword: str) -> List[Dict[str, Any]]:
        """搜索笔记"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """SELECT n.*, c.name as category_name 
                   FROM notebook n 
                   LEFT JOIN categories c ON n.category_id = c.id 
                   WHERE n.plugin_id = ? AND (n.title LIKE ? OR n.content LIKE ?)
                   ORDER BY n.sort_order, n.id DESC""",
                (plugin_id, f'%{keyword}%', f'%{keyword}%')
            )
            return [dict(row) for row in cursor.fetchall()]


class NotebookWidget(QWidget):
    """随手记主组件"""
    
    note_saved = pyqtSignal()
    note_deleted = pyqtSignal()

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = NotebookDatabase()
        self.PLUGIN_ID = "notebook"
        self._current_note_id = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置 UI"""
        self.setObjectName("notebookWidget")
        self.setStyleSheet("NotebookWidget{background: transparent;}")

        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建最外层的滚动区域
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
        
        # 创建内容容器
        self._content_widget = QWidget()
        self._content_widget.setObjectName("contentWidget")
        self._content_widget.setStyleSheet("QWidget#contentWidget{background: transparent;}")
        self._content_layout = QHBoxLayout(self._content_widget)
        self._content_layout.setSpacing(0)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 分隔符
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setObjectName("notebookSplitter")
        
        # 设置样式 - 添加边框
        splitter.setStyleSheet("""
            QSplitter#notebookSplitter {
                border: 1px solid rgba(0, 0, 0, 0.06);
                border-radius: 5px;
                background: transparent;
            }
            QSplitter::handle {
                background: rgba(0, 0, 0, 0.06);
                width: 1px;
            }
        """)

        # 左侧边栏
        self._sidebar = NotebookSidebar(self)
        self._sidebar.setStyleSheet("""
            NotebookSidebar {
                background: transparent;
                border-right: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        splitter.addWidget(self._sidebar)

        # 右侧编辑区
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

        # 工具栏
        self._toolbar = NotebookToolBar(self)
        self._toolbar.setStyleSheet("""
            NotebookToolBar {
                background: transparent;
                border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            }
        """)
        
        # 创建滚动区域包装工具栏
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

        # 创建滚动区域包装编辑器
        from qfluentwidgets import ScrollArea
        self._editor_scroll_area = ScrollArea()
        self._editor_scroll_area.setWidgetResizable(True)
        self._editor_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._editor_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 设置滚动区域背景透明
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
        
        # 编辑器
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

        splitter.addWidget(self._editor_container)

        # 设置分割比例
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([250, 1000])

        self._content_layout.addWidget(splitter)
        
        # 将内容容器添加到滚动区域
        self._main_scroll_area.setWidget(self._content_widget)
        
        main_layout.addWidget(self._main_scroll_area)
    
    def _connect_signals(self):
        """连接信号"""
        self._sidebar.note_selected.connect(self._load_note)
        self._sidebar.note_created.connect(self._create_new_note)
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
        self._editor.alt_enter_pressed.connect(self._on_alt_enter_pressed)
        self._editor.save_signal.connect(self._save_note)
    
    def load_data(self):
        """加载数据"""
        self._sidebar.load_notes(self.db.get_notes(self.PLUGIN_ID))
    
    def _load_note(self, note_id: int):
        """加载笔记"""
        notes = self.db.get_notes(self.PLUGIN_ID)
        for note in notes:
            if note['id'] == note_id:
                self._current_note_id = note_id
                self._editor.set_content(note['content'])
                self._toolbar.set_note_type(note['note_type'])
                break
    
    def _create_new_note(self):
        """创建新笔记"""
        self._current_note_id = None
        self._editor.clear()
        self._toolbar.set_note_type('markdown')
    
    def _save_note(self):
        """保存笔记

        第一次保存：弹出对话框输入标题
        后续保存：直接覆盖保存
        """
        from qfluentwidgets import MessageBoxBase, LineEdit
        from PyQt5.QtWidgets import QVBoxLayout
        from datetime import datetime

        content = self._editor.get_content()
        note_type = self._toolbar.get_note_type()

        # 如果已有笔记ID，直接覆盖保存
        if self._current_note_id:
            notes = self.db.get_notes(self.PLUGIN_ID)
            current_title = ""
            for note in notes:
                if note['id'] == self._current_note_id:
                    current_title = note['title']
                    break

            self.db.update_note(
                self.PLUGIN_ID,
                self._current_note_id,
                content=content,
                note_type=note_type
            )
            InfoBar.success("保存成功", f"笔记 '{current_title}' 已更新", parent=self)
            self._sidebar.load_notes(self.db.get_notes(self.PLUGIN_ID))
            self.note_saved.emit()
            return

        # 第一次保存，弹出对话框
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
            # 如果标题为空，使用当前时间作为标题
            if not title:
                title = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            note_id = self.db.add_note(
                self.PLUGIN_ID,
                title=title,
                content=content,
                note_type=note_type
            )
            self._current_note_id = note_id
            InfoBar.success("创建成功", f"笔记 '{title}' 已创建", parent=self)

            self._sidebar.load_notes(self.db.get_notes(self.PLUGIN_ID))
            self.note_saved.emit()
    
    def _delete_note(self):
        """删除笔记"""
        if not self._current_note_id:
            InfoBar.warning("提示", "没有可删除的笔记", parent=self)
            return
        
        box = MessageBox("删除笔记", "确定要删除当前笔记吗？", self)
        if box.exec():
            self.db.delete_note(self.PLUGIN_ID, self._current_note_id)
            self._current_note_id = None
            self._editor.clear()
            self._sidebar.load_notes(self.db.get_notes(self.PLUGIN_ID))
            InfoBar.success("删除成功", "笔记已删除", parent=self)
            self.note_deleted.emit()
    
    def _format_note(self, format_type: str):
        """格式化笔记"""
        self.core.logger.info(f"格式化笔记：{format_type}")
        # TODO: 实现格式化逻辑
    
    def _show_doc_info(self):
        """显示文档信息"""
        from qfluentwidgets import InfoBar, InfoBarPosition
        content = self._editor.get_content()
        char_count = len(content)
        line_count = len(content.splitlines())
        InfoBar.info(
            title="文档信息",
            content=f"字符数：{char_count}\n行数：{line_count}",
            orient=Qt.Vertical,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def _find_text(self):
        """查找文本 - 使用无边框对话框"""
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
                # 使用 QTextEdit 的 find 方法
                found = self._editor._editor.find(text)
                if found:
                    InfoBar.success("查找成功", f"找到 '{text}'", parent=self)
                else:
                    InfoBar.warning("未找到", f"未找到 '{text}'", parent=self)
    
    def _replace_text(self):
        """替换文本 - 简单实现"""
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
        from qfluentwidgets import MessageBoxBase, ComboBox, InfoBar, PushButton
        from PyQt5.QtWidgets import QVBoxLayout, QFileDialog
        from pathlib import Path
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("导出笔记")
        
        export_layout = QVBoxLayout()
        format_combo = ComboBox()
        format_combo.addItems(["TXT", "Markdown", "HTML"])
        export_layout.addWidget(format_combo)
        
        dialog.viewLayout.addLayout(export_layout)
        
        if dialog.exec():
            format_type = format_combo.currentText()
            content = self._editor.get_content()
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存文件", "",
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
    
    def _on_alt_enter_pressed(self):
        """处理 Alt+Enter 键 - 弹出保存对话框"""
        self._save_note()


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
