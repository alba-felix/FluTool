"""工具集插件 - 管理和快速启动各类工具"""

from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QMenu, QAction, QHeaderView, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    setCustomStyleSheet, isDarkTheme, qconfig,
    MessageBoxBase, SubtitleLabel, TransparentToolButton,
    SingleDirectionScrollArea, ComboBox
)
from functools import partial
import subprocess
import sys
from pathlib import Path

from core import PluginInterface, SearchResult
from .service import ToolkitService


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
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)

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
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)

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


class Plugin(PluginInterface):
    """工具集插件"""

    PLUGIN_ID = "toolkit"
    PLUGIN_NAME = "工具集"
    PLUGIN_ICON = FIF.APPLICATION

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return ToolkitWidget(self.core, parent)

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
