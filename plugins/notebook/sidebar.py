"""随手记侧边栏 - 笔记列表和搜索"""

from typing import List, Dict, Any
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QHBoxLayout
from qfluentwidgets import SearchLineEdit, ToolButton, FluentIcon as FIF, isDarkTheme
from ui import CustomFluentIcon as CFIF


class NotebookSidebar(QWidget):
    """侧边栏组件"""

    note_selected = pyqtSignal(int)  # 笔记选中信号 (note_id)
    note_created = pyqtSignal()  # 笔记创建信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notebookSidebar")
        self.setFixedWidth(250)
        self._notes_data = []
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(4)  # 减小间距
        layout.setContentsMargins(6, 6, 6, 6)  # 减小边距

        # 顶部工具栏（搜索框 + 新建按钮）
        top_layout = QHBoxLayout()
        top_layout.setSpacing(4)
        self._search_box = SearchLineEdit()
        self._search_box.setPlaceholderText("搜索笔记")
        self._search_box.textChanged.connect(self._filter_notes)
        top_layout.addWidget(self._search_box, 1)
        
        self._new_btn = ToolButton(CFIF.NOTEBOOK)
        self._new_btn.setToolTip("新建笔记")
        self._new_btn.setFixedSize(32, 32)  # 稍微缩小按钮
        self._new_btn.clicked.connect(self.note_created.emit)
        top_layout.addWidget(self._new_btn)
        
        layout.addLayout(top_layout)

        # 笔记列表
        self._note_list = QListWidget()
        self._note_list.setFrameShape(QListWidget.NoFrame)
        
        # 根据主题设置颜色
        if isDarkTheme():
            text_color = "#e6e6e6"
            hover_bg = "rgba(255, 255, 255, 0.08)"
            selected_bg = "rgba(0, 120, 215, 0.15)"
        else:
            text_color = "#333333"
            hover_bg = "rgba(0, 0, 0, 0.04)"
            selected_bg = "rgba(0, 120, 215, 0.08)"
        
        self._note_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                height: 32px;  /* 减小高度 */
                border-radius: 4px;
                padding: 4px 8px;  /* 减小内边距 */
                color: {text_color};
            }}
            QListWidget::item:hover {{
                background: {hover_bg};
            }}
            QListWidget::item:selected {{
                background: {selected_bg};
            }}
        """)
        self._note_list.itemClicked.connect(self._on_note_selected)
        layout.addWidget(self._note_list)

    def load_notes(self, notes: List[Dict[str, Any]]):
        """加载笔记列表"""
        self._notes_data = notes
        self._note_list.clear()
        for note in notes:
            item = QListWidgetItem(note['title'])
            item.setData(Qt.UserRole, note['id'])
            self._note_list.addItem(item)

    def _filter_notes(self, text: str):
        """过滤笔记"""
        for i in range(self._note_list.count()):
            item = self._note_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _on_note_selected(self, item: QListWidgetItem):
        """笔记选中事件"""
        note_id = item.data(Qt.UserRole)
        if note_id is not None:
            self.note_selected.emit(note_id)

    def get_selected_note_id(self) -> int:
        """获取选中的笔记 ID"""
        current_item = self._note_list.currentItem()
        return current_item.data(Qt.UserRole) if current_item else None
