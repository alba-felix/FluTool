"""
代办事项插件
提供任务管理功能，支持优先级、截止日期、标签、置顶等
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QDate, QTime, QTimer, QObject
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidgetItem, QHeaderView, QDateEdit, QTimeEdit, QSystemTrayIcon,
    QDialog
)
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, TreeWidget, StrongBodyLabel,
    setCustomStyleSheet, isDarkTheme, qconfig,
    MessageBoxBase, TransparentToolButton, CaptionLabel, ComboBox,
    TextEdit, CheckBox, SubtitleLabel, BodyLabel, MessageBox, RoundMenu,
    TeachingTip, TeachingTipTailPosition
)
from core import PluginInterface
from .service import TodoService


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
        self.title_input.returnPressed.connect(lambda: self.yesButton.click())
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
        self.due_time_edit = QTimeEdit()
        self.due_time_edit.setDisplayFormat("HH:mm")
        self.due_time_edit.setTime(QTime(23, 59))
        due_date_layout.addWidget(self.due_time_edit)
        self.viewLayout.addLayout(due_date_layout)
        
        self.viewLayout.addWidget(StrongBodyLabel("标签:", self))
        self.tags_input = LineEdit(self)
        self.tags_input.setPlaceholderText("用逗号分隔多个标签")
        self.tags_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.tags_input)

        remind_layout = QHBoxLayout()
        remind_layout.addWidget(StrongBodyLabel("提醒:", self))
        self.remind_combo = ComboBox(self)
        for _, label in TodoReminderManager.REMINDER_OPTIONS:
            self.remind_combo.addItem(label)
        self.remind_combo.setCurrentIndex(0)
        remind_layout.addWidget(self.remind_combo, 1)
        self.viewLayout.addLayout(remind_layout)

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
            "due_time": self.due_time_edit.time().toString("HH:mm"),
            "tags": [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()],
            "completed": False,
            "status": "进行中",
            "pinned": False,
            "remind_before": TodoReminderManager.REMINDER_OPTIONS[self.remind_combo.currentIndex()][0],
            "last_reminded": "",
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
        self.title_input.returnPressed.connect(lambda: self.yesButton.click())
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
        self.due_time_edit = QTimeEdit()
        self.due_time_edit.setDisplayFormat("HH:mm")
        due_date_layout.addWidget(self.due_time_edit)
        self.viewLayout.addLayout(due_date_layout)
        
        self.viewLayout.addWidget(StrongBodyLabel("标签:", self))
        self.tags_input = LineEdit(self)
        self.tags_input.setPlaceholderText("用逗号分隔多个标签")
        self.tags_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.tags_input)

        remind_layout = QHBoxLayout()
        remind_layout.addWidget(StrongBodyLabel("提醒:", self))
        self.remind_combo = ComboBox(self)
        for _, label in TodoReminderManager.REMINDER_OPTIONS:
            self.remind_combo.addItem(label)
        remind_layout.addWidget(self.remind_combo, 1)
        self.viewLayout.addLayout(remind_layout)

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
        
        due_time = self.todo_data.get("due_time", "23:59")
        self.due_time_edit.setTime(QTime.fromString(due_time, "HH:mm"))
        
        tags = self.todo_data.get("tags", [])
        self.tags_input.setText(", ".join(tags))
        
        remind_before = self.todo_data.get("remind_before", 0)
        self.remind_combo.setCurrentIndex(
            max(i for i, (v, _) in enumerate(TodoReminderManager.REMINDER_OPTIONS) if v <= remind_before)
        )
        
        self.completed_checkbox.setChecked(self.todo_data.get("completed", False))
        self.pinned_checkbox.setChecked(self.todo_data.get("pinned", False))
    
    def get_data(self) -> Dict[str, Any]:
        """获取对话框数据"""
        completed = self.completed_checkbox.isChecked()
        data = self.todo_data.copy()
        data.update({
            "title": self.title_input.text(),
            "description": self.description_input.toPlainText(),
            "priority": self.priority_combo.currentText(),
            "start_date": self.start_date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "due_time": self.due_time_edit.time().toString("HH:mm"),
            "tags": [tag.strip() for tag in self.tags_input.text().split(",") if tag.strip()],
            "completed": completed,
            "status": "已完成" if completed else self.todo_data.get("status", "进行中"),
            "pinned": self.pinned_checkbox.isChecked(),
            "remind_before": TodoReminderManager.REMINDER_OPTIONS[self.remind_combo.currentIndex()][0],
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return data


class TodoReminderManager(QObject):
    """待办事项提醒管理器"""

    REMINDER_OPTIONS = [
        (0, "不提醒"),
        (1, "1 分钟"),      # 临时测试
        (5, "5 分钟"),
        (30, "30 分钟"),
        (60, "1 小时前"),
        (120, "2 小时前"),
        (360, "6 小时前"),
        (720, "12 小时前"),
        (1440, "1 天前"),
        (2880, "2 天前"),
    ]

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._reminded_todos: set = set()

    def check_and_notify(self, todos: List[Dict]) -> None:
        """检查所有待办事项，在需要时发送提醒"""
        now = datetime.now()
        logger = getattr(self.core, 'logger', None)

        for todo in todos:
            if todo.get("completed", False):
                continue

            remind_before = todo.get("remind_before", 0)
            if remind_before <= 0:
                continue

            due_date = todo.get("due_date", "")
            if not due_date:
                continue

            due_time = todo.get("due_time", "23:59")
            try:
                deadline = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    deadline = datetime.strptime(f"{due_date} 23:59", "%Y-%m-%d %H:%M")
                except ValueError:
                    continue

            if now > deadline:
                if logger:
                    logger.info(f"[提醒] 待办已过期，跳过: {todo.get('title')}")
                continue

            remaining = deadline - now
            remaining_minutes = remaining.total_seconds() / 60

            if logger:
                logger.info(f"[提醒] 待办 '{todo.get('title')}' 剩余 {remaining_minutes:.1f} 分钟, 阈值 {remind_before} 分钟")

            if not (0 < remaining_minutes <= remind_before):
                continue

            key = (todo.get("id"), due_date)
            if key in self._reminded_todos:
                if logger:
                    logger.info(f"[提醒] 已会话提醒过，跳过: {todo.get('title')}")
                continue

            last_reminded = todo.get("last_reminded", "")
            if last_reminded:
                try:
                    last_time = datetime.fromisoformat(last_reminded)
                    cooldown_minutes = min(remind_before / 2, 60)
                    if (now - last_time).total_seconds() < cooldown_minutes * 60:
                        if logger:
                            logger.info(f"[提醒] 冷却中，跳过: {todo.get('title')}")
                        continue
                except (ValueError, TypeError):
                    pass

            if logger:
                logger.info(f"[提醒] 触发通知: {todo.get('title')}")
            self._show_notification(todo, remaining_minutes)
            self._reminded_todos.add(key)

    def _show_notification(self, todo: Dict, remaining_minutes: float) -> None:
        """显示提醒通知（独立置顶弹窗，手动关闭）"""
        title = todo.get("title", "未命名")
        logger = getattr(self.core, 'logger', None)

        if remaining_minutes < 60:
            time_text = f"{int(remaining_minutes)} 分钟"
        else:
            hours = int(remaining_minutes / 60)
            time_text = f"{hours} 小时"

        message = f"代办事项「{title}」将在 {time_text} 后到期"

        try:
            dialog = QDialog(None, Qt.WindowStaysOnTopHint | Qt.Dialog)
            dialog.setWindowTitle("代办事项提醒")
            dialog.setFixedSize(400, 160)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(15)

            title_label = BodyLabel("代办事项提醒", dialog)
            title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            layout.addWidget(title_label)

            msg_label = BodyLabel(message, dialog)
            msg_label.setWordWrap(True)
            layout.addWidget(msg_label)

            layout.addStretch()
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            ok_btn = PushButton("知道了", dialog)
            ok_btn.setFixedWidth(120)
            ok_btn.clicked.connect(dialog.close)
            btn_layout.addWidget(ok_btn)
            layout.addLayout(btn_layout)

            qconfig.themeChanged.connect(
                lambda: self._style_notification_dialog(dialog)
            )
            self._style_notification_dialog(dialog)
            dialog.show()

            if logger:
                logger.info(f"[提醒] 独立弹窗已显示: {title}")
        except Exception as e:
            if logger:
                logger.warning(f"[提醒] 独立弹窗失败: {e}")

    @staticmethod
    def _style_notification_dialog(dialog: QDialog) -> None:
        """设置提醒弹窗样式"""
        bg = "#2d2d2d" if isDarkTheme() else "#ffffff"
        fg = "#ffffff" if isDarkTheme() else "#000000"
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }}
        """)

    def clear_reminded(self, todo_id: int) -> None:
        """清除某条待办的已提醒状态（编辑后重置）"""
        self._reminded_todos = {k for k in self._reminded_todos if k[0] != todo_id}

    def get_remind_before_index(self, remind_before: int) -> int:
        """根据提醒小时数获取 ComboBox 索引"""
        for i, (value, _) in enumerate(self.REMINDER_OPTIONS):
            if value == remind_before:
                return i
        return 0


