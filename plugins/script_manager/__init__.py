import os
from typing import Optional, Dict, Any, List
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem,
    QMenu, QAction, QFormLayout, QHeaderView, QApplication,
    QLabel, QSplitter, QFileDialog
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import QProcess
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, TextEdit,
    FluentIcon as FIF, InfoBar, InfoBarPosition, TreeWidget,
    ProgressBar, TransparentToolButton, SingleDirectionScrollArea,
    setCustomStyleSheet, isDarkTheme, qconfig, MessageBoxBase,
    SubtitleLabel, ComboBox, CaptionLabel, MessageBox, PlainTextEdit
)
from core import PluginInterface
from core.async_loader import BaseAsyncLoader
from plugins.script_manager.service import ScriptService
from functools import partial
from core import SearchResult
from ui.common import InputDialog


def get_powershell_path() -> str:
    """获取 PowerShell 可执行文件路径，优先使用 PowerShell 7"""
    pwsh7_path = r"C:\Program Files\PowerShell\7\pwsh.exe"
    if os.path.exists(pwsh7_path):
        return pwsh7_path
    return "powershell"


class ScriptDialog(MessageBoxBase):
    """脚本添加/编辑对话框"""
    
    SCRIPT_TYPES = ['bat', 'cmd', 'ps1', 'py', 'html']
    
    def __init__(self, parent=None, script_name: str = "", 
                 script_content: str = "", script_type: str = "bat",
                 description: str = "", categories: List[str] = None,
                 current_category: str = ""):
        super().__init__(parent)
        self.categories = categories or []
        self.current_category = current_category
        
        self.titleLabel = SubtitleLabel('添加/编辑脚本', self)
        self.viewLayout.addWidget(self.titleLabel)
        
        formLayout = QFormLayout()
        
        self.name_input = LineEdit(self)
        self.name_input.setText(script_name)
        self.name_input.setPlaceholderText("请输入脚本名称")
        self.name_input.setClearButtonEnabled(True)
        self.name_input.returnPressed.connect(lambda: self.yesButton.click())
        formLayout.addRow("脚本名称:", self.name_input)
        
        self.type_combo = ComboBox(self)
        self.type_combo.addItems(self.SCRIPT_TYPES)
        if script_type in self.SCRIPT_TYPES:
            index = self.SCRIPT_TYPES.index(script_type)
            self.type_combo.setCurrentIndex(index)
        formLayout.addRow("脚本类型:", self.type_combo)
        
        self.desc_input = LineEdit(self)
        self.desc_input.setText(description)
        self.desc_input.setPlaceholderText("可选")
        self.desc_input.setClearButtonEnabled(True)
        self.desc_input.returnPressed.connect(lambda: self.yesButton.click())
        formLayout.addRow("描述:", self.desc_input)
        
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
        if not self.name_input.text().strip():
            return False
        return True
    
    def get_script_data(self) -> Dict[str, str]:
        data = {
            "name": self.name_input.text().strip(),
            "script_type": self.type_combo.currentText(),
            "description": self.desc_input.text().strip()
        }
        if hasattr(self, 'category_combo'):
            data["category"] = self.category_combo.currentText()
        return data


class ScriptLoader(BaseAsyncLoader):
    """异步脚本加载器"""

    def __init__(self, service: ScriptService):
        super().__init__(None, service.plugin_id)
        self.service = service
    
    def load_data(self) -> List[Dict[str, Any]]:
        """加载脚本数据"""
        return self.service.list_scripts()
    
    def get_data_name(self) -> str:
        return "脚本"


