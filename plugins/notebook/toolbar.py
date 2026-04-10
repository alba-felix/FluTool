"""随手记工具栏 - 格式化和操作按钮"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout
from qfluentwidgets import ComboBox, SpinBox, ToolButton, FluentIcon as FIF, ToggleToolButton
from ui import CustomFluentIcon as CFIF


class NotebookToolBar(QWidget):
    """工具栏组件"""

    new_note_signal = pyqtSignal()
    save_note_signal = pyqtSignal()
    delete_note_signal = pyqtSignal()
    export_note_signal = pyqtSignal()
    format_note_signal = pyqtSignal(str)
    doc_info_signal = pyqtSignal()
    find_signal = pyqtSignal()
    replace_signal = pyqtSignal()
    font_changed = pyqtSignal(str)
    font_size_changed = pyqtSignal(int)
    wrap_toggled = pyqtSignal(bool)
    quick_replace_toggled = pyqtSignal(bool)
    list_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notebookToolBar")
        self.setFixedHeight(40)
        self.setStyleSheet("""
            NotebookToolBar {
                background: transparent;
            }
        """)
        self._setup_ui()
        self._connect_signals()
    
    def _connect_signals(self):
        """连接信号"""
        self._font_combo.currentTextChanged.connect(self.font_changed.emit)
        self._size_combo.currentTextChanged.connect(lambda text: self.font_size_changed.emit(int(text)))

    def _setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 4, 8, 4)

        self._type_combo = ComboBox()
        self._type_combo.addItems(["markdown", "plain", "sql", "json", "xml", "python", "java", "html"])
        self._type_combo.setCurrentText("markdown")
        self._type_combo.setFixedWidth(100)
        layout.addWidget(self._type_combo)

        self._font_combo = ComboBox()
        self._font_combo.addItems([
            "楷体", "宋体", "黑体", "微软雅黑",
            "Consolas", "Courier New", "Arial",
            "Times New Roman", "Verdana", "Tahoma"
        ])
        self._font_combo.setCurrentText("楷体")
        self._font_combo.setFixedWidth(100)
        layout.addWidget(self._font_combo)

        self._size_combo = ComboBox()
        self._size_combo.addItems([str(i) for i in range(7, 33)])
        self._size_combo.setCurrentText("13")
        self._size_combo.setFixedWidth(65)
        layout.addWidget(self._size_combo)

        layout.addSpacing(8)

        self._quick_replace_btn = ToggleToolButton(FIF.SETTING)
        self._quick_replace_btn.setToolTip("快捷替换面板")
        self._quick_replace_btn.toggled.connect(self.quick_replace_toggled.emit)
        layout.addWidget(self._quick_replace_btn)

        self._list_btn = ToggleToolButton(FIF.MENU)
        self._list_btn.setToolTip("显示/隐藏列表")
        self._list_btn.setChecked(True)
        self._list_btn.toggled.connect(self.list_toggled.emit)
        layout.addWidget(self._list_btn)

        self._ul_btn = ToolButton(CFIF.NOTEBOOK_LIST)
        self._ul_btn.setToolTip("无序列表")
        self._ul_btn.clicked.connect(lambda: self.format_note_signal.emit("ul"))
        layout.addWidget(self._ul_btn)

        self._ol_btn = ToolButton(CFIF.ISLIST)
        self._ol_btn.setToolTip("有序列表")
        self._ol_btn.clicked.connect(lambda: self.format_note_signal.emit("ol"))
        layout.addWidget(self._ol_btn)

        self._wrap_btn = ToggleToolButton(CFIF.LINE_WRAPPINGING)
        self._wrap_btn.setToolTip("自动换行")
        self._wrap_btn.toggled.connect(self.wrap_toggled.emit)
        layout.addWidget(self._wrap_btn)

        self._new_btn = ToolButton(FIF.ADD_TO)
        self._new_btn.setToolTip("新建笔记")
        self._new_btn.clicked.connect(self.new_note_signal.emit)
        layout.addWidget(self._new_btn)

        self._find_btn = ToolButton(FIF.SEARCH)
        self._find_btn.setToolTip("查找 (Ctrl+F)")
        self._find_btn.clicked.connect(self.find_signal.emit)
        layout.addWidget(self._find_btn)

        self._save_btn = ToolButton(FIF.SAVE)
        self._save_btn.setToolTip("保存 (Ctrl+S)")
        self._save_btn.clicked.connect(self.save_note_signal.emit)
        layout.addWidget(self._save_btn)

        self._delete_btn = ToolButton(FIF.DELETE)
        self._delete_btn.setToolTip("删除")
        self._delete_btn.clicked.connect(self.delete_note_signal.emit)
        layout.addWidget(self._delete_btn)

        self._export_btn = ToolButton(FIF.SHARE)
        self._export_btn.setToolTip("导出")
        self._export_btn.clicked.connect(self.export_note_signal.emit)
        layout.addWidget(self._export_btn)

        self._format_btn = ToolButton(FIF.FONT_SIZE)
        self._format_btn.setToolTip("格式化代码")
        self._format_btn.clicked.connect(lambda: self.format_note_signal.emit("format"))
        layout.addWidget(self._format_btn)

        self._info_btn = ToolButton(FIF.INFO)
        self._info_btn.setToolTip("文档信息")
        self._info_btn.clicked.connect(self.doc_info_signal.emit)
        layout.addWidget(self._info_btn)

        self._replace_btn = ToolButton(FIF.SYNC)
        self._replace_btn.setToolTip("替换 (Ctrl+H)")
        self._replace_btn.clicked.connect(self.replace_signal.emit)
        layout.addWidget(self._replace_btn)

        layout.addStretch(1)
    
    def get_note_type(self) -> str:
        """获取笔记类型"""
        return self._type_combo.currentText()
    
    def set_note_type(self, note_type: str):
        """设置笔记类型"""
        self._type_combo.setCurrentText(note_type)
    
    def set_wrap_state(self, wrapped: bool):
        """设置换行状态"""
        self._wrap_btn.setChecked(wrapped)
    
    def set_font_size(self, size: int):
        """设置字体大小"""
        self._size_combo.setCurrentText(str(size))