class TodoWidget(QWidget):
    """代办事项管理组件"""
    
    PLUGIN_ID = "todo"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = TodoService()
        self.todos: List[Dict[str, Any]] = []
        self._reminder_manager = TodoReminderManager(core, self)

        self._setup_ui()
        self._load_todos()
        self._setup_timer()
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """设置事件监听器"""
        if hasattr(self, 'core') and self.core and hasattr(self.core, 'event_bus'):
            self.core.event_bus.listen("data_restored", lambda _: self._on_data_restored())

    def _on_data_restored(self):
        """数据恢复后刷新"""
        self._load_todos()
    
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
        self.tree.setColumnWidth(0, 100)
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
        """设置自适应定时器"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_and_optimize_timer)
        self.timer.start(15000)
        self._check_and_optimize_timer()

    def _check_and_optimize_timer(self):
        """检查提醒并动态调整下次检查间隔"""
        self._check_overdue_tasks()

        now = datetime.now()
        next_check = float('inf')

        for todo in self.todos:
            if todo.get("completed", False):
                continue
            remind_before = todo.get("remind_before", 0)
            if remind_before <= 0:
                continue
            due_date = todo.get("due_date", "")
            if not due_date:
                continue
            due_time = todo.get("due_time", "23:59")
            try:
                deadline = datetime.strptime(f"{due_date} {due_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    deadline = datetime.strptime(f"{due_date} 23:59", "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
            if now > deadline:
                continue
            trigger_time = deadline.replace(second=0) - timedelta(minutes=remind_before)
            if trigger_time <= now:
                # 已经在提醒窗口内，应保持高频检查
                next_check = min(next_check, 15)
            else:
                seconds_until = (trigger_time - now).total_seconds()
                if seconds_until < next_check:
                    next_check = seconds_until

        overdue_exists = any(
            not todo.get("completed", False) and todo.get("due_date", "") and
            todo.get("due_date", "") < now.strftime("%Y-%m-%d")
            for todo in self.todos
        )

        if overdue_exists:
            next_check = min(next_check, 300)

        if next_check == float('inf'):
            next_check = 1800

        if next_check < 60:
            interval = 15000
        elif next_check < 300:
            interval = 30000
        elif next_check < 1800:
            interval = 60000
        elif next_check < 7200:
            interval = 300000
        elif next_check < 43200:
            interval = 900000
        else:
            interval = 1800000

        if self.timer.interval() != interval:
            self.timer.setInterval(interval)
    
    def _load_todos(self):
        """从数据库加载代办事项"""
        try:
            self.todos = self.service.list_todos()
            for todo in self.todos:
                if "status" not in todo:
                    todo["status"] = "已完成" if todo.get("completed", False) else "进行中"
        except Exception as e:
            self.core.logger.error(f"加载代办事项失败: {e}")
            self.todos = []
        
        self._display_todos()
        self._update_stats()
        self._check_and_optimize_timer()
    
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
                status = "✓已完成"
            else:
                todo_status = todo.get("status", "进行中")
                if todo_status == "未完成":
                    status = "○未完成"
                else:
                    status = "▶进行中"
            
            if todo.get("pinned", False):
                status = "📌" + status
            
            item.setText(0, status)
            item.setText(1, todo.get("title", "未命名"))
            item.setText(2, todo.get("priority", "中"))
            item.setText(3, todo.get("created_at", ""))
            due_date = todo.get("due_date", "")
            due_time = todo.get("due_time", "")
            if due_date:
                if due_time and due_time != "23:59":
                    display = f"{due_date} {due_time}"
                else:
                    display = due_date
            else:
                display = ""
            item.setText(4, display)
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
                todo_id = self.service.add_todo(todo_data)
                todo_data["id"] = todo_id
                self.todos.append(todo_data)
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
                # 记录操作日志
                if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                    self.core.logger.log_operation("CREATE", f"添加待办事项: {todo_data['title']}")
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
                todo_id = todo_data.get("id")
                if todo_id:
                    self.service.update_todo(todo_id, updated_data)
                    self._reminder_manager.clear_reminded(todo_id)
                self.todos[todo_idx] = updated_data
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
                # 记录操作日志
                if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                    self.core.logger.log_operation("UPDATE", f"更新待办事项: {updated_data['title']}")
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
            todo["status"] = "已完成"
        else:
            todo.pop("completed_at", None)
            todo["status"] = "未完成"

        todo_id = todo.get("id")
        if todo_id:
            self.service.toggle_completed(todo_id)

        self._display_todos()
        self._update_stats()

        status_msg = todo["status"]
        InfoBar.success(
            title="状态变更",
            content=f"'{todo.get('title', '未命名')}' 已标记为{status_msg}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
        # 记录操作日志
        if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
            self.core.logger.log_operation("UPDATE", f"标记待办事项为{status_msg}: {todo.get('title', '未命名')}")
    
    def _toggle_pin(self, item: QTreeWidgetItem):
        """切换置顶状态"""
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo = self.todos[todo_idx]
        
        todo["pinned"] = not todo.get("pinned", False)
        
        todo_id = todo.get("id")
        if todo_id:
            self.service.toggle_pinned(todo_id)
        
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

        box = MessageBox("删除代办事项", f"确定要删除 '{todo.get('title', '未命名')}' 吗？", self)
        if box.exec():
            todo_id = todo.get("id")
            todo_title = todo.get('title', '未命名')
            if todo_id:
                self.service.delete_todo(todo_id)
            del self.todos[todo_idx]
            self._display_todos()
            self._update_stats()
            InfoBar.success(
                title="删除成功",
                content=f"已删除代办事项 '{todo_title}'",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            # 记录操作日志
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("DELETE", f"删除待办事项: {todo_title}")
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        from PyQt5.QtGui import QCursor
        from PyQt5.QtWidgets import QAction
        
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        todo_idx = item.data(0, Qt.UserRole)
        if todo_idx is None or todo_idx >= len(self.todos):
            return
        todo = self.todos[todo_idx]
        
        menu = RoundMenu(parent=self)
        
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
        """检查过期任务和提醒"""
        today = datetime.now().strftime("%Y-%m-%d")
        overdue_count = sum(1 for todo in self.todos
                             if not todo.get("completed", False) and
                             todo.get("due_date", "") and
                             todo.get("due_date", "") < today)
        
        if overdue_count > 0:
            self._update_stats()
        
        self._reminder_manager.check_and_notify(self.todos)
    
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
        
        box = MessageBox("确认操作", f"确定要将 {completed_count} 个已完成任务标记为未完成吗？", self)
        if box.exec():
            for todo in self.todos:
                if todo.get("completed", False):
                    todo["completed"] = False
                    todo["status"] = "未完成"
                    todo.pop("completed_at", None)
                    todo_id = todo.get("id")
                    if todo_id:
                        self.service.update_fields(todo_id, completed=0, status="未完成")

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
            # 记录操作日志
            if hasattr(self, 'core') and self.core and hasattr(self.core, 'logger'):
                self.core.logger.log_operation("UPDATE", f"批量标记{completed_count}个任务为未完成")
    
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
    PLUGIN_PRIORITY = 11
    
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
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        from core import SearchResult
        results = []
        todos = TodoService().search(query)
        for todo in todos[:20]:
            completed = todo.get('completed', False)
            todo_status = todo.get('status', '')
            if completed:
                status = "✓已完成"
            elif todo_status == "未完成":
                status = "○未完成"
            else:
                status = "▶进行中"
            pinned = "📌" if todo['pinned'] else ""
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=f"{pinned}{status} {todo['title']}",
                description=f"优先级: {todo['priority']} | 截止: {todo['due_date'] or '无'}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if todo['pinned'] else 0.8,
                action=lambda t=todo['title']: QApplication.clipboard().setText(t),
                metadata={'todo_id': todo['id']}
            )
            results.append(result)
        return results
