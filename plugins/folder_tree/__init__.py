import os
import re
import json
from pathlib import Path
from typing import Optional, Tuple, List
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal, QSize, QEvent
from PyQt5.QtGui import QColor, QPalette, QPixmap, QPainter, QCursor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QColorDialog,
    QGridLayout, QScrollArea, QFrame, QTabWidget,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox, QToolTip,
    QMenu, QAction, QApplication, QFileDialog, QTextEdit, QDialog,
    QVBoxLayout as QVBoxLayoutWidget, QLineEdit, QPushButton
)
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, ScrollArea, PrimaryPushButton, ToolButton,
    CardWidget, SpinBox, isDarkTheme, qconfig, ToolButton, BodyLabel, IndeterminateProgressBar,
    ComboBox, FluentStyleSheet, Dialog, RoundMenu, Action, MessageBoxBase,
    SubtitleLabel, BodyLabel as FluentBodyLabel
)
from core import PluginInterface, get_app_data_path
from storage.database import DatabaseManager


class FolderTreeWidget(QWidget):
    """文件夹树插件界面"""
    PLUGIN_ID = "folder_tree"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self.current_folder = None
        self.tree_content = ""
        self.custom_rules = {}
        self.load_custom_rules()
        self.init_ui()
        self.setup_style()
        qconfig.themeChanged.connect(self.on_theme_changed)

    def on_theme_changed(self):
        """主题变化时更新样式"""
        self.setup_style()

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建最外层滚动区域
        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setObjectName("folderTreeScrollArea")

        # 创建内容容器
        self._content_widget = QWidget()
        self._content_widget.setObjectName("folderTreeContent")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        # 工具栏
        toolbar = self.create_toolbar()
        self._content_layout.addWidget(toolbar)

        # 预览文本框
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setPlaceholderText("请选择文件夹并生成树形结构...")
        self._content_layout.addWidget(self._preview_text, 1)

        # 状态栏
        status_bar = self.create_status_bar()
        self._content_layout.addWidget(status_bar)

        # 将内容容器添加到滚动区域
        self._scroll_area.setWidget(self._content_widget)

        main_layout.addWidget(self._scroll_area)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("folderTreeToolbar")
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_layout.setSpacing(8)

        # 选择文件夹按钮
        self._select_btn = PrimaryPushButton(FIF.FOLDER, "选择文件夹")
        self._select_btn.clicked.connect(self.select_folder)
        toolbar_layout.addWidget(self._select_btn)

        # 生成树形结构按钮
        self._generate_tree_btn = PushButton(FIF.VIEW, "生成树形结构")
        self._generate_tree_btn.clicked.connect(self.generate_tree)
        toolbar_layout.addWidget(self._generate_tree_btn)

        # 只生成文件夹按钮
        self._generate_folders_btn = PushButton(FIF.FOLDER, "只生成文件夹")
        self._generate_folders_btn.clicked.connect(self.generate_folders_only)
        toolbar_layout.addWidget(self._generate_folders_btn)

        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator)

        # 保存为txt按钮
        self._save_btn = PushButton(FIF.SAVE, "保存")
        self._save_btn.clicked.connect(self.save_to_txt)
        toolbar_layout.addWidget(self._save_btn)

        # 另存为按钮
        self._save_as_btn = PushButton(FIF.SAVE_AS, "另存为")
        self._save_as_btn.clicked.connect(self.save_as)
        toolbar_layout.addWidget(self._save_as_btn)

        # 分隔符
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator2)

        # 规则下拉框
        self._rules_combo = ComboBox()
        self._update_rules_combo()  # 初始化时加载所有规则（包括自定义）
        self._rules_combo.setCurrentIndex(0)
        self._rules_combo.currentIndexChanged.connect(self.on_rules_combo_changed)
        toolbar_layout.addWidget(self._rules_combo)
        
        # 自定义规则按钮
        self._custom_rule_btn = PushButton(FIF.EDIT, "自定义规则")
        self._custom_rule_btn.clicked.connect(self.open_custom_rule_dialog)
        toolbar_layout.addWidget(self._custom_rule_btn)

        toolbar_layout.addStretch()

        return toolbar_widget

    def create_status_bar(self):
        """创建状态栏"""
        status_widget = QWidget()
        status_widget.setObjectName("folderTreeStatus")
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self._status_label = BodyLabel("就绪")
        status_layout.addWidget(self._status_label)

        # 进度条（等待条）
        self._progress_bar = IndeterminateProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setVisible(False)
        status_layout.addWidget(self._progress_bar)

        status_layout.addStretch()

        self._folder_count_label = BodyLabel("文件夹: 0")
        status_layout.addWidget(self._folder_count_label)

        self._file_count_label = BodyLabel("文件: 0")
        status_layout.addWidget(self._file_count_label)

        return status_widget

    def setup_style(self):
        """设置样式（支持主题）"""
        dark = isDarkTheme()
        
        if dark:
            bg_color = "#1e1e1e"
            text_color = "#ffffff"
            border_color = "#3d3d3d"
        else:
            bg_color = "#f5f5f5"
            text_color = "#333333"
            border_color = "#d9d9d9"
        
        # 工具栏
        toolbar = self.findChild(QWidget, "folderTreeToolbar")
        if toolbar:
            toolbar.setStyleSheet(f"""
                QWidget#folderTreeToolbar {{
                    background-color: {bg_color};
                    border-bottom: 1px solid {border_color};
                }}
            """)
        
        # 滚动区域
        self._scroll_area.setStyleSheet(f"""
            ScrollArea#folderTreeScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea#folderTreeScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea#folderTreeScrollArea > QWidget {{
                background-color: {bg_color};
            }}
        """)
        
        # 内容容器
        self._content_widget.setStyleSheet(f"QWidget#folderTreeContent{{background-color: {bg_color};}}")
        
        # 预览文本框
        self._preview_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
        """)
        
        # 状态栏
        status = self.findChild(QWidget, "folderTreeStatus")
        if status:
            status.setStyleSheet(f"""
                QWidget#folderTreeStatus {{
                    background-color: {bg_color};
                    border-top: 1px solid {border_color};
                }}
            """)
    
    def load_custom_rules(self):
        """加载自定义规则"""
        try:
            rules = self.db.get_all_folder_tree_rules()
            self.custom_rules = {}
            for rule in rules:
                items = json.loads(rule['exclude_items']) if rule['exclude_items'] else []
                self.custom_rules[rule['rule_name']] = items
        except Exception as e:
            self.custom_rules = {}
    
    def save_custom_rules(self):
        """保存自定义规则（已弃用，现在实时保存到数据库）"""
        return True
    
    def validate_rule_items(self, items_str: str) -> Tuple[bool, List[str]]:
        """验证规则项格式
        返回：(是否有效，解析后的列表)
        """
        if not items_str.strip():
            return False, []
        
        items = [item.strip() for item in items_str.split(',')]
        # 正则验证：允许字母、数字、点、下划线、中划线
        pattern = re.compile(r'^[a-zA-Z0-9_\-\.\u4e00-\u9fa5]+$')
        
        invalid_items = []
        for item in items:
            if not item:
                continue
            if not pattern.match(item):
                invalid_items.append(item)
        
        if invalid_items:
            return False, invalid_items
        
        return True, [item for item in items if item]
    
    def open_custom_rule_dialog(self):
        """打开自定义规则对话框"""
        dark = isDarkTheme()
        bg_color = "#1e1e1e" if dark else "#f5f5f5"
        text_color = "#ffffff" if dark else "#333333"
        border_color = "#3d3d3d" if dark else "#d9d9d9"
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("自定义规则管理")
        dialog.yesButton.setText("关闭")
        dialog.cancelButton.setVisible(False)
        
        content_widget = QWidget()
        content_widget.setObjectName("customRuleContent")
        content_widget.setStyleSheet(f"QWidget#customRuleContent{{background-color: {bg_color};}}")
        content_layout = QVBoxLayoutWidget(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = SubtitleLabel("已有规则：")
        content_layout.addWidget(list_label)
        content_layout.addSpacing(8)
        
        self._rule_list = QListWidget()
        self._rule_list.setObjectName("ruleList")
        self._rule_list.setStyleSheet(f"""
            QListWidget#ruleList {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
        """)
        for rule_name, items in self.custom_rules.items():
            self._rule_list.addItem(f"{rule_name}: {', '.join(items)}")
        self._rule_list.setMinimumHeight(150)
        content_layout.addWidget(self._rule_list)
        content_layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        
        self._new_btn = PrimaryPushButton(FIF.ADD, "新建")
        self._new_btn.clicked.connect(lambda: self.show_rule_editor(dialog, None))
        btn_layout.addWidget(self._new_btn)
        
        self._edit_btn = PushButton(FIF.EDIT, "编辑")
        self._edit_btn.clicked.connect(lambda: self.show_rule_editor(dialog, self._rule_list.currentRow()))
        btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = PushButton(FIF.DELETE, "删除")
        self._delete_btn.clicked.connect(lambda: self.delete_rule(dialog))
        btn_layout.addWidget(self._delete_btn)
        
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)
        
        dialog.viewLayout.addWidget(content_widget)
        dialog.exec_()
    
    def show_rule_editor(self, parent_dialog, edit_index: int = None):
        """显示规则编辑器"""
        dark = isDarkTheme()
        bg_color = "#1e1e1e" if dark else "#f5f5f5"
        text_color = "#ffffff" if dark else "#333333"
        hint_color = "#888888" if dark else "#666666"
        
        editor = MessageBoxBase(self)
        if edit_index is not None:
            editor.setWindowTitle("编辑规则")
        else:
            editor.setWindowTitle("新建规则")
        
        content_widget = QWidget()
        content_widget.setObjectName("ruleEditorContent")
        content_widget.setStyleSheet(f"QWidget#ruleEditorContent{{background-color: {bg_color};}}")
        content_layout = QVBoxLayoutWidget(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = SubtitleLabel("规则名称：")
        content_layout.addWidget(name_label)
        content_layout.addSpacing(4)
        
        name_input = LineEdit()
        if edit_index is not None:
            rule_names = list(self.custom_rules.keys())
            name_input.setText(rule_names[edit_index])
        name_input.setPlaceholderText("例如：规则 2")
        content_layout.addWidget(name_input)
        content_layout.addSpacing(16)
        
        items_label = SubtitleLabel("排除项（用英文逗号分隔）：")
        content_layout.addWidget(items_label)
        content_layout.addSpacing(4)
        
        items_input = LineEdit()
        if edit_index is not None:
            rule_names = list(self.custom_rules.keys())
            rule_name = rule_names[edit_index]
            items_input.setText(', '.join(self.custom_rules[rule_name]))
        items_input.setPlaceholderText("例如：node_modules,.git,__pycache__")
        content_layout.addWidget(items_input)
        content_layout.addSpacing(8)
        
        hint_label = FluentBodyLabel("提示：支持以.开头的文件或文件夹，如.gitignore")
        hint_label.setStyleSheet(f"color: {hint_color}; font-size: 12px;")
        content_layout.addWidget(hint_label)
        
        editor.viewLayout.addWidget(content_widget)
        
        editor.yesButton.setText("保存")
        editor.yesButton.clicked.connect(lambda: self.save_rule(editor, edit_index, name_input.text(), items_input.text(), parent_dialog))
        
        editor.exec_()
    
    def save_rule(self, editor, edit_index: int, name: str, items_str: str, parent_dialog):
        """保存规则"""
        name = name.strip()
        items_str = items_str.strip()
        
        if not name:
            InfoBar.error(
                title="错误",
                content="规则名称不能为空",
                parent=self,
                duration=2000
            )
            return
        
        valid, result = self.validate_rule_items(items_str)
        if not valid:
            InfoBar.error(
                title="错误",
                content=f"以下项目格式不正确：{', '.join(result)}\n只允许字母、数字、点、下划线、中划线和中文",
                parent=self,
                duration=3000
            )
            return
        
        if edit_index is not None:
            rule_names = list(self.custom_rules.keys())
            old_name = rule_names[edit_index]
            if old_name != name:
                if name in self.custom_rules:
                    InfoBar.error(
                        title="错误",
                        content=f"规则'{name}'已存在",
                        parent=self,
                        duration=2000
                    )
                    return
                self.db.delete_folder_tree_rule(old_name)
                del self.custom_rules[old_name]
            else:
                self.db.update_folder_tree_rule(name, result)
                self.custom_rules[name] = result
                self._update_rules_combo(name)
                if parent_dialog:
                    parent_dialog.findChild(QListWidget).clear()
                    for rule_name, items in self.custom_rules.items():
                        parent_dialog.findChild(QListWidget).addItem(f"{rule_name}: {', '.join(items)}")
                InfoBar.success(
                    title="成功",
                    content=f"已保存规则：{name}",
                    parent=self,
                    duration=2000
                )
                editor.accept()
                return
        
        if name in self.custom_rules:
            InfoBar.error(
                title="错误",
                content=f"规则'{name}'已存在",
                parent=self,
                duration=2000
            )
            return
        
        self.db.add_folder_tree_rule(name, result)
        self.custom_rules[name] = result
        self._update_rules_combo(name)
        
        if parent_dialog:
            parent_dialog.findChild(QListWidget).clear()
            for rule_name, items in self.custom_rules.items():
                parent_dialog.findChild(QListWidget).addItem(f"{rule_name}: {', '.join(items)}")
        
        InfoBar.success(
            title="成功",
            content=f"已保存规则：{name}",
            parent=self,
            duration=2000
        )
        editor.accept()
    
    def delete_rule(self, parent_dialog):
        """删除规则"""
        current_row = self._rule_list.currentRow()
        if current_row < 0:
            InfoBar.warning(
                title="提示",
                content="请先选择要删除的规则",
                parent=self,
                duration=2000
            )
            return
        
        from qfluentwidgets import MessageBox
        w = MessageBox(
            title='确认删除',
            content='确定要删除选中的规则吗？',
            parent=self
        )
        if w.exec_():
            rule_names = list(self.custom_rules.keys())
            rule_name = rule_names[current_row]
            self.db.delete_folder_tree_rule(rule_name)
            del self.custom_rules[rule_name]
            
            self._update_rules_combo()
            self._rule_list.takeItem(current_row)
            
            InfoBar.success(
                title="成功",
                content=f"已删除规则：{rule_name}",
                parent=self,
                duration=2000
            )
    
    def _update_rules_combo(self, select_custom_rule_name: str = None):
        """更新规则下拉框
        Args:
            select_custom_rule_name: 如果指定，选中该自定义规则
        """
        current_index = self._rules_combo.currentIndex()
        current_text = self._rules_combo.currentText()
        
        self._rules_combo.blockSignals(True)  # 暂时阻止信号
        
        self._rules_combo.clear()
        self._rules_combo.addItems(["无规则", "规则1：跳过.venv, .git, .idea"])
        
        # 添加自定义规则
        for rule_name in self.custom_rules.keys():
            self._rules_combo.addItem(f"自定义：{rule_name}")
        
        # 如果指定了规则名，选中它
        if select_custom_rule_name:
            for i in range(self._rules_combo.count()):
                if f"自定义：{select_custom_rule_name}" in self._rules_combo.itemText(i):
                    self._rules_combo.setCurrentIndex(i)
                    self._rules_combo.blockSignals(False)
                    return
        # 否则尽量保持原来的选择
        elif current_index < self._rules_combo.count():
            self._rules_combo.setCurrentIndex(current_index)
        
        self._rules_combo.blockSignals(False)
    
    def on_rules_combo_changed(self, index: int):
        """当下拉框选择变化时重新加载规则配置"""
        # 如果选择的是自定义规则（索引 >= 2），重新加载配置文件
        if index >= 2:
            self.load_custom_rules()
            # 重新更新下拉框，保持当前选择
            current_text = self._rules_combo.itemText(index)
            if current_text.startswith("自定义："):
                rule_name = current_text.replace("自定义：", "")
                self._update_rules_combo(rule_name)

    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.current_folder = Path(folder)
            self._status_label.setText(f"已选择: {self.current_folder.name}")
            InfoBar.success(
                title="选择成功",
                content=f"已选择文件夹: {self.current_folder.name}",
                parent=self,
                duration=2000
            )

    def generate_tree(self):
        """生成文件夹树形结构"""
        if not self.current_folder:
            InfoBar.warning(
                title="请先选择文件夹",
                content="请先点击选择文件夹按钮",
                parent=self,
                duration=2000
            )
            return
        
        try:
            self._status_label.setText('正在生成树形结构...')
            self._progress_bar.setVisible(True)
            QApplication.processEvents()
            
            rule_index = self._rules_combo.currentIndex()
            self.tree_content = self._get_folder_tree(self.current_folder, '', rule_index)
            self._preview_text.setPlainText(self.tree_content)
            self._update_counts()
            self._status_label.setText('树形结构生成完成')
            
            InfoBar.success(
                title="生成成功",
                content="树形结构已生成",
                parent=self,
                duration=2000
            )
        except Exception as e:
            QMessageBox.critical(self, '错误', f'生成树形结构失败：{str(e)}')
            self._status_label.setText('生成失败')
        finally:
            self._progress_bar.setVisible(False)

    def generate_folders_only(self):
        """只生成文件夹的树形结构"""
        if not self.current_folder:
            InfoBar.warning(
                title="请先选择文件夹",
                content="请先点击选择文件夹按钮",
                parent=self,
                duration=2000
            )
            return
        
        try:
            self._status_label.setText('正在生成文件夹树形结构...')
            self._progress_bar.setVisible(True)
            QApplication.processEvents()
            
            rule_index = self._rules_combo.currentIndex()
            self.tree_content = self._get_folder_only_tree(self.current_folder, '', rule_index)
            self._preview_text.setPlainText(self.tree_content)
            self._update_counts()
            self._status_label.setText('文件夹树形结构生成完成')
            
            InfoBar.success(
                title="生成成功",
                content="文件夹结构已生成",
                parent=self,
                duration=2000
            )
        except Exception as e:
            QMessageBox.critical(self, '错误', f'生成文件夹树形结构失败: {str(e)}')
            self._status_label.setText('生成失败')
        finally:
            self._progress_bar.setVisible(False)

    def _get_folder_tree(self, root_path: Path, prefix: str = '', rule_index: int = 0) -> str:
        """递归获取文件夹树形结构"""
        tree = ''
        try:
            items = sorted(root_path.iterdir(), key=lambda x: x.name.lower())
        except PermissionError:
            return f'{prefix}└── [权限不足，无法访问]\n'
        
        # 规则 1：跳过.venv, .git, .idea
        if rule_index == 1:
            skip_names = [".venv", ".git", ".idea"]
            items = [item for item in items if item.name not in skip_names]
        
        # 自定义规则（索引 >= 2）
        if rule_index >= 2:
            custom_rule_index = rule_index - 2
            rule_names = list(self.custom_rules.keys())
            if custom_rule_index < len(rule_names):
                rule_name = rule_names[custom_rule_index]
                skip_names = self.custom_rules[rule_name]
                items = [item for item in items if item.name not in skip_names]
        
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            
            # 如果是文件夹，在名称后面添加斜杠
            display_name = f'{item.name}/' if item.is_dir() else item.name
            
            if is_last:
                tree += f'{prefix}└── {display_name}\n'
                next_prefix = f'{prefix}    '
            else:
                tree += f'{prefix}├── {display_name}\n'
                next_prefix = f'{prefix}│   '
            
            if item.is_dir():
                try:
                    tree += self._get_folder_tree(item, next_prefix, rule_index)
                except PermissionError:
                    tree += f'{next_prefix}└── [权限不足，无法访问]\n'
        
        return tree

    def _get_folder_only_tree(self, root_path: Path, prefix: str = '', rule_index: int = 0) -> str:
        """递归获取只有文件夹的树形结构"""
        tree = ''
        try:
            items = sorted(root_path.iterdir(), key=lambda x: x.name.lower())
        except PermissionError:
            return f'{prefix}└── [权限不足，无法访问]\n'
        
        folders = [item for item in items if item.is_dir()]
        
        # 规则 1：跳过.venv, .git, .idea
        if rule_index == 1:
            skip_names = [".venv", ".git", ".idea"]
            folders = [item for item in folders if item.name not in skip_names]
        
        # 自定义规则（索引 >= 2）
        if rule_index >= 2:
            custom_rule_index = rule_index - 2
            rule_names = list(self.custom_rules.keys())
            if custom_rule_index < len(rule_names):
                rule_name = rule_names[custom_rule_index]
                skip_names = self.custom_rules[rule_name]
                folders = [item for item in folders if item.name not in skip_names]
        
        for i, item in enumerate(folders):
            is_last = (i == len(folders) - 1)
            
            display_name = f'{item.name}/'
            
            if is_last:
                tree += f'{prefix}└── {display_name}\n'
                next_prefix = f'{prefix}    '
            else:
                tree += f'{prefix}├── {display_name}\n'
                next_prefix = f'{prefix}│   '
            
            try:
                tree += self._get_folder_only_tree(item, next_prefix, rule_index)
            except PermissionError:
                tree += f'{next_prefix}└── [权限不足，无法访问]\n'
        
        return tree

    def _update_counts(self):
        """更新统计信息"""
        if not self.current_folder:
            return
        
        folder_count = 0
        file_count = 0
        
        for item in self.current_folder.rglob("*"):
            if item.is_dir():
                folder_count += 1
            else:
                file_count += 1
        
        self._folder_count_label.setText(f"文件夹: {folder_count}")
        self._file_count_label.setText(f"文件: {file_count}")

    def save_to_txt(self):
        """保存为txt（默认位置）"""
        if not self.tree_content:
            InfoBar.warning(
                title="无内容",
                content="请先生成树形结构",
                parent=self,
                duration=2000
            )
            return
        
        # 默认保存位置
        default_dir = Path("data/temp_text")
        default_dir.mkdir(parents=True, exist_ok=True)
        
        default_path = default_dir / f"{self.current_folder.name}_tree.txt"
        
        try:
            with open(default_path, "w", encoding="utf-8") as f:
                f.write(self.tree_content)
            
            InfoBar.success(
                title="保存成功",
                content=f"已保存到: {default_path}",
                parent=self,
                duration=2000
            )
            self._status_label.setText(f"已保存: {default_path.name}")
        except Exception as e:
            InfoBar.error(
                title="保存失败",
                content=str(e),
                parent=self,
                duration=2000
            )

    def save_as(self):
        """另存为"""
        if not self.tree_content:
            InfoBar.warning(
                title="无内容",
                content="请先生成树形结构",
                parent=self,
                duration=2000
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            f"{self.current_folder.name}_tree.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.tree_content)
                
                InfoBar.success(
                    title="保存成功",
                    content=f"已保存到: {file_path}",
                    parent=self,
                    duration=2000
                )
                self._status_label.setText(f"已保存: {Path(file_path).name}")
            except Exception as e:
                InfoBar.error(
                    title="保存失败",
                    content=str(e),
                    parent=self,
                    duration=2000
                )

    def show_rules(self):
        """显示规则设置"""
        InfoBar.info(
            title="规则设置",
            content="规则设置功能开发中...",
            parent=self,
            duration=2000
        )


class Plugin(PluginInterface):
    """文件夹树插件"""
    PLUGIN_ID = "folder_tree"
    PLUGIN_NAME = "文件夹树"
    PLUGIN_ICON = FIF.FOLDER
    PLUGIN_PRIORITY = 12

    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return FolderTreeWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        pass
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        from core import SearchResult
        db = DatabaseManager()
        results = []
        rules = db.search_folder_tree_rules(query)
        for rule in rules[:20]:
            exclude_items = json.loads(rule['exclude_items']) if rule['exclude_items'] else []
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=f"规则: {rule['rule_name']}",
                description=f"排除项: {', '.join(exclude_items[:5])}{'...' if len(exclude_items) > 5 else ''}",
                icon=self.PLUGIN_ICON,
                relevance=1.0,
                action=lambda: None,
                metadata={'rule_id': rule['id'], 'rule_name': rule['rule_name']}
            )
            results.append(result)
        return results
