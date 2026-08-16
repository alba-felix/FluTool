"""工具集插件 - 子插件容器，容纳外部工具管理与图片转换等工具"""

from typing import Optional, Dict, Any, List, Type
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QAction, QHeaderView, QApplication, QScrollArea, QStackedWidget, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QCursor
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    setCustomStyleSheet, isDarkTheme, qconfig,
    MessageBoxBase, SubtitleLabel, TransparentToolButton,
    SingleDirectionScrollArea, ComboBox, RoundMenu,
)
from functools import partial
import subprocess
import sys
from pathlib import Path

from core import PluginInterface, SearchResult
from .service import ToolkitService
from .page_interface import TabPageInterface
from .image_converter import ImageConverterPage


def get_app_data_path(relative_path: str) -> Path:
    """获取应用数据路径"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent.parent
    return base_path / relative_path


class ToolInputDialog(MessageBoxBase):
    """工具添加/编辑对话框"""

    def __init__(self, parent=None, tool_data: Dict[str, str] = None,
                 categories: List[str] = None, current_category: str = ""):
        super().__init__(parent)
        self.tool_data = tool_data or {}
        self.categories = categories or []
        self.current_category = current_category

        self.titleLabel = SubtitleLabel('添加工具', self)
        self.viewLayout.addWidget(self.titleLabel)

        self._setup_form()
        self._setup_buttons()

    def _setup_form(self) -> None:
        """构建表单"""
        self.name_input = LineEdit(self)
        self.name_input.setText(self.tool_data.get('name', ''))
        self.name_input.setPlaceholderText("工具名称")
        self.name_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.name_input)

        self.path_input = LineEdit(self)
        self.path_input.setText(self.tool_data.get('content', ''))
        self.path_input.setPlaceholderText("工具路径或命令")
        self.path_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.path_input)

        self.desc_input = LineEdit(self)
        self.desc_input.setText(self.tool_data.get('sub_title', ''))
        self.desc_input.setPlaceholderText("描述（可选）")
        self.desc_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.desc_input)

        if self.categories:
            self.category_combo = ComboBox(self)
            self.category_combo.addItems(self.categories)
            if self.current_category in self.categories:
                idx = self.category_combo.findText(self.current_category)
                if idx >= 0:
                    self.category_combo.setCurrentIndex(idx)
            self.viewLayout.addWidget(self.category_combo)

    def _setup_buttons(self) -> None:
        """设置按钮"""
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)

    def validate(self) -> bool:
        """验证表单"""
        return bool(self.name_input.text().strip() and self.path_input.text().strip())

    def get_tool_data(self) -> Dict[str, str]:
        """获取表单数据"""
        data = {
            "name": self.name_input.text().strip(),
            "content": self.path_input.text().strip(),
            "sub_title": self.desc_input.text().strip(),
        }
        if hasattr(self, 'category_combo'):
            data["category"] = self.category_combo.currentText()
        return data


class CategoryInputDialog(MessageBoxBase):
    """分类添加/编辑对话框"""

    def __init__(self, parent=None, title: str = "添加分类", default_name: str = ""):
        super().__init__(parent)

        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.name_input = LineEdit(self)
        self.name_input.setText(default_name)
        self.name_input.setPlaceholderText("分类名称")
        self.name_input.setClearButtonEnabled(True)
        self.name_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.name_input)

        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(300)

    def get_name(self) -> str:
        """获取分类名称"""
        return self.name_input.text().strip()

    def validate(self) -> bool:
        """验证表单"""
        return bool(self.get_name())


class ToolkitWidget(QWidget):
    """工具集主界面"""

    PLUGIN_ID = "toolkit"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = ToolkitService(self.PLUGIN_ID)
        self._current_category_id: Optional[int] = None
        self._current_category_name = "全部"
        self._category_buttons: List[PushButton] = []
        self._tools_cache: List[Dict[str, Any]] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.setObjectName("toolkitView")
        setCustomStyleSheet(
            self,
            "QWidget#toolkitView { background-color: transparent; }",
            "QWidget#toolkitView { background-color: transparent; }"
        )

        self._setup_toolbar(layout)
        self._setup_category_bar(layout)
        self._setup_tool_list(layout)
        self._setup_copy_label()

    def _setup_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """顶部工具栏"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.add_btn = PushButton("添加工具", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_tool)
        toolbar.addWidget(self.add_btn)

        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索工具...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_tools)
        toolbar.addWidget(self.search_edit, 1)

        parent_layout.addLayout(toolbar)

    def _setup_category_bar(self, parent_layout: QVBoxLayout) -> None:
        """分类标签栏"""
        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Horizontal)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(36)

        scroll_content = QWidget()
        scroll_content.setObjectName("categoryContent")
        setCustomStyleSheet(
            scroll_content,
            "QWidget#categoryContent { background-color: transparent; }",
            "QWidget#categoryContent { background-color: transparent; }"
        )

        self.category_layout = QHBoxLayout(scroll_content)
        self.category_layout.setContentsMargins(5, 2, 5, 2)
        self.category_layout.setSpacing(4)
        self.category_layout.setAlignment(Qt.AlignLeft)

        self.all_btn = PushButton("全部", self)
        self.all_btn.clicked.connect(self._show_all)
        self.category_layout.addWidget(self.all_btn)

        self.add_category_btn = TransparentToolButton(FIF.ADD, self)
        self.add_category_btn.setToolTip("添加分类")
        self.add_category_btn.clicked.connect(self._add_category)
        self.category_layout.addWidget(self.add_category_btn)
        self.category_layout.addStretch()

        self.scroll_area.setWidget(scroll_content)
        self.scroll_area.enableTransparentBackground()
        parent_layout.addWidget(self.scroll_area)

    def _setup_tool_list(self, parent_layout: QVBoxLayout) -> None:
        """工具列表"""
        tip_layout = QHBoxLayout()
        tip_layout.setContentsMargins(0, 0, 0, 0)
        self.tip_label = StrongBodyLabel("提示: 双击工具启动，右键更多操作")
        self.tip_label.setObjectName("tipLabel")
        setCustomStyleSheet(
            self.tip_label,
            "QLabel { color: gray; font-size: 9pt; }",
            "QLabel { color: #888; font-size: 9pt; }"
        )
        tip_layout.addWidget(self.tip_label)
        parent_layout.addLayout(tip_layout)

        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["名称", "描述", "路径"])
        self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnHidden(2, True)
        self._apply_tree_style()

        qconfig.themeChangedFinished.connect(self._apply_tree_style)
        self.tree.itemDoubleClicked.connect(self._launch_tool)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        parent_layout.addWidget(self.tree)

    def _setup_copy_label(self) -> None:
        """设置提示标签"""
        self.status_label = StrongBodyLabel("已启动", self)
        self.status_label.setObjectName("statusLabel")
        setCustomStyleSheet(
            self.status_label,
            "QLabel { background-color: rgba(0, 120, 212, 200); color: white; padding: 8px 16px; border-radius: 4px; }",
            "QLabel { background-color: rgba(0, 120, 212, 200); color: white; padding: 8px 16px; border-radius: 4px; }"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.hide()

    def _apply_tree_style(self) -> None:
        """应用树形列表样式"""
        header = self.tree.header()
        if isDarkTheme():
            header.setStyleSheet(
                "QHeaderView { background-color: transparent; }"
                "QHeaderView::section { background-color: #1f1f1f; color: #dddddd; border: none; padding: 6px 8px; }"
            )
            self.tree.setStyleSheet(
                "QTreeWidget { background-color: transparent; alternate-background-color: #252525; }"
                "QTreeWidget::item { padding: 4px; }"
                "QTreeWidget::item:selected { background-color: #0078d4; color: white; }"
            )
        else:
            header.setStyleSheet(
                "QHeaderView { background-color: transparent; }"
                "QHeaderView::section { background-color: #f5f5f5; color: #202020; border: none; padding: 6px 8px; }"
            )
            self.tree.setStyleSheet(
                "QTreeWidget { background-color: transparent; alternate-background-color: #f0f0f0; }"
                "QTreeWidget::item { padding: 4px; }"
                "QTreeWidget::item:selected { background-color: #0078d4; color: white; }"
            )
        self.tree.setAlternatingRowColors(True)

    def load_data(self) -> None:
        """加载数据"""
        self._load_categories()
        self._load_tools()

    def _load_categories(self) -> None:
        """加载分类按钮"""
        for btn in self._category_buttons:
            btn.deleteLater()
        self._category_buttons.clear()

        categories = self.service.list_categories()
        for cat in categories:
            btn = PushButton(cat['name'], self)
            btn.clicked.connect(partial(self._show_category, cat))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(partial(self._show_category_menu, cat))
            self.category_layout.insertWidget(self.category_layout.count() - 2, btn)
            self._category_buttons.append(btn)

    def _load_tools(self, category_id: int = None) -> None:
        """加载工具列表"""
        self.tree.clear()
        tools = self.service.list_tools(category_id)
        self._tools_cache = tools

        for idx, tool in enumerate(tools, 1):
            item = QTreeWidgetItem([
                tool['name'],
                tool.get('sub_title', ''),
                tool['content']
            ])
            item.setData(0, Qt.UserRole, tool['id'])
            self.tree.addTopLevelItem(item)

    def _show_all(self) -> None:
        """显示全部工具"""
        self._current_category_id = None
        self._current_category_name = "全部"
        self._load_tools()

    def _show_category(self, category: dict) -> None:
        """按分类筛选"""
        self._current_category_id = category['id']
        self._current_category_name = category['name']
        self._load_tools(category['id'])

    def _show_category_menu(self, category: dict, pos) -> None:
        """分类右键菜单"""
        menu = RoundMenu(parent=self)

        edit_action = QAction("编辑分类", self)
        edit_action.triggered.connect(partial(self._edit_category, category))
        menu.addAction(edit_action)

        delete_action = QAction("删除分类", self)
        delete_action.triggered.connect(partial(self._delete_category, category))
        menu.addAction(delete_action)

        menu.exec(QCursor.pos())

    def _add_category(self) -> None:
        """添加分类"""
        dialog = CategoryInputDialog(self, "添加分类")
        if dialog.exec():
            name = dialog.get_name()
            if name:
                self.service.add_category(name)
                self._load_categories()
                InfoBar.success(
                    title="成功",
                    content=f"分类 '{name}' 已添加",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def _edit_category(self, category: dict) -> None:
        """编辑分类"""
        dialog = CategoryInputDialog(self, "编辑分类", category['name'])
        if dialog.exec():
            name = dialog.get_name()
            if name and name != category['name']:
                self.service.update_category(category['id'], name)
                self._load_categories()
                InfoBar.success(
                    title="成功",
                    content=f"分类已更新为 '{name}'",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def _delete_category(self, category: dict) -> None:
        """删除分类"""
        from qfluentwidgets import MessageBox
        box = MessageBox("确认删除", f"确定要删除分类 '{category['name']}' 吗？\n该分类下的工具将移至未分类。", self)
        if box.exec():
            self.service.delete_category(category['id'])
            self._load_categories()
            if self._current_category_id == category['id']:
                self._show_all()
            InfoBar.success(
                title="成功",
                content=f"分类 '{category['name']}' 已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _add_tool(self) -> None:
        """添加工具"""
        categories = self.service.list_category_names()
        dialog = ToolInputDialog(
            self,
            categories=categories,
            current_category=self._current_category_name if self._current_category_id else ""
        )
        if dialog.exec():
            data = dialog.get_tool_data()
            self.service.add_tool(
                name=data['name'],
                content=data['content'],
                sub_title=data.get('sub_title', ''),
                category_name=data.get('category', '')
            )
            self._load_tools(self._current_category_id)
            InfoBar.success(
                title="成功",
                content=f"工具 '{data['name']}' 已添加",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _edit_tool(self, tool_id: int) -> None:
        """编辑工具"""
        tool = next((t for t in self._tools_cache if t['id'] == tool_id), None)
        if not tool:
            return

        categories = self.service.list_category_names()
        dialog = ToolInputDialog(
            self,
            tool_data=tool,
            categories=categories,
            current_category=tool.get('category_name', '')
        )
        dialog.titleLabel.setText('编辑工具')

        if dialog.exec():
            data = dialog.get_tool_data()
            self.service.update_tool(
                tool_id,
                name=data['name'],
                content=data['content'],
                sub_title=data.get('sub_title', ''),
                category_name=data.get('category', '')
            )
            self._load_tools(self._current_category_id)
            InfoBar.success(
                title="成功",
                content=f"工具 '{data['name']}' 已更新",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _delete_tool(self, tool_id: int) -> None:
        """删除工具"""
        from qfluentwidgets import MessageBox
        tool = next((t for t in self._tools_cache if t['id'] == tool_id), None)
        if not tool:
            return

        box = MessageBox("确认删除", f"确定要删除工具 '{tool['name']}' 吗？", self)
        if box.exec():
            self.service.delete_tool(tool_id)
            self._load_tools(self._current_category_id)
            InfoBar.success(
                title="成功",
                content=f"工具 '{tool['name']}' 已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _launch_tool(self, item: QTreeWidgetItem) -> None:
        """启动工具"""
        path = item.text(2)
        if not path:
            return

        try:
            subprocess.Popen(path, shell=True)
            self._show_status("已启动")
        except Exception as e:
            InfoBar.error(
                title="启动失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _show_context_menu(self, pos) -> None:
        """右键菜单"""
        item = self.tree.itemAt(pos)
        if not item:
            return

        tool_id = item.data(0, Qt.UserRole)
        menu = RoundMenu(parent=self)

        launch_action = QAction("启动", self)
        launch_action.triggered.connect(lambda: self._launch_tool(item))
        menu.addAction(launch_action)

        menu.addSeparator()

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self._edit_tool(tool_id))
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_tool(tool_id))
        menu.addAction(delete_action)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _filter_tools(self, text: str) -> None:
        """搜索过滤"""
        query = text.lower().strip()
        self.tree.clear()

        if not query:
            self._load_tools(self._current_category_id)
            return

        for tool in self._tools_cache:
            if (query in tool['name'].lower() or
                query in tool.get('sub_title', '').lower() or
                query in tool['content'].lower()):
                item = QTreeWidgetItem([
                    tool['name'],
                    tool.get('sub_title', ''),
                    tool['content']
                ])
                item.setData(0, Qt.UserRole, tool['id'])
                self.tree.addTopLevelItem(item)

    def _show_status(self, message: str) -> None:
        """显示状态提示"""
        self.status_label.setText(message)
        self.status_label.adjustSize()
        x = (self.width() - self.status_label.width()) // 2
        y = (self.height() - self.status_label.height()) // 2
        self.status_label.move(x, y)
        self.status_label.show()
        self.status_label.raise_()

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self.status_label.hide)


class ExternalToolsPage(TabPageInterface):
    """外部工具管理页面 - 包装原 ToolkitWidget"""

    page_id = "external_tools"
    page_name = "外部工具"

    @classmethod
    def create(cls, parent=None, core=None) -> QWidget:
        widget = ToolkitWidget(core, parent)
        return widget


class OverflowPopup(QWidget):
    """溢出标签页弹出窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._click_callback = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedWidth(300)
        self.setMaximumHeight(600)

        self._main_frame = QFrame(self)
        self._main_frame.setObjectName("overflowMainFrame")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_frame)

        frame_layout = QVBoxLayout(self._main_frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)
        frame_layout.setSpacing(2)

        scroll_area = QScrollArea(self._main_frame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        frame_layout.addWidget(scroll_area)

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        scroll_area.setWidget(self._list_widget)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_style()

    def _apply_style(self) -> None:
        if isDarkTheme():
            self._main_frame.setStyleSheet("""
                QFrame#overflowMainFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self._main_frame.setStyleSheet("""
                QFrame#overflowMainFrame {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """)

    def show_tabs(self, tabs: List[Dict[str, Any]], on_click_callback) -> None:
        self._click_callback = on_click_callback

        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for tab in tabs:
            btn = PushButton(tab['text'], self._list_widget)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, t=tab: self._on_tab_click(t))
            self._list_layout.addWidget(btn)

        self.adjustSize()

    def _on_tab_click(self, tab: Dict[str, Any]) -> None:
        self.hide()
        if self._click_callback:
            self._click_callback(tab)

    def show_at(self, global_pos: QPoint, max_height: int) -> None:
        self.setMaximumHeight(min(max_height, 600))
        self.adjustSize()

        x = global_pos.x() - self.width()
        y = global_pos.y()

        screen = QApplication.screenAt(global_pos)
        if screen:
            screen_rect = screen.availableGeometry()
            if x < screen_rect.left():
                x = screen_rect.left()
            if y + self.height() > screen_rect.bottom():
                y = screen_rect.bottom() - self.height()

        self.move(x, y)
        self.show()
        self.setFocus()


class CustomTabBar(QWidget):
    """自定义标签页栏"""

    currentChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tabs: List[Dict[str, Any]] = []
        self._current_index = 0
        self._visible_count = 0
        self._hidden_start = 0
        self._hidden_end = 0
        self._overflow_popup: Optional[OverflowPopup] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setFixedHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)

        self._tab_container = QWidget(self)
        self._tab_layout = QHBoxLayout(self._tab_container)
        self._tab_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_layout.setSpacing(2)
        self._tab_layout.addStretch()
        layout.addWidget(self._tab_container, 1)

        self._overflow_btn = TransparentToolButton(FIF.MORE, self)
        self._overflow_btn.setFixedSize(36, 36)
        self._overflow_btn.setToolTip("更多标签页")
        self._overflow_btn.clicked.connect(self._show_overflow)
        self._overflow_btn.hide()
        layout.addWidget(self._overflow_btn)

    def addTab(self, page_id: str, text: str) -> int:
        """添加标签页，返回页面索引"""
        page_index = len(self._tabs)
        self._tabs.append({
            'page_id': page_id,
            'text': text,
            'widget_index': page_index,
            'button': None
        })
        self._update_visible_tabs()
        return page_index

    def _update_visible_tabs(self) -> None:
        while self._tab_layout.count() > 1:
            item = self._tab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        n = len(self._tabs)
        if n == 0:
            self._visible_count = 0
            self._hidden_start = 0
            self._hidden_end = 0
            self._overflow_btn.hide()
            return

        # 预估每个标签按钮宽度（从后往前累计，确定可见数量）
        widths = []
        for tab in self._tabs:
            btn = PushButton(tab['text'], self)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(64)
            btn.setMaximumWidth(150)
            btn.adjustSize()
            widths.append(btn.width() + 2)
            btn.deleteLater()

        # 溢出按钮 + 边距预留 50px
        available = max(0, self.width() - 50 - 50)
        visible_count = 0
        acc = 0
        for w in reversed(widths):
            if acc + w <= available:
                acc += w
                visible_count += 1
            else:
                break
        visible_count = max(1, min(visible_count, n))
        self._visible_count = visible_count

        # 可见区起点：保证当前选中项可见，其余隐藏"上面的"标签（靠前的进溢出菜单）
        default_start = n - visible_count
        start = min(self._current_index, default_start)
        self._hidden_start = start
        self._hidden_end = start + visible_count

        # 渲染可见按钮
        for i in range(start, start + visible_count):
            tab = self._tabs[i]
            btn = PushButton(tab['text'], self)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(64)
            btn.setMaximumWidth(150)
            btn.setCheckable(True)
            btn.setChecked(i == self._current_index)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_tab_click(idx))
            self._tab_layout.insertWidget(self._tab_layout.count() - 1, btn)
            tab['button'] = btn

        for i, tab in enumerate(self._tabs):
            if not (start <= i < start + visible_count):
                tab['button'] = None

        hidden_count = n - visible_count
        self._overflow_btn.setVisible(hidden_count > 0)

    def _on_tab_click(self, index: int) -> None:
        self.setCurrentIndex(index)

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self._current_index = index
            self._update_visible_tabs()
            widget_index = self._tabs[index]['widget_index']
            self.currentChanged.emit(widget_index)

    def _show_overflow(self) -> None:
        hidden_tabs = self._tabs[:self._hidden_start] + self._tabs[self._hidden_end:]
        if not hidden_tabs:
            return

        if self._overflow_popup is None:
            self._overflow_popup = OverflowPopup()

        main_window = self.window()
        max_height = main_window.height() - 100 if main_window else 400
        btn_pos = self._overflow_btn.mapToGlobal(QPoint(0, self._overflow_btn.height()))

        self._overflow_popup.show_tabs(hidden_tabs, self._on_overflow_tab_click)
        self._overflow_popup.show_at(btn_pos, max_height)

    def _on_overflow_tab_click(self, tab: Dict[str, Any]) -> None:
        """点击溢出菜单中的标签：保持标签顺序不变，仅把可见窗口移到该标签处"""
        clicked_index = self._tabs.index(tab)
        self.setCurrentIndex(clicked_index)

    def wheelEvent(self, event) -> None:
        """滚轮上下滑动可见窗口，选中项随之移动"""
        delta = event.angleDelta().y()
        if delta == 0 or not self._tabs:
            return
        step = 1 if delta < 0 else -1
        new_index = self._current_index + step
        if 0 <= new_index < len(self._tabs):
            self.setCurrentIndex(new_index)
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_visible_tabs)


class TabManager:
    """标签页管理器 - 管理所有标签页的注册和创建"""

    def __init__(self):
        self._pages: List[Type[TabPageInterface]] = []

    def register(self, page_class: Type[TabPageInterface]) -> None:
        """注册标签页"""
        self._pages.append(page_class)

    def get_pages(self) -> List[Type[TabPageInterface]]:
        """获取所有已注册的标签页"""
        return self._pages.copy()

    def create_all(self, parent=None, core=None) -> List[QWidget]:
        """创建所有标签页内容"""
        return [page.create(parent, core=core) for page in self._pages]


class SubPluginWidget(QWidget):
    """子插件主界面"""

    PLUGIN_ID = "toolkit"

    def __init__(self, core, tab_manager: TabManager, parent=None):
        super().__init__(parent)
        self.core = core
        self._tab_manager = tab_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setObjectName("subPluginView")
        self.setStyleSheet("QWidget#subPluginView { background-color: transparent; }")

        self.tab_bar = CustomTabBar(self)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_bar)

        # 标签页下方水平分隔线
        self._separator = QFrame(self)
        self._separator.setFrameShape(QFrame.HLine)
        self._separator.setFixedHeight(1)
        self._separator.setObjectName("tabSeparator")
        layout.addWidget(self._separator)

        # 创建滚动区域包裹 stacked_widget，启用双向滚动但不显示滚动条
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self._scroll_area.viewport().setStyleSheet("background: transparent; border: none;")

        # 创建容器放置 stacked_widget
        self._scroll_container = QWidget()
        self._scroll_container_layout = QVBoxLayout(self._scroll_container)
        self._scroll_container_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_container_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget(self._scroll_container)
        self._scroll_container_layout.addWidget(self.stacked_widget)

        self._scroll_area.setWidget(self._scroll_container)
        layout.addWidget(self._scroll_area)

        self._init_tabs()
        self._apply_separator_style()

        qconfig.themeChangedFinished.connect(lambda: QTimer.singleShot(0, self._apply_separator_style))

    def _on_tab_changed(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)

    def _apply_separator_style(self) -> None:
        if isDarkTheme():
            self._separator.setStyleSheet("QFrame#tabSeparator { background-color: #3d3d3d; border: none; }")
        else:
            self._separator.setStyleSheet("QFrame#tabSeparator { background-color: #e0e0e0; border: none; }")

    def _init_tabs(self) -> None:
        """初始化所有已注册的标签页"""
        pages = self._tab_manager.get_pages()
        widgets = self._tab_manager.create_all(self, core=self.core)

        for page_class, widget in zip(pages, widgets):
            self.tab_bar.addTab(page_class.page_id, page_class.page_name)
            widget.setStyleSheet("background-color: transparent;")
            self.stacked_widget.addWidget(widget)

        if widgets:
            self.stacked_widget.setCurrentIndex(0)


