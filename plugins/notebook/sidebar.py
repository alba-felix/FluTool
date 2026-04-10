"""随手记侧边栏 - 笔记列表和搜索 - 性能优化版本"""

from typing import List, Dict, Any
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout, QMenu, QAction
from qfluentwidgets import SearchLineEdit, ToolButton, FluentIcon as FIF, isDarkTheme
from ui import CustomFluentIcon as CFIF


class NotebookSidebar(QWidget):
    """侧边栏组件 - 性能优化版本"""

    note_selected = pyqtSignal(int)
    note_created = pyqtSignal()
    note_deleted = pyqtSignal(int)
    note_renamed = pyqtSignal(int, str)
    note_exported = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notebookSidebar")
        self.setFixedWidth(250)
        self._notes_data = []
        self._notes_by_id: Dict[int, Dict[str, Any]] = {}
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_filter)
        self._pending_search = ""
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 6, 6, 6)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(4)
        self._search_box = SearchLineEdit()
        self._search_box.setPlaceholderText("搜索笔记")
        self._search_box.textChanged.connect(self._queue_filter)
        top_layout.addWidget(self._search_box, 1)
        
        self._new_btn = ToolButton(CFIF.NOTEBOOK)
        self._new_btn.setToolTip("新建笔记")
        self._new_btn.setFixedSize(32, 32)
        self._new_btn.clicked.connect(self.note_created.emit)
        top_layout.addWidget(self._new_btn)
        
        layout.addLayout(top_layout)

        self._note_list = QListWidget()
        self._note_list.setFrameShape(QListWidget.NoFrame)
        self._note_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._note_list.customContextMenuRequested.connect(self._show_context_menu)
        
        text_color = "#0078d4"
        
        if isDarkTheme():
            hover_bg = "rgba(255, 255, 255, 0.08)"
            selected_bg = "rgba(0, 120, 215, 0.15)"
        else:
            hover_bg = "rgba(0, 0, 0, 0.04)"
            selected_bg = "rgba(0, 120, 215, 0.08)"
        
        style_sheet = """
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                height: 32px;
                border-radius: 4px;
                padding: 4px 8px;
                color: %s;
            }
            QListWidget::item:hover {
                background: %s;
            }
            QListWidget::item:selected {
                background: %s;
                color: #0078d4;
            }
        """ % (text_color, hover_bg, selected_bg)
        self._note_list.setStyleSheet(style_sheet)
        self._note_list.itemClicked.connect(self._on_note_selected)
        self._note_list.itemDoubleClicked.connect(self._on_note_double_clicked)
        self._note_list.installEventFilter(self)
        layout.addWidget(self._note_list)

    def eventFilter(self, obj, event):
        """事件过滤器"""
        if obj == self._note_list:
            if event.type() == event.KeyPress:
                if event.key() == Qt.Key_Delete:
                    self._delete_selected_note()
                    return True
                elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    self._rename_selected_note()
                    return True
                elif event.key() == Qt.Key_Up or event.key() == Qt.Key_Down:
                    current_row = self._note_list.currentRow()
                    if event.key() == Qt.Key_Up and current_row > 0:
                        self._select_note_by_row(current_row - 1)
                    elif event.key() == Qt.Key_Down and current_row < self._note_list.count() - 1:
                        self._select_note_by_row(current_row + 1)
                    return True
        return super().eventFilter(obj, event)

    def _select_note_by_row(self, row: int):
        """通过行号选中笔记"""
        item = self._note_list.item(row)
        if item:
            self._note_list.setCurrentItem(item)
            self._on_note_selected(item)

    def _show_context_menu(self, pos):
        """显示右键菜单"""
        item = self._note_list.itemAt(pos)
        if not item:
            return
        
        note_id = item.data(Qt.UserRole)
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 120, 215, 0.2);
            }
        """)
        
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self._rename_note(note_id))
        menu.addAction(rename_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        export_action = QAction("导出", self)
        export_action.triggered.connect(lambda: self._export_note(note_id))
        menu.addAction(export_action)
        
        menu.exec_(self._note_list.mapToGlobal(pos))

    def _rename_note(self, note_id: int):
        """重命名笔记"""
        from qfluentwidgets import MessageBoxBase, LineEdit
        from PyQt5.QtWidgets import QVBoxLayout
        
        note = self._notes_by_id.get(note_id)
        current_title = note['title'] if note else ""
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("重命名笔记")
        
        layout = QVBoxLayout()
        name_edit = LineEdit()
        name_edit.setText(current_title)
        name_edit.selectAll()
        layout.addWidget(name_edit)
        dialog.viewLayout.addLayout(layout)
        
        dialog.yesButtonText = "确定"
        dialog.cancelButtonText = "取消"
        
        if dialog.exec():
            new_title = name_edit.text().strip()
            if new_title and new_title != current_title:
                self.note_renamed.emit(note_id, new_title)

    def _delete_note(self, note_id: int):
        """删除笔记"""
        self.note_deleted.emit(note_id)

    def _delete_selected_note(self):
        """删除选中的笔记"""
        current_item = self._note_list.currentItem()
        if current_item:
            note_id = current_item.data(Qt.UserRole)
            self._delete_note(note_id)

    def _rename_selected_note(self):
        """重命名选中的笔记"""
        current_item = self._note_list.currentItem()
        if current_item:
            note_id = current_item.data(Qt.UserRole)
            self._rename_note(note_id)

    def _export_note(self, note_id: int):
        """导出笔记"""
        self.note_exported.emit(note_id)

    def load_notes(self, notes: List[Dict[str, Any]]):
        """加载笔记列表"""
        self._notes_data = notes
        self._notes_by_id = {note['id']: note for note in notes}
        self._note_list.clear()
        for note in notes:
            item = QListWidgetItem(note['title'])
            item.setData(Qt.UserRole, note['id'])
            
            created_at = note.get('created_at', '')
            if created_at:
                tooltip = f"创建时间: {created_at}"
                item.setToolTip(tooltip)
            
            self._note_list.addItem(item)

    def _queue_filter(self, text: str):
        """队列过滤 - 防抖优化"""
        self._pending_search = text
        self._search_timer.start(150)

    def _do_filter(self):
        """执行过滤 - 使用缓存优化"""
        text = self._pending_search.lower()
        
        for i in range(self._note_list.count()):
            item = self._note_list.item(i)
            note_id = item.data(Qt.UserRole)
            
            title_match = text in item.text().lower()
            
            note = self._notes_by_id.get(note_id)
            content_match = note and text in note.get('content', '').lower()
            
            item.setHidden(not (title_match or content_match))

    def _filter_notes(self, text: str):
        """过滤笔记 - 搜索标题和内容"""
        self._queue_filter(text)

    def _on_note_selected(self, item: QListWidgetItem):
        """笔记选中事件"""
        note_id = item.data(Qt.UserRole)
        if note_id is not None:
            self.note_selected.emit(note_id)

    def _on_note_double_clicked(self, item: QListWidgetItem):
        """笔记双击事件 - 重命名"""
        note_id = item.data(Qt.UserRole)
        if note_id is not None:
            self._rename_note(note_id)

    def get_selected_note_id(self) -> int:
        """获取选中的笔记 ID"""
        current_item = self._note_list.currentItem()
        return current_item.data(Qt.UserRole) if current_item else None
    
    def select_note(self, note_id: int):
        """选中指定笔记"""
        for i in range(self._note_list.count()):
            item = self._note_list.item(i)
            if item.data(Qt.UserRole) == note_id:
                self._note_list.setCurrentItem(item)
                self._on_note_selected(item)
                break
    
    def update_note_title(self, note_id: int, new_title: str):
        """更新笔记标题"""
        for i in range(self._note_list.count()):
            item = self._note_list.item(i)
            if item.data(Qt.UserRole) == note_id:
                item.setText(new_title)
                break
        
        if note_id in self._notes_by_id:
            self._notes_by_id[note_id]['title'] = new_title