class ScriptEditor(QWidget):
    """脚本编辑器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._current_script_id: Optional[int] = None
        self._current_script_type: str = "bat"
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        self.type_label = CaptionLabel("类型: bat", self)
        top_layout.addWidget(self.type_label)
        
        top_layout.addStretch()
        
        self.save_btn = PushButton("保存", self)
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.setEnabled(False)
        top_layout.addWidget(self.save_btn)
        
        self.run_btn = PushButton("运行", self)
        self.run_btn.setIcon(FIF.PLAY)
        self.run_btn.setEnabled(False)
        top_layout.addWidget(self.run_btn)
        
        layout.addLayout(top_layout)
        
        # 创建垂直分割线，用于脚本编辑器和输出区
        splitter = QSplitter(Qt.Vertical, self)
        splitter.setHandleWidth(2)
        splitter.setChildrenCollapsible(False)
        
        self.editor = PlainTextEdit(self)
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setPlaceholderText("在此编写脚本...")
        self.editor.setLineWrapMode(PlainTextEdit.NoWrap)
        self.editor.textChanged.connect(self._on_text_changed)
        splitter.addWidget(self.editor)
        
        # 输出区容器
        output_container = QWidget()
        output_layout = QVBoxLayout(output_container)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(4)
        
        self.output_label = CaptionLabel("输出:", self)
        output_layout.addWidget(self.output_label)
        
        self.output = PlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 9))
        self.output.setPlaceholderText("脚本输出将显示在这里...")
        output_layout.addWidget(self.output)
        
        splitter.addWidget(output_container)
        splitter.setSizes([400, 150])
        
        self._apply_splitter_style(splitter)
        qconfig.themeChangedFinished.connect(lambda: self._apply_splitter_style(splitter))
        
        layout.addWidget(splitter)
        
        self._apply_editor_style()
        qconfig.themeChangedFinished.connect(self._apply_editor_style)
    
    def _apply_editor_style(self) -> None:
        if isDarkTheme():
            self.editor.setStyleSheet(
                "PlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; }"
            )
            self.output.setStyleSheet(
                "PlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; }"
            )
        else:
            self.editor.setStyleSheet(
                "PlainTextEdit { background-color: #ffffff; color: #1e1e1e; border: 1px solid #e0e0e0; }"
            )
            self.output.setStyleSheet(
                "PlainTextEdit { background-color: #f5f5f5; color: #1e1e1e; border: 1px solid #e0e0e0; }"
            )
    
    def _apply_splitter_style(self, splitter: QSplitter) -> None:
        """应用垂直分割线样式"""
        if isDarkTheme():
            splitter.setStyleSheet("""
                QSplitter::handle {
                    background-color: #3d3d3d;
                }
                QSplitter::handle:hover {
                    background-color: #0078d4;
                }
                QSplitter::handle:pressed {
                    background-color: #005a9e;
                }
            """)
        else:
            splitter.setStyleSheet("""
                QSplitter::handle {
                    background-color: #e0e0e0;
                }
                QSplitter::handle:hover {
                    background-color: #0078d4;
                }
                QSplitter::handle:pressed {
                    background-color: #005a9e;
                }
            """)
    
    def _on_text_changed(self) -> None:
        if self._current_script_id:
            self.save_btn.setEnabled(True)
    
    def load_script(self, script: Dict[str, Any]) -> None:
        self._current_script_id = script.get('id')
        self._current_script_type = script.get('script_type', 'bat')
        self.editor.setPlainText(script.get('content', ''))
        self.type_label.setText(f"类型: {self._current_script_type}")
        self.save_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
    
    def clear(self) -> None:
        self._current_script_id = None
        self._current_script_type = "bat"
        self.editor.clear()
        self.output.clear()
        self.type_label.setText("类型: bat")
        self.save_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
    
    def get_content(self) -> str:
        return self.editor.toPlainText()
    
    def get_script_id(self) -> Optional[int]:
        return self._current_script_id
    
    def get_script_type(self) -> str:
        return self._current_script_type


class ScriptWidget(QWidget):
    """脚本管理界面"""
    
    PLUGIN_ID = "script_manager"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = ScriptService(self.PLUGIN_ID)
        self._current_category_id: Optional[int] = None
        self._current_category_name = "全部"
        self._category_buttons: List[PushButton] = []
        self._is_loading = False
        self._scripts_cache: List[Dict[str, Any]] = []
        self._loader: Optional[ScriptLoader] = None
        self._process: Optional[QProcess] = None
        self._setup_ui()
    
    def _setup_ui(self) -> None:
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
        
        self.add_btn = PushButton("添加脚本", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_script)
        top_layout.addWidget(self.add_btn)
        
        self.search_edit = LineEdit(self)
        self.search_edit.setPlaceholderText("搜索脚本...")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._search_scripts)
        top_layout.addWidget(self.search_edit)
        layout.addLayout(top_layout)
        
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = TreeWidget(left_widget)
        self.tree.setHeaderLabels(["序号", "名称", "类型", "分类", "描述"])
        self.tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree.setColumnWidth(0, 50)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 60)
        self.tree.setColumnWidth(3, 100)
        self.tree.setColumnHidden(0, True)
        self._apply_header_style()
        qconfig.themeChangedFinished.connect(self._apply_header_style)
        self.tree.itemClicked.connect(self._on_script_selected)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        left_layout.addWidget(self.tree)
        
        splitter.addWidget(left_widget)
        
        self.editor = ScriptEditor(self)
        self.editor.save_btn.clicked.connect(self._save_current_script)
        self.editor.run_btn.clicked.connect(self._run_current_script)
        splitter.addWidget(self.editor)
        
        splitter.setSizes([300, 500])
        self._apply_splitter_style(splitter)
        qconfig.themeChangedFinished.connect(lambda: self._apply_splitter_style(splitter))
        layout.addWidget(splitter)
        
        self._set_ui_enabled(False)
    
    def _apply_header_style(self) -> None:
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
    
    def _apply_splitter_style(self, splitter: QSplitter) -> None:
        """应用分割线样式"""
        if isDarkTheme():
            splitter.setStyleSheet("""
                QSplitter::handle {
                    background-color: #3d3d3d;
                }
                QSplitter::handle:hover {
                    background-color: #0078d4;
                }
                QSplitter::handle:pressed {
                    background-color: #005a9e;
                }
            """)
        else:
            splitter.setStyleSheet("""
                QSplitter::handle {
                    background-color: #e0e0e0;
                }
                QSplitter::handle:hover {
                    background-color: #0078d4;
                }
                QSplitter::handle:pressed {
                    background-color: #005a9e;
                }
            """)
    
    def load_data(self) -> None:
        if self._loader and self._loader.isRunning():
            return
        
        self._is_loading = True
        self.progress_bar.setVisible(True)
        
        self._loader = ScriptLoader(self.service)
        self._loader.load_finished.connect(self._on_load_finished)
        self._loader.load_progress.connect(self._on_load_progress)
        self._loader.load_error.connect(self._on_load_error)
        self._loader.finished.connect(self._on_loader_finished)
        self._loader.start()
    
    def _on_loader_finished(self) -> None:
        if self._loader:
            self._loader.deleteLater()
            self._loader = None
    
    def _on_load_progress(self, progress: int) -> None:
        self.progress_bar.setValue(progress)
    
    def _on_load_finished(self, scripts: List[Dict[str, Any]]) -> None:
        self._scripts_cache = scripts
        self._is_loading = False
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        self._load_categories()
        self._load_scripts()
    
    def _on_load_error(self, error_message: str) -> None:
        self._is_loading = False
        self.progress_bar.setVisible(False)
        self._set_ui_enabled(True)
        self._load_categories()
        self._load_scripts()
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
        self.add_btn.setEnabled(enabled)
        self.add_category_btn.setEnabled(enabled)
        self.search_edit.setEnabled(enabled)
        self.tree.setEnabled(enabled)
        self.all_btn.setEnabled(enabled)
        for btn in self._category_buttons:
            btn.setEnabled(enabled)
    
    def _load_categories(self) -> None:
        for btn in self._category_buttons:
            btn.deleteLater()
        self._category_buttons.clear()
        
        categories = self.service.list_categories()
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
        dialog = InputDialog("编辑分类", "请输入新的分类名称", category['name'], self)
        if dialog.exec():
            new_name = dialog.get_text()
            if new_name and new_name != category['name']:
                existing_names = [btn.text() for btn in self._category_buttons]
                if new_name not in existing_names:
                    self.service.update_category(category['id'], new_name)
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
        box = MessageBox("删除分类", f"确定要删除分类 '{category['name']}' 吗？\n该分类下的脚本将移至\"全部\"分类。", self)
        if box.exec():
            self.service.delete_category(category['id'])
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
    
    def _load_scripts(self) -> None:
        self.tree.clear()
        scripts = self.service.list_scripts(self._current_category_id)
        
        for idx, script in enumerate(scripts, 1):
            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx))
            item.setText(1, script['name'])
            item.setText(2, script.get('script_type', 'bat'))
            item.setText(3, script.get('category_name', ''))
            item.setText(4, script.get('description', ''))
            item.setData(0, Qt.UserRole, script['id'])
            item.setForeground(2, QColor("#0078d4"))
    
    def _show_all(self) -> None:
        self._current_category_id = None
        self._current_category_name = "全部"
        self._load_scripts()
    
    def _show_category(self, category: Dict[str, Any]) -> None:
        self._current_category_id = category['id']
        self._current_category_name = category['name']
        self._load_scripts()
    
    def _search_scripts(self, text: str) -> None:
        if self._is_loading:
            return
        
        if not text.strip():
            self._load_scripts()
            return
        
        self.tree.clear()
        results = self.service.search_scripts(text)
        
        for idx, script in enumerate(results, 1):
            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx))
            item.setText(1, script['name'])
            item.setText(2, script.get('script_type', 'bat'))
            item.setText(3, script.get('category_name', ''))
            item.setText(4, script.get('description', ''))
            item.setData(0, Qt.UserRole, script['id'])
            item.setForeground(2, QColor("#0078d4"))
    
    def _on_script_selected(self, item: QTreeWidgetItem) -> None:
        script_id = item.data(0, Qt.UserRole)
        scripts = [s for s in self._scripts_cache if s['id'] == script_id]
        if scripts:
            self.editor.load_script(scripts[0])
    
    def _add_script(self) -> None:
        categories = self.service.list_category_names()
        current_cat = self._current_category_name if self._current_category_name != "全部" else ""
        
        dialog = ScriptDialog(
            self, 
            categories=categories, 
            current_category=current_cat
        )
        
        if dialog.exec():
            data = dialog.get_script_data()
            
            category_name = data.get("category", current_cat) or None
            
            script_id = self.service.add_script(
                name=data["name"],
                content="",
                script_type=data["script_type"],
                category_name=category_name,
                description=data["description"]
            )
            
            self._scripts_cache = self.service.list_scripts()
            self._load_categories()
            self._load_scripts()
            
            for script in self._scripts_cache:
                if script['id'] == script_id:
                    self.editor.load_script(script)
                    break
            
            InfoBar.success(
                title="添加成功",
                content=f"已添加脚本 {data['name']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _add_category(self) -> None:
        dialog = InputDialog("添加分类", "请输入分类名称", parent=self)
        if dialog.exec():
            name = dialog.get_text()
            if not name:
                return
            
            self.service.add_category(name)
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
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        edit_action = QAction("编辑信息", self)
        edit_action.triggered.connect(partial(self._edit_script_info, item))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(partial(self._delete_script, item))
        menu.addAction(delete_action)
        
        menu.exec_(self.tree.viewport().mapToGlobal(pos))
    
    def _edit_script_info(self, item: QTreeWidgetItem) -> None:
        script_id = item.data(0, Qt.UserRole)
        old_name = item.text(1)
        old_type = item.text(2)
        old_category = item.text(3)
        old_desc = item.text(4)
        
        categories = self.service.list_category_names()
        
        dialog = ScriptDialog(
            self,
            script_name=old_name,
            script_type=old_type,
            description=old_desc,
            categories=categories,
            current_category=old_category
        )
        if dialog.exec():
            data = dialog.get_script_data()
            
            new_category = data.get("category", old_category)
            category_id = self.service.resolve_category_id(new_category)
            
            self.service.update_script(
                script_id,
                name=data["name"],
                script_type=data["script_type"],
                description=data["description"],
                category_id=category_id
            )
            self._scripts_cache = self.service.list_scripts()
            self._load_scripts()
            
            InfoBar.success(
                title="编辑成功",
                content=f"已更新脚本 {data['name']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _delete_script(self, item: QTreeWidgetItem) -> None:
        script_id = item.data(0, Qt.UserRole)
        name = item.text(1)
        
        if MessageBox("确认删除", f"确定要删除脚本 '{name}' 吗？", self).exec():
            self.service.delete_script(script_id)
            self._scripts_cache = self.service.list_scripts()
            self._load_scripts()
            
            if self.editor.get_script_id() == script_id:
                self.editor.clear()
            
            InfoBar.success(
                title="删除成功",
                content=f"已删除脚本 {name}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _save_current_script(self) -> None:
        script_id = self.editor.get_script_id()
        if not script_id:
            return
        
        content = self.editor.get_content()
        self.service.update_script(script_id, content=content)
        self.editor.save_btn.setEnabled(False)
        
        for i, script in enumerate(self._scripts_cache):
            if script['id'] == script_id:
                self._scripts_cache[i]['content'] = content
                break
        
        InfoBar.success(
            title="保存成功",
            content="脚本已保存",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )
    
    def _run_current_script(self) -> None:
        script_type = self.editor.get_script_type()
        content = self.editor.get_content()
        
        if not content.strip():
            InfoBar.warning(
                title="脚本为空",
                content="请先编写脚本内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        import tempfile
        import os
        import webbrowser
        
        # HTML 文件直接在浏览器中打开
        if script_type == 'html':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            webbrowser.open(temp_path)
            InfoBar.success(
                title="已打开",
                content=f"HTML 文件已在默认浏览器中打开",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        
        suffix_map = {
            'bat': '.bat',
            'cmd': '.cmd',
            'ps1': '.ps1',
            'py': '.py'
        }
        
        suffix = suffix_map.get(script_type, '.bat')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        self.editor.output.clear()
        self.editor.output.appendPlainText(f"运行脚本：{temp_path}\n")
        
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_process_output)
        self._process.readyReadStandardError.connect(self._on_process_error)
        self._process.finished.connect(self._on_process_finished)
        
        if script_type == 'ps1':
            ps_path = get_powershell_path()
            self._process.start(ps_path, ['-ExecutionPolicy', 'Bypass', '-File', temp_path])
        elif script_type == 'py':
            # Python 脚本：先尝试全局环境，失败则使用应用解释器
            import sys
            self._process.start('python', [temp_path])
            # 如果启动失败，在 finished 信号中重试
            self._py_script_path = temp_path
        else:
            self._process.start('cmd', ['/c', temp_path])
        
        self._temp_file = temp_path
    
    def _on_process_output(self) -> None:
        data = self._process.readAllStandardOutput().data()
        try:
            text = data.decode('gbk', errors='replace')
        except Exception:
            text = data.decode('utf-8', errors='replace')
        self.editor.output.appendPlainText(text)
    
    def _on_process_error(self) -> None:
        data = self._process.readAllStandardError().data()
        try:
            text = data.decode('gbk', errors='replace')
        except Exception:
            text = data.decode('utf-8', errors='replace')
        self.editor.output.appendPlainText(f"[错误] {text}")
    
    def _on_process_finished(self, exit_code: int, exit_status: int) -> None:
        # 如果是 Python 脚本且全局解释器失败，尝试使用应用解释器
        if hasattr(self, '_py_script_path') and exit_code != 0:
            import sys
            self.editor.output.appendPlainText(f"\n全局 Python 解释器失败，尝试使用应用解释器...\n")
            
            process = QProcess(self)
            process.setProcessChannelMode(QProcess.MergedChannels)
            process.finished.connect(lambda code, status: self._on_process_finished(code, status))
            process.readyReadStandardOutput.connect(self._on_process_output)
            process.readyReadStandardError.connect(self._on_process_error)
            
            # 使用当前应用的 Python 解释器
            process.start(sys.executable, [self._py_script_path])
            process.waitForFinished(-1)  # 等待完成
            
            delattr(self, '_py_script_path')
            return
        
        self.editor.output.appendPlainText(f"\n进程结束，退出码：{exit_code}")
        
        if hasattr(self, '_temp_file') and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception:
                pass
        
        # 清理 Python 脚本路径
        if hasattr(self, '_py_script_path'):
            delattr(self, '_py_script_path')


class Plugin(PluginInterface):
    """脚本管理插件"""
    PLUGIN_ID = "script_manager"
    PLUGIN_NAME = "脚本管理"
    PLUGIN_ICON = FIF.CODE
    PLUGIN_PRIORITY = 14
    
    TEST_SCRIPTS = [
        {
            "name": "BAT 测试脚本",
            "script_type": "bat",
            "content": "@echo off\nchcp 65001 >nul\necho ================================\necho    BAT 脚本测试\necho ================================\necho.\necho 当前目录: %cd%\necho 当前时间: %date% %time%\necho.\necho 系统信息:\nver\necho.\necho 环境变量 PATH:\necho %PATH:;=&echo %\necho.\necho 测试完成!\npause",
            "description": "Windows 批处理脚本测试"
        },
        {
            "name": "CMD 测试脚本",
            "script_type": "cmd",
            "content": "@echo off\necho ================================\necho    CMD 脚本测试\necho ================================\necho.\necho 用户名: %USERNAME%\necho 计算机名: %COMPUTERNAME%\necho 用户目录: %USERPROFILE%\necho.\necho 目录列表:\ndir /b\npause",
            "description": "CMD 命令脚本测试"
        },
        {
            "name": "PowerShell 测试脚本",
            "script_type": "ps1",
            "content": "Write-Host \"================================\"\nWrite-Host \"   PowerShell 脚本测试\" -ForegroundColor Cyan\nWrite-Host \"================================\"\nWrite-Host \"\"\nWrite-Host \"系统信息:\" -ForegroundColor Yellow\nWrite-Host \"  PowerShell 版本: $($PSVersionTable.PSVersion)\"\nWrite-Host \"  操作系统: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)\"\nWrite-Host \"  当前用户: $env:USERNAME\"\nWrite-Host \"  计算机名: $env:COMPUTERNAME\"\nWrite-Host \"\"\nWrite-Host \"当前目录内容:\" -ForegroundColor Yellow\nGet-ChildItem -Name | ForEach-Object { Write-Host \"  $_\" }\nWrite-Host \"\"\nWrite-Host \"测试完成!\" -ForegroundColor Green",
            "description": "PowerShell 脚本测试"
        },
        {
            "name": "Python 测试脚本",
            "script_type": "py",
            "content": "# -*- coding: utf-8 -*-\nimport sys\nimport os\nimport platform\n\nprint(\"=\" * 40)\nprint(\"   Python 脚本测试\")\nprint(\"=\" * 40)\nprint()\nprint(\"Python 信息:\")\nprint(f\"  版本: {sys.version}\")\nprint(f\"  可执行文件: {sys.executable}\")\nprint(f\"  平台: {sys.platform}\")\nprint()\nprint(\"系统信息:\")\nprint(f\"  系统: {platform.system()}\")\nprint(f\"  版本: {platform.version()}\")\nprint(f\"  架构: {platform.machine()}\")\nprint(f\"  处理器: {platform.processor()}\")\nprint()\nprint(\"当前目录:\")\nprint(f\"  {os.getcwd()}\")\nprint()\nprint(\"目录内容:\")\nfor item in os.listdir('.')[:10]:\n    print(f\"  {item}\")\nprint()\nprint(\"测试完成!\")",
            "description": "Python 脚本测试"
        }
    ]
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.get_name()}' initialized")
        self._init_test_scripts()
    
    def _init_test_scripts(self) -> None:
        """初始化测试脚本"""
        service = ScriptService(self.PLUGIN_ID)
        for script in self.TEST_SCRIPTS:
            if not service.script_exists(script["name"]):
                service.add_script(
                    name=script["name"],
                    content=script["content"],
                    script_type=script["script_type"],
                    description=script["description"],
                )
                self.core.logger.info(f"Added test script: {script['name']}")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        return ScriptWidget(self.core, parent)
    
    def _do_load_data(self) -> None:
        if self._widget is None:
            return
        self._widget.load_data()

    def supports_search(self) -> bool:
        return True

    def search(self, query: str):
        service = ScriptService(self.PLUGIN_ID)
        results = []
        scripts = service.search_scripts(query)
        for script in scripts[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=script['name'],
                description=f"{script.get('description', '')} - {script['script_type']}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in script['name'].lower() else 0.5,
                action=lambda s=script: self._run_script(s),
                metadata={'script_id': script['id']}
            )
            results.append(result)
        return results

    def _run_script(self, script: Dict[str, Any]) -> None:
        """运行脚本"""
        import tempfile
        import os
        import webbrowser

        script_type = script.get('script_type', 'bat')
        content = script.get('content', '')
        
        # 调试输出
        print(f"[DEBUG] Running script: type={script_type}, name={script.get('name', 'unknown')}")

        if not content.strip():
            return

        # HTML 文件直接在浏览器中打开
        if script_type == 'html':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            webbrowser.open(temp_path)
            return

        suffix_map = {
            'bat': '.bat',
            'cmd': '.cmd',
            'ps1': '.ps1',
            'py': '.py'
        }

        suffix = suffix_map.get(script_type, '.bat')

        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        process = QProcess()

        if script_type == 'ps1':
            process.start(get_powershell_path(), ['-ExecutionPolicy', 'Bypass', '-File', temp_path])
        elif script_type == 'py':
            process.start('python', [temp_path])
        else:
            process.start('cmd', ['/c', temp_path])