class Plugin(PluginInterface):
    """工具集插件 - 子插件容器"""

    PLUGIN_ID = "toolkit"
    PLUGIN_NAME = "工具集"
    PLUGIN_ICON = FIF.APPLICATION
    PLUGIN_HIDDEN = False

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

        self._tab_manager = TabManager()
        # 在这里注册工具集的标签页
        self._tab_manager.register(ExternalToolsPage)
        self._tab_manager.register(ImageConverterPage)

        self._widget = None

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        if self._widget is None:
            self._widget = SubPluginWidget(self.core, self._tab_manager, parent)
        return self._widget

    def supports_search(self) -> bool:
        return True

    def search(self, query: str):
        """全局搜索"""
        results = []
        tools = ToolkitService(self.PLUGIN_ID).search_tools(query)

        for tool in tools[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=tool['name'],
                description=tool.get('sub_title', '') or tool['content'],
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in tool['name'].lower() else 0.5,
                action=lambda t=tool: self._launch_tool_from_search(t),
                metadata={'tool_id': tool['id']}
            )
            results.append(result)
        return results

    def _launch_tool_from_search(self, tool: dict) -> None:
        """从搜索结果启动工具"""
        try:
            subprocess.Popen(tool['content'], shell=True)
        except Exception as e:
            self.core.logger.error(f"启动工具失败: {e}")
