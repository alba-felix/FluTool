"""
代办事项插件
提供任务管理功能，支持优先级、截止日期、标签、置顶等
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem, QHeaderView, QDateEdit
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, TreeWidget, StrongBodyLabel,
    setCustomStyleSheet, isDarkTheme, qconfig,
    MessageBoxBase, TransparentToolButton, CaptionLabel, ComboBox,
    TextEdit, CheckBox, SubtitleLabel, BodyLabel
)
from core.plugin_interface import PluginInterface


class AddTodoDialog(MessageBoxBase):
    """添加代办事项对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("添加代办事项", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """构建界面"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        self.title_input = LineEdit(self)
        self.title_input.setPlaceholderText("输入标题...")
        self.viewLayout.addWidget(StrongBodyLabel("标题:", self))
        self.viewLayout.addWidget(self.title_input)
        
        self.description_input = TextEdit(self)
        self.description_input.setPlaceholderText("输入描述...")
        self.description_input.setMinimumHeight(80)
        self.viewLayout.addWidget(StrongBodyLabel("描述:", self))
        self.viewLayout.addWidget(self.description_input)
        
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(StrongBodyLabel("优先级:", self))
        self.priority_combo = ComboBox(self)
        self.priority_combo.addItems(["低", "中", "高", "紧急"])
        self.priority_combo.setCurrentIndex(1)
        priority_layout.addWidget(self.priority_combo, 1)
        self.viewLayout.addLayout(priority_layout)
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(StrongBodyLabel("开始日期:", self))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.start_date_edit, 1)
        self.viewLayout.addLayout(date_layout)
        
        due_date_layout = QHBoxLayout()
        due_date_layout.addWidget(StrongBodyLabel("截止日期:", self))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setDate(QDate.currentDate().addDays(7))
        self.due_date_edit.setCalendarPopup(True)
        due_date_layout.addWidget(self.due_date_edit, 1)
        self.viewLayout.addLayout(due_date_layout)
        
        self.viewLayout.addWidget(StrongBodyLabel("标签:", self))
        self.tags_input = LineEdit(self)
        self.tags_input.setPlaceholderText("用逗号分隔多个标签")
        self.viewLayout.addWidget(self.tags_input)
        
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(400)
    
    def get_data(self) -> Dict[str, Any]:
        """获取对话框数据"""
        return {
            "title": self.title_input.text(),
            "description": self.description_input.toPlainText(),
            "priority": self.priority_combo.currentText(),
            "start_date": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "tags": [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()],
            "completed": False,
            "pinned": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


class EditTodoDialog(MessageBoxBase):
    """编辑代办事项对话框"""
    
    def __init__(self, todo_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.todo_data = todo_data
        self.titleLabel = SubtitleLabel("编辑代办事项", self)
        self.viewLayout.addWidget(self.titleLabel)
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """构建界面"""
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        self.title_input = LineEdit(self)
        self.title_input.setPlaceholderText("输入标题...")
        self.viewLayout.addWidget(StrongBodyLabel("标题:", self))
        self.viewLayout.addWidget(self.title_input)
        
        self.description_input = TextEdit(self)
        self.description_input.setPlaceholderText("输入描述...")
        self.description_input.setMinimumHeight(80)
        self.viewLayout.addWidget(StrongBodyLabel("描述:", self))
        self.viewLayout.addWidget(self.description_input)
        
        priority_layout = QHBoxLayout()
        priority_layout.addWidget(StrongBodyLabel("优先级:", self))
        self.priority_combo = ComboBox(self)
        self.priority_combo.addItems(["低", "中", "高", "紧急"])
        priority_layout.addWidget(self.priority_combo, 1)
        self.viewLayout.addLayout(priority_layout)
        
        date_layout = QHBoxLayout()
        date_layout.addWidget(StrongBodyLabel("开始日期:", self))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        date_layout.addWidget(self.start_date_edit, 1)
        self.viewLayout.addLayout(date_layout)
        
        due_date_layout = QHBoxLayout()
        due_date_layout.addWidget(StrongBodyLabel("截止日期:", self))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        due_date_layout.addWidget(self.due_date_edit, 1)
        self.viewLayout.addLayout(due_date_layout)
        
        self.viewLayout.addWidget(StrongBodyLabel("标签:", self))
        self.tags_input = LineEdit(self)
        self.tags_input.setPlaceholderText("用逗号分隔多个标签")
        self.viewLayout.addWidget(self.tags_input)
        
        self.completed_checkbox = CheckBox("已完成", self)
        self.viewLayout.addWidget(self.completed_checkbox)
        
        self.pinned_checkbox = CheckBox("置顶", self)
        self.viewLayout.addWidget(self.pinned_checkbox)
        
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        
        self.widget.setMinimumWidth(400)
    
    def _load_data(self):
        """加载现有数据"""
        self.title_input.setText(self.todo_data.get("title", ""))
        self.description_input.setPlainText(self.todo_data.get("description", ""))
        
        priority = self.todo_data.get("priority", "中")
        index = self.priority_combo.findText(priority)
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)
        
        start_date = self.todo_data.get("start_date", "")
        if start_date:
            self.start_date_edit.setDate(QDate.fromString(start_date, "yyyy-MM-dd"))
        else:
            self.start_date_edit.setDate(QDate.currentDate())
        
        due_date = self.todo_data.get("due_date", "")
        if due_date:
            self.due_date_edit.setDate(QDate.fromString(due_date, "yyyy-MM-dd"))
        else:
            self.due_date_edit.setDate(QDate.currentDate().addDays(7))
        
        tags = self.todo_data.get("tags", [])
        self.tags_input.setText(", ".join(tags))
        
        self.completed_checkbox.setChecked(self.todo_data.get("completed", False))
        self.pinned_checkbox.setChecked(self.todo_data.get("pinned", False))
    
    def get_data(self) -> Dict[str, Any]:
        """获取对话框数据"""
        data = self.todo_data.copy()
        data.update({
            "title": self.title_input.text(),
            "description": self.description_input.toPlainText(),
            "priority": self.priority_combo.currentText(),
            "start_date": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "tags": [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()],
            "completed": self.completed_checkbox.isChecked(),
            "pinned": self.pinned_checkbox.isChecked(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return data


class TodoWidget(QWidget):
    """代办事项管理组件"""
    
    PLUGIN_ID = "todo"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.todos: List[Dict[str, Any]] = []
        
        self._init_paths()
        self._setup_ui()
        self._load_todos()
        self._setup_timer()
    
    def _init_paths(self):
        """初始化路径"""
        base_dir = Path(__file__).parent.parent.parent
        self.data_dir = base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.json_file = self.data_dir / "todos.json"
    
    def _setup_ui(self):
        """构建界面"""
        self.setObjectName("todoWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self.add_btn = PushButton("添加", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_todo)
        header_layout.addWidget(self.add_btn)
        
        self.mark_uncompleted_btn = PushButton("全部未完成", self)
        self.mark_uncompleted_btn.clicked.connect(self._mark_all_uncompleted)
        header_layout.addWidget(self.mark_uncompleted_btn)
        
        header_layout.addStretch()
        
        header_layout.addWidget(StrongBodyLabel("过滤:", self))
        self.filter_combo = ComboBox(self)
        self.filter_combo.addItems(["全部", "未完成", "已完成", "今日到期", "过期"])
        self.filter_combo.currentTextChanged.connect(self._filter_todos)
        header_layout.addWidget(self.filter_combo)
        
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索代办事项...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_todos)
        header_layout.addWidget(self.search_input, 1)
        
        main_layout.addLayout(header_layout)
        
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["状态", "标题", "优先级", "创建时间", "截止日期", "标签"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(3, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(4, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(5, QHeaderView.Fixed)
        self.tree.setColumnWidth(0, 60)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 150)
        self.tree.setColumnWidth(4, 100)
        self.tree.setColumnWidth(5, 150)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._edit_todo)
        self.tree.setSelectionMode(self.tree.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        
        self._apply_tree_style()
        qconfig.themeChangedFinished.connect(self._apply_tree_style)
        
        main_layout.addWidget(self.tree)
        
        self.stats_label = CaptionLabel("就绪", self)
        main_layout.addWidget(self.stats_label)
    
    def _apply_tree_style(self):
        """应用树形列表样式"""
        header = self.tree.header()
        
        if isDarkTheme():
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: transparent;
                    alternate-background-color: #252525;
                    border: none;
                }
                QTreeWidget::item {
                    padding: 6px;
                    border-radius: 4px;
                }
                QTreeWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QTreeWidget::item:hover {
                    background-color: #3d3d3d;
                }
            """)
            header.setStyleSheet("""
                QHeaderView::section {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: none;
                    border-bottom: 1px solid #3d3d3d;
                    padding: 8px;
                    font-weight: 500;
                }
            """)
        else:
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: transparent;
                    alternate-background-color: #f5f5f5;
                    border: none;
                }
                QTreeWidget::item {
                    padding: 6px;
                    border-radius: 4px;
                }
                QTreeWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QTreeWidget::item:hover {
                    background-color: #e5e5e5;
                }
            """)
            header.setStyleSheet("""
                QHeaderView::section {
                    background-color: #ffffff;
                    color: #000000;
                    border: none;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 8px;
                    font-weight: 500;
                }
            """)
    
    def _setup_timer(self):
        """设置定时器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_overdue_tasks)
        self.timer.start(60000)
    
    def _load_todos(self):
        """从文件加载代办事项"""
        try:
            if self.json_file.exists() and self.json_file.stat().st_size > 0:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.todos = data.get("todos", [])
            else:
                self.todos = []
                self._save_todos()
        except Exception as e:
            self.core.logger.error(f"加载代办事项失败: {e}")
            self.todos = []
        
        self._display_todos()
        self._update_stats()
    
    def _save_todos(self):
        """保存代办事项到文件"""
        try:
            temp_file = str(self.json_file) + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump({"todos": self.todos}, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, str(self.json_file))
        except Exception as e:
            self.core.logger.error(f"保存代办事项失败: {e}")
            InfoBar.error(
                title="保存失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _display_todos(self):
        """显示代办事项列表"""
        self.tree.clear()
        
        pinned_todos = [(todo, idx) for idx, todo in enumerate(self.todos) if todo.get("pinned", False)]
        unpinned_todos = [(todo, idx) for idx, todo in enumerate(self.todos) if not todo.get("pinned", False)]
        
        pinned_todos.sort(key=lambda x: x[0].get("created_at", ""), reverse=True)
        unpinned_todos.sort(key=lambda x: x[0].get("created_at", ""), reverse=True)
        
        for todo, idx in pinned_todos + unpinned_todos:
            item = QTreeWidgetItem()
            
            if todo.get("completed", False):
                status = "✓"
            else:
                priority = todo.get("priority", "中")
                if priority == "紧急":
                    status = "❗"
                elif priority == "高":
                    status = "⚠️"
                else:
                    status = "⭕"
            
            if todo.get("pinned", False):
                status = "📌" + status
            
            item.setText(0, status)
            item.setText(1, todo.get("title", "未命名"))
            item.setText(2, todo.get("priority", "中"))
            item.setText(3, todo.get("created_at", ""))
            item.setText(4, todo.get("due_date", ""))
            item.setText(5, ", ".join(todo.get("tags", [])))
            item.setData(0, Qt.UserRole, idx)
            
            if todo.get("completed", False):
                for col in range(6):
                    item.setForeground(col, Qt.gray)
            else:
                priority = todo.get("priority", "中")
                if priority == "紧急":
                    for col in range(6):
                        item.setForeground(col, Qt.red)
                        font = item.font(col)
                        font.setBold(True)
                        item.setFont(col, font)
                elif priority == "高":
                    for col in range(6):
                        item.setForeground(col, QColor(200, 0, 0))
            
            self.tree.addTopLevelItem(item)
    
    def _filter_todos(self):
        """过滤代办事项"""
        filter_text = self.filter_combo.currentText()
        search_text = self.search_input.text().lower()
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            todo_idx = item.data(0, Qt.UserRole)
            if todo_idx is None or todo_idx >= len(self.todos):
                continue
            todo = self.todos[todo_idx]
            
            show_item = True
            
            if filter_text == "未完成" and todo.get("completed", False):
                show_item = False
            elif filter_text == "已完成" and not todo.get("completed", False):
                show_item = False
            elif filter_text == "今日到期":
                due_date = todo.get("due_date", "")
                today = datetime.now().strftime("%Y-%m-%d")
                if due_date != today:
                    show_item = False
            elif filter_text == "过期":
                due_date = todo.get("due_date", "")
                today = datetime.now().strftime("%Y-%m-%d")
                if not due_date or due_date >= today or todo.get("completed", False):
                    show_item = False
            
            if search_text and show_item:
                title = todo.get("title", "").lower()
                description = todo.get("description", "").lower()
                tags = " ".join(todo.get("tags", [])).lower()
                if search_text not in title and search_text not in description and search_text not in tags:
                    show_item = False
            
            item.setHidden(not show_item)
    
    def _update_stats(self):
        """更新统计信息"""
        total = len(self.todos)
        completed = sum(1 for todo in self.todos if todo.get("completed", False))
        pending = total - completed
        
        urgent_pending = sum(1 for todo in self.todos
                         if not todo.get("completed", False) and todo.get("priority", "中") == "紧急")
        high_pending = sum(1 for todo in self.todos
                        if not todo.get("completed", False) and todo.get("priority", "中") == "高")
        
        today = datetime.now().strftime("%Y-%m-%d")
        overdue = sum(1 for todo in self.todos
                     if not todo.get("completed", False) and
                     todo.get("due_date", "") and
                     todo.get("due_date", "") < today)
        
        self.stats_label.setText(
            f"总计: {total} | 待完成: {pending} (紧急: {urgent_pending} ❗ | 高: {high_pending} ⚠️) | 已完成: {completed} | 过期: {overdue}"
        )
    
    def _add_todo(self):
        """添加代办事项"""
        dialog = AddTodoDialog(self)
        if dialog.exec():
            todo_data = dialog.get_data()
            if todo_data["title"]:
                self.todos.append(todo_data)
                self._save_todos()
                self._display_todos()
                self._update_stats()
                InfoBar.success(
                    title="添加成功",
                    content=f"已添加代办事项 '{todo_data['title']}'",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                InfoBar.warning(
                    title="输入错误",
                    content="标题不能为空",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _edit_todo(self, item: QTreeWidgetItem, column: int):
        """编辑代办事项"""
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo_data = self.todos[todo_idx]
        
        dialog = EditTodoDialog(todo_data, self)
        if dialog.exec():
            updated_data = dialog.get_data()
            if updated_data["title"]:
                self.todos[todo_idx] = updated_data
                self._save_todos()
                self._display_todos()
                self._update_stats()
                InfoBar.success(
                    title="修改成功",
                    content=f"已更新代办事项 '{updated_data['title']}'",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                InfoBar.warning(
                    title="输入错误",
                    content="标题不能为空",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _toggle_status(self, item: QTreeWidgetItem):
        """切换完成状态"""
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo = self.todos[todo_idx]
        
        todo["completed"] = not todo.get("completed", False)
        if todo["completed"]:
            todo["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            todo.pop("completed_at", None)
        
        self._save_todos()
        self._display_todos()
        self._update_stats()
        
        status_msg = "已完成" if todo["completed"] else "未完成"
        InfoBar.success(
            title="状态变更",
            content=f"'{todo.get('title', '未命名')}' 已标记为{status_msg}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _toggle_pin(self, item: QTreeWidgetItem):
        """切换置顶状态"""
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo = self.todos[todo_idx]
        
        todo["pinned"] = not todo.get("pinned", False)
        self._save_todos()
        self._display_todos()
        self._update_stats()
        
        status_msg = "已置顶" if todo["pinned"] else "已取消置顶"
        InfoBar.success(
            title="置顶变更",
            content=f"'{todo.get('title', '未命名')}' {status_msg}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _delete_todo(self, item: QTreeWidgetItem):
        """删除代办事项"""
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo = self.todos[todo_idx]
        
        box = MessageBoxBase("删除代办事项", f"确定要删除 '{todo.get('title', '未命名')}' 吗？", self)
        if box.exec():
            del self.todos[todo_idx]
            self._save_todos()
            self._display_todos()
            self._update_stats()
            InfoBar.success(
                title="删除成功",
                content=f"已删除代办事项 '{todo.get('title', '未命名')}'",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        from PyQt5.QtGui import QCursor
        from PyQt5.QtWidgets import QMenu, QAction
        
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo = self.todos[todo_idx]
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        if todo.get("completed", False):
            toggle_action = QAction("标记为未完成", self)
        else:
            toggle_action = QAction("标记为已完成", self)
        toggle_action.triggered.connect(lambda: self._toggle_status(item))
        menu.addAction(toggle_action)
        
        if todo.get("pinned", False):
            pin_action = QAction("取消置顶", self)
        else:
            pin_action = QAction("置顶", self)
        pin_action.triggered.connect(lambda: self._toggle_pin(item))
        menu.addAction(pin_action)
        
        menu.addSeparator()
        
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self._edit_todo(item, 0))
        menu.addAction(edit_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_todo(item))
        menu.addAction(delete_action)
        
        menu.exec_(QCursor.pos())
    
    def _check_overdue_tasks(self):
        """检查过期任务"""
        today = datetime.now().strftime("%Y-%m-%d")
        overdue_count = sum(1 for todo in self.todos
                             if not todo.get("completed", False) and
                             todo.get("due_date", "") and
                             todo.get("due_date", "") < today)
        
        if overdue_count > 0:
            self._update_stats()
    
    def _mark_all_uncompleted(self):
        """批量标记所有任务为未完成"""
        completed_count = sum(1 for todo in self.todos if todo.get("completed", False))
        
        if completed_count == 0:
            InfoBar.info(
                title="提示",
                content="当前没有已完成的任务需要标记为未完成",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        box = MessageBoxBase("确认操作", f"确定要将 {completed_count} 个已完成任务标记为未完成吗？", self)
        if box.exec():
            for todo in self.todos:
                if todo.get("completed", False):
                    todo["completed"] = False
                    todo.pop("completed_at", None)
            
            self._save_todos()
            self._display_todos()
            self._update_stats()
            InfoBar.success(
                title="操作完成",
                content=f"已成功将 {completed_count} 个任务标记为未完成状态",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def load_data(self) -> None:
        """加载数据"""
        self._load_todos()
    
    def showEvent(self, event):
        """窗口显示时刷新"""
        super().showEvent(event)
        self._load_todos()


class Plugin(PluginInterface):
    """代办事项插件"""
    
    PLUGIN_ID = "todo"
    PLUGIN_NAME = "代办事项"
    PLUGIN_ICON = FIF.CALENDAR
    PLUGIN_PRIORITY = 7
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return TodoWidget(self.core, parent)
    
    def load_data(self) -> None:
        """加载数据"""
        if self._widget:
            self._widget.load_data()
