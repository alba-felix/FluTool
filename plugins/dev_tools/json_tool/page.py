"""JSON 工具页面"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QSplitter, QFrame, QApplication,
)
from qfluentwidgets import (
    FluentIcon as FIF, PushButton, ComboBox, InfoBar, InfoBarPosition,
    BodyLabel, isDarkTheme, qconfig,
)
from qfluentwidgets.components.widgets.menu import TextEditMenu

from ..page_interface import TabPageInterface
from .json_highlighter import JsonHighlighter
from .json_service import JsonService


class FluentTextEdit(QTextEdit):
    """带 Fluent 风格右键菜单的文本编辑器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 强制纯文本粘贴，避免保留来源格式导致样式错乱
        self.setAcceptRichText(False)

    def contextMenuEvent(self, event) -> None:
        menu = TextEditMenu(self)
        menu.exec_(event.globalPos())


class JsonToolWidget(QWidget):
    """JSON 工具主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = JsonService()
        self._highlighters: list = []
        self._setup_ui()
        self._apply_theme()
        qconfig.themeChangedFinished.connect(self._apply_theme)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # 顶部操作栏 1：核心操作
        bar1 = QHBoxLayout()
        bar1.setSpacing(8)

        self.format_btn = PushButton("格式化", self)
        self.format_btn.setIcon(FIF.EDIT)
        self.format_btn.clicked.connect(self._format)
        bar1.addWidget(self.format_btn)

        self.minify_btn = PushButton("压缩", self)
        self.minify_btn.setIcon(FIF.TILES)
        self.minify_btn.clicked.connect(self._minify)
        bar1.addWidget(self.minify_btn)

        self.validate_btn = PushButton("校验", self)
        self.validate_btn.setIcon(FIF.CHECKBOX)
        self.validate_btn.clicked.connect(self._validate)
        bar1.addWidget(self.validate_btn)

        self.sort_btn = PushButton("排序键", self)
        self.sort_btn.setIcon(FIF.FILTER)
        self.sort_btn.clicked.connect(self._sort_keys)
        bar1.addWidget(self.sort_btn)

        self.paths_btn = PushButton("提取路径", self)
        self.paths_btn.setIcon(FIF.SEARCH)
        self.paths_btn.clicked.connect(self._extract_paths)
        bar1.addWidget(self.paths_btn)

        bar1.addStretch()
        layout.addLayout(bar1)

        # 顶部操作栏 2：字符串处理与工具
        bar2 = QHBoxLayout()
        bar2.setSpacing(8)

        self.escape_btn = PushButton("转义", self)
        self.escape_btn.clicked.connect(self._escape)
        bar2.addWidget(self.escape_btn)

        self.unescape_btn = PushButton("反转义", self)
        self.unescape_btn.clicked.connect(self._unescape)
        bar2.addWidget(self.unescape_btn)

        bar2.addSpacing(16)
        bar2.addWidget(BodyLabel("缩进:", self))

        self.indent_combo = ComboBox(self)
        self.indent_combo.addItems(["2", "4"])
        self.indent_combo.currentIndexChanged.connect(self._on_indent_changed)
        bar2.addWidget(self.indent_combo)

        bar2.addStretch()

        self.copy_btn = PushButton("复制结果", self)
        self.copy_btn.setIcon(FIF.COPY)
        self.copy_btn.clicked.connect(self._copy_output)
        bar2.addWidget(self.copy_btn)

        self.clear_btn = PushButton("清空", self)
        self.clear_btn.setIcon(FIF.DELETE)
        self.clear_btn.clicked.connect(self._clear_all)
        bar2.addWidget(self.clear_btn)

        layout.addLayout(bar2)

        # 分隔线
        separator = QFrame(self)
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setObjectName("jsonSeparator")
        layout.addWidget(separator)

        # 输入 / 输出区
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)

        input_panel, self.input_edit = self._build_editor_panel("输入 JSON", self, enable_highlight=True)
        splitter.addWidget(input_panel)

        output_panel, self.output_edit = self._build_editor_panel("输出结果", self, enable_highlight=False)
        self.output_edit.setReadOnly(True)
        splitter.addWidget(output_panel)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter, 1)

        # 底部状态栏
        self.status_label = BodyLabel("就绪", self)
        layout.addWidget(self.status_label)

    def _build_editor_panel(self, title: str, parent: QWidget, enable_highlight: bool = False):
        """构建带标题的编辑面板，返回 (面板, 编辑器)

        :param enable_highlight: 是否挂载 JSON 语法高亮器（仅输入框启用，输出框只读无需高亮）
        """
        panel = QWidget(parent)
        v_layout = QVBoxLayout(panel)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(4)

        title_label = BodyLabel(title, panel)
        v_layout.addWidget(title_label)

        editor = FluentTextEdit(panel)
        mono_font = QFont("Consolas")
        mono_font.setPointSize(11)
        editor.setFont(mono_font)
        editor.setLineWrapMode(QTextEdit.NoWrap)
        editor.setObjectName("jsonEditor")
        if enable_highlight:
            self._highlighters.append(JsonHighlighter(editor.document()))
        v_layout.addWidget(editor, 1)
        return panel, editor

    def _apply_theme(self) -> None:
        """根据主题应用编辑区样式"""
        if isDarkTheme():
            qss = (
                "QTextEdit#jsonEditor { background-color: #1e1e1e; "
                "border: 1px solid #3d3d3d; border-radius: 6px; "
                "color: #e0e0e0; padding: 8px; }"
                "QFrame#jsonSeparator { background-color: #3d3d3d; border: none; }"
            )
        else:
            qss = (
                "QTextEdit#jsonEditor { background-color: #ffffff; "
                "border: 1px solid #e0e0e0; border-radius: 6px; "
                "color: #333333; padding: 8px; }"
                "QFrame#jsonSeparator { background-color: #e0e0e0; border: none; }"
            )
        self.setStyleSheet(qss)

    # ============ 操作处理 ============

    def _on_indent_changed(self, index: int) -> None:
        self.service.set_indent(int(self.indent_combo.currentText()))

    def _run_operation(self, op) -> None:
        """统一执行操作：读输入 → 调 service → 写输出或提示"""
        text = self.input_edit.toPlainText()
        ok, result = op(text)
        if ok:
            self.output_edit.setPlainText(result)
            lines = len(result.splitlines()) if result else 0
            self.status_label.setText(f"完成，输出 {lines} 行")
        else:
            self.status_label.setText(result)
            InfoBar.error(
                title="操作失败", content=result,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self,
            )

    def _format(self):
        self._run_operation(self.service.format_json)

    def _minify(self):
        self._run_operation(self.service.minify_json)

    def _validate(self):
        text = self.input_edit.toPlainText()
        ok, result = self.service.validate_json(text)
        self.status_label.setText(result)
        if ok:
            InfoBar.success(
                title="校验通过", content=result,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP_RIGHT, duration=2000, parent=self,
            )
        else:
            InfoBar.error(
                title="校验失败", content=result,
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP_RIGHT, duration=3000, parent=self,
            )

    def _sort_keys(self):
        self._run_operation(self.service.sort_keys)

    def _extract_paths(self):
        self._run_operation(self.service.extract_paths)

    def _escape(self):
        self._run_operation(self.service.escape_string)

    def _unescape(self):
        self._run_operation(self.service.unescape_string)

    def _copy_output(self):
        text = self.output_edit.toPlainText()
        if not text:
            self.status_label.setText("没有可复制的内容")
            return
        QApplication.clipboard().setText(text)
        self.status_label.setText(f"已复制 {len(text)} 字符")

    def _clear_all(self):
        self.input_edit.clear()
        self.output_edit.clear()
        self.status_label.setText("已清空")


class JsonToolPage(TabPageInterface):
    """JSON 工具标签页"""

    page_id = "json_tool"
    page_name = "JSON 工具"
    page_icon = FIF.EMBED

    @classmethod
    def create(cls, parent=None, core=None) -> QWidget:
        return JsonToolWidget(parent)
