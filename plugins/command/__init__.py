from typing import Optional, Dict, Any, List
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QMenu, QAction,
    QFormLayout, QHeaderView, QApplication, QLabel
)
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, TextEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    ProgressBar, TransparentToolButton, SingleDirectionScrollArea,
    setCustomStyleSheet, isDarkTheme, qconfig, MessageBoxBase,
    SubtitleLabel, ComboBox, CaptionLabel, MessageBox
)
from core import PluginInterface
from storage import DatabaseManager
from functools import partial


class InputDialog(MessageBoxBase):
    """Fluent 风格输入对话框"""
    
    def __init__(self, title: str, label: str, default_text: str = "", parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self.input_edit = LineEdit(self)
        self.input_edit.setText(default_text)
        self.input_edit.setPlaceholderText(label)
        self.input_edit.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.input_edit)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(350)
        
        self.input_edit.setFocus()
    
    def get_text(self) -> str:
        return self.input_edit.text().strip()


class CommandDialog(MessageBoxBase):
    """命令添加/编辑对话框"""
    
    def __init__(self, parent=None, command_name: str = "", 
                 command_content: str = "", sub_title: str = "",
                 categories: List[str] = None, current_category: str = ""):
        super().__init__(parent)
        self.categories = categories or []
        self.current_category = current_category
        
        self.titleLabel = SubtitleLabel('添加/编辑命令', self)
        self.viewLayout.addWidget(self.titleLabel)
        
        formLayout = QFormLayout()
        
        self.name_input = LineEdit(self)
        self.name_input.setText(command_name)
        self.name_input.setPlaceholderText("请输入命令名称")
        self.name_input.setClearButtonEnabled(True)
        formLayout.addRow("命令名称:", self.name_input)
        
        self.sub_title_input = LineEdit(self)
        self.sub_title_input.setText(sub_title)
        self.sub_title_input.setPlaceholderText("可选")
        self.sub_title_input.setClearButtonEnabled(True)
        formLayout.addRow("次标题:", self.sub_title_input)
        
        self.content_input = TextEdit(self)
        self.content_input.setPlainText(command_content)
        self.content_input.setPlaceholderText("请输入命令内容")
        self.content_input.setFixedHeight(120)
        formLayout.addRow("命令内容:", self.content_input)
        
        if self.categories:
            self.category_combo = ComboBox(self)
            self.category_combo.addItems(self.categories)
            if current_category in self.categories:
                index = self.category_combo.findText(current_category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            formLayout.addRow("分类:", self.category_combo)
        
        self.viewLayout.addLayout(formLayout)
        
        self.yesButton.setText("确定")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(450)
    
    def validate(self) -> bool:
        """验证表单数据"""
        if not self.name_input.text().strip():
            return False
        if not self.content_input.toPlainText().strip():
            return False
        return True
    
    def get_command_data(self) -> Dict[str, str]:
        """获取输入的命令数据"""
        data = {
            "name": self.name_input.text().strip(),
            "sub_title": self.sub_title_input.text().strip(),
            "content": self.content_input.toPlainText()
        }
        if hasattr(self, 'category_combo'):
            data["category"] = self.category_combo.currentText()
        return data


class CommandLoader(QThread):
    """异步命令加载器"""
    
    load_finished = pyqtSignal(list)
    load_progress = pyqtSignal(int)
    load_error = pyqtSignal(str)
    
    def __init__(self, db: DatabaseManager, plugin_id: str):
        super().__init__()
        self.db = db
        self.plugin_id = plugin_id
    
    def run(self):
        """异步加载命令数据"""
        try:
            self.load_progress.emit(10)
            self.load_progress.emit(30)
            
            commands = self.db.get_commands(self.plugin_id)
            self.load_progress.emit(60)
            
            categories = self.db.get_categories(self.plugin_id)
            self.load_progress.emit(100)
            
            self.load_finished.emit(commands)
        except Exception as e:
            self.load_error.emit(f"加载命令数据时出错: {e}")


class CommandWidget(QWidget):
    """命令管理界面"""
    
    PLUGIN_ID = "command"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self._current_category_id: Optional[int] = None
        self._current_category_name = "全部"
        self._category_buttons: List[PushButton] = []
        self._is_loading = False
        self._commands_cache: List[Dict[str, Any]] = []
        self._loader: Optional[CommandLoader] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.progress_bar = ProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.scroll_area = SingleDirectionScrollArea(self, orient=Qt.Horizontal)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(40)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("categoryContent")
        setCustomStyleSheet(
            scroll_content,
            "QWidget#categoryContent { background-color: transparent; }",
            "QWidget#categoryContent { background-color: transparent; }"
        )
        self.category_layout = QHBoxLayout(scroll_content)
        self.category_layout.setContentsMargins(10, 5, 10, 5)
        self.category_layout.setSpacing(5)
        self.category_layout.setAlignment(Qt.AlignLeft)
        self.scroll_area.setWidget(scroll_content)
        self.scroll_area.enableTransparentBackground()
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.viewport().setStyleSheet("background: transparent;")
        
        setCustomStyleSheet(
            self.scroll_area,
            """
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            """,
            """
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
            """
        )
        layout.addWidget(self.scroll_area)
        
        self.all_btn = PushButton("全部", self)
        self.all_btn.clicked.connect(self._show_all)
        self.category_layout.addWidget(self.all_btn)
        
        self.add_category_btn = TransparentToolButton(FIF.ADD, self)
        self.add_category_btn.setToolTip("添加分类")
        self.add_category_btn.clicked.connect(self._add_category)
        self.category_layout.addWidget(self.add_category_btn)
        self.category_layout.addStretch()
        
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 5, 10, 5)
        top_layout.setSpacing(10)
        
        self.add_btn = PushButton("添加命令", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_command)
        top_layout.addWidget(self.add_btn)
        
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索命令...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._search_commands)
        top_layout.addWidget(self.search_edit)
        layout.addLayout(top_layout)
        
        tip_layout = QHBoxLayout()
        tip_layout.setContentsMargins(10, 0, 10, 5)
        self.tip_label = QLabel("提示: 双击命令复制到剪贴板")
        self.tip_label.setObjectName("tipLabel")
        setCustomStyleSheet(
            self.tip_label,
            "QLabel { color: gray; font-size: 9pt; }",
            "QLabel { color: #888; font-size: 9pt; }"
        )
        tip_layout.addWidget(self.tip_label)
        layout.addLayout(tip_layout)
        
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["序号", "名称", "次标题", "分类", "命令内容"])
        self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 100)
        self.tree.setColumnWidth(3, 100)
        self.tree.setColumnHidden(0, True)
        self._apply_header_style()
        qconfig.themeChangedFinished.connect(self._apply_header_style)
        self.tree.itemDoubleClicked.connect(self._copy_command)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree)
        
        self.copy_label = QLabel("已复制到剪贴板", self)
        self.copy_label.setObjectName("copyLabel")
        setCustomStyleSheet(
            self.copy_label,
            "QLabel { background-color: rgba(0, 120, 212, 200); color: white; padding: 8px 16px; border-radius: 4px; font-size: 12px; }",
            "QLabel { background-color: rgba(0, 120, 212, 200); color: white; padding: 8px 16px; border-radius: 4px; font-size: 12px; }"
        )
        self.copy_label.setAlignment(Qt.AlignCenter)
        self.copy_label.hide()
        
        self._set_ui_enabled(False)

    def _apply_header_style(self) -> None:
        """应用树形列表样式，包括表头和交替行颜色"""
        if not hasattr(self, "tree"):
            return
        
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
        """加载命令数据"""
        if self._loader and self._loader.isRunning():
            return
        
        self._is_loading = True
        self.progress_bar.setVisible(True)
        
        self._loader = CommandLoader(self.db, self.PLUGIN_ID)
        self._loader.load_finished.connect(self._on_load_finished)
        self._loader.load_progress.connect(self._on_load_progress)
        self._loader.load_error.connect(self._on_load_error)
        self._loader.finished.connect(self._on_loader_finished)
        self._loader.start()
    
    def _on_loader_finished(self) -> None:
        """线程完成后的清理"""
        if self._loader:
            self._loader.deleteLater()
            self._loader = None
    
    def _on_load_progress(self, progress: int) -> None:
        """加载进度更新"""
        self.progress_bar.setValue(progress)
    
    def _on_load_finished(self, commands: List[Dict[str, Any]]) -> None:
        """数据加载完成"""
        self._commands_cache = commands
        self._is_loading = False
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        self._load_categories()
        self._load_commands()
    
    def _on_load_error(self, error_message: str) -> None:
        """加载错误处理"""
        self._is_loading = False
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        self._load_categories()
        self._load_commands()
        InfoBar.error(
            title="加载错误",
            content=error_message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
    
    def _set_ui_enabled(self, enabled: bool) -> None:
        """设置UI组件的启用状态"""
        self.add_btn.setEnabled(enabled)
        self.add_category_btn.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)
        self.tree.setEnabled(enabled)
        self.all_btn.setEnabled(enabled)
        for btn in self._category_buttons:
            btn.setEnabled(enabled)
    
    def _load_categories(self) -> None:
        """加载分类按钮"""
        for btn in self._category_buttons:
            btn.deleteLater()
        self._category_buttons.clear()
        
        categories = self.db.get_categories(self.PLUGIN_ID)
        for cat in categories:
            btn = PushButton(cat['name'], self)
            btn.clicked.connect(partial(self._show_category, cat))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(partial(self._show_category_menu, cat))
            self.category_layout.insertWidget(
                self.category_layout.count() - 2, btn
            )
            self._category_buttons.append(btn)
    
    def _show_category_menu(self, category: dict, pos) -> None:
        """显示分类右键菜单"""
        from PyQt5.QtGui import QCursor
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        edit_action = QAction("编辑分类", self)
        edit_action.triggered.connect(partial(self._edit_category, category))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除分类", self)
        delete_action.triggered.connect(partial(self._delete_category, category))
        menu.addAction(delete_action)
        
        menu.exec_(QCursor.pos())
    
    def _edit_category(self, category: dict) -> None:
        """编辑分类"""
        dialog = InputDialog("编辑分类", "请输入新的分类名称", category['name'], self)
        if dialog.exec():
            new_name = dialog.get_text()
            if new_name and new_name != category['name']:
                existing_names = [btn.text() for btn in self._category_buttons]
                if new_name not in existing_names:
                    self.db.update_category(self.PLUGIN_ID, category['id'], new_name)
                    self._load_categories()
                    if self._current_category_id == category['id']:
                        self._current_category_name = new_name
                    InfoBar.success(
                        title="修改成功",
                        content=f"分类已重命名为 {new_name}",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
                else:
                    InfoBar.warning(
                        title="警告",
                        content="该分类名称已存在！",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )
    
    def _delete_category(self, category: dict) -> None:
        """删除分类"""
        box = MessageBox("删除分类", f"确定要删除分类 '{category['name']}' 吗？\n该分类下的命令将移至\"全部\"分类。", self)
        if box.exec():
            self.db.delete_category(self.PLUGIN_ID, category['id'])
            self._load_categories()
            if self._current_category_id == category['id']:
                self._show_all()
            InfoBar.success(
                title="删除成功",
                content=f"已删除分类 {category['name']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _load_commands(self) -> None:
        """加载命令列表"""
        self.tree.clear()
        commands = self.db.get_commands(self.PLUGIN_ID, self._current_category_id)
        
        for idx, cmd in enumerate(commands, 1):
            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx))
            item.setText(1, cmd['name'])
            item.setText(2, cmd.get('sub_title', ''))
            item.setText(3, cmd.get('category_name', ''))
            item.setText(4, cmd['content'])
            item.setData(0, Qt.UserRole, cmd['id'])
            item.setForeground(3, QColor("#0078d4"))
    
    def _show_all(self) -> None:
        """显示全部命令"""
        self._current_category_id = None
        self._current_category_name = "全部"
        self._load_commands()
    
    def _show_category(self, category: Dict[str, Any]) -> None:
        """显示指定分类的命令"""
        self._current_category_id = category['id']
        self._current_category_name = category['name']
        self._load_commands()
    
    def _search_commands(self, text: str) -> None:
        """搜索命令"""
        if self._is_loading:
            return
        
        if not text.strip():
            self._load_commands()
            return
        
        self.tree.clear()
        results = self.db.search_commands(self.PLUGIN_ID, text)
        
        for idx, cmd in enumerate(results, 1):
            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx))
            item.setText(1, cmd['name'])
            item.setText(2, cmd.get('sub_title', ''))
            item.setText(3, cmd.get('category_name', ''))
            item.setText(4, cmd['content'])
            item.setData(0, Qt.UserRole, cmd['id'])
            item.setForeground(3, QColor("#0078d4"))
    
    def _copy_command(self, item: QTreeWidgetItem) -> None:
        """复制命令内容到剪贴板"""
        content = item.text(4)
        if content:
            clipboard = QApplication.clipboard()
            clipboard.setText(content)
            
            self.copy_label.move(
                self.width() - self.copy_label.width() - 20, 60
            )
            self.copy_label.show()
            self.copy_label.raise_()
            
            QTimer.singleShot(2000, self.copy_label.hide)
            
            InfoBar.success(
                title="复制成功",
                content="命令已复制到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
    
    def _add_command(self) -> None:
        """添加新命令"""
        categories = [cat['name'] for cat in self.db.get_categories(self.PLUGIN_ID)]
        current_cat = self._current_category_name if self._current_category_name != "全部" else ""
        
        dialog = CommandDialog(
            self, 
            categories=categories, 
            current_category=current_cat
        )
        
        if dialog.exec():
            data = dialog.get_command_data()
            
            category_name = data.get("category", current_cat) or None
            
            self.db.add_command(
                plugin_id=self.PLUGIN_ID,
                name=data["name"],
                content=data["content"],
                category_name=category_name,
                sub_title=data["sub_title"]
            )
            
            self._load_categories()
            self._load_commands()
            
            InfoBar.success(
                title="添加成功",
                content=f"已添加命令 {data['name']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _add_category(self) -> None:
        """添加分类"""
        dialog = InputDialog("添加分类", "请输入分类名称", parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if not name:
                return
            
            self.db.add_category(self.PLUGIN_ID, name)
            self._load_categories()
            
            InfoBar.success(
                title="添加成功",
                content=f"已添加分类 {name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _show_context_menu(self, pos) -> None:
        """显示右键菜单"""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        copy_action = QAction("复制命令内容", self)
        copy_action.triggered.connect(partial(self._copy_command, item))
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(partial(self._edit_command, item))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(partial(self._delete_command, item))
        menu.addAction(delete_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
    
    def _edit_command(self, item: QTreeWidgetItem) -> None:
        """编辑命令"""
        cmd_id = item.data(0, Qt.UserRole)
        old_name = item.text(1)
        old_sub_title = item.text(2)
        old_content = item.text(4)
        old_category = item.text(3)
        
        categories = [cat['name'] for cat in self.db.get_categories(self.PLUGIN_ID)]
        
        dialog = CommandDialog(
            self,
            command_name=old_name,
            command_content=old_content,
            sub_title=old_sub_title,
            categories=categories,
            current_category=old_category
        )
        if dialog.exec():
            data = dialog.get_command_data()
            
            new_category = data.get("category", old_category)
            category_id = None
            if new_category:
                cats = self.db.get_categories(self.PLUGIN_ID)
                for cat in cats:
                    if cat['name'] == new_category:
                        category_id = cat['id']
                        break
            
            self.db.update_command(
                self.PLUGIN_ID, cmd_id,
                name=data["name"],
                content=data["content"],
                sub_title=data["sub_title"],
                category_id=category_id
            )
            self._load_commands()
            
            InfoBar.success(
                title="编辑成功",
                content=f"已更新命令 {data['name']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _delete_command(self, item: QTreeWidgetItem) -> None:
        """删除命令"""
        cmd_id = item.data(0, Qt.UserRole)
        name = item.text(1)
        
        if MessageBox("确认删除", f"确定要删除命令 '{name}' 吗？", self).exec():
            self.db.delete_command(self.PLUGIN_ID, cmd_id)
            self._load_commands()
            
            InfoBar.success(
                title="删除成功",
                content=f"已删除命令 {name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )


class Plugin(PluginInterface):
    """命令管理插件"""
    PLUGIN_ID = "command"
    PLUGIN_NAME = "命令管理"
    PLUGIN_ICON = FIF.COMMAND_PROMPT
    PLUGIN_PRIORITY = 2
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.get_name()}' initialized")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        return CommandWidget(self.core, parent)
    
    def _do_load_data(self) -> None:
        """加载数据：直接从数据库读取"""
        if self._widget is None:
            return
        self._widget.load_data()
