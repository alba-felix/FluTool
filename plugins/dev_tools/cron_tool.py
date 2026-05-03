"""Cron 表达式生成器"""

from typing import Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QRadioButton, QButtonGroup, QSpinBox,
    QCheckBox, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    FluentIcon as FIF, LineEdit, PushButton,
    TextEdit, ComboBox, InfoBar, InfoBarPosition,
    SegmentedWidget, StrongBodyLabel,
    qconfig, isDarkTheme
)

from plugins.text_tools.page_interface import TabPageInterface


class CronFieldWidget(QFrame):
    """Cron 字段配置组件（秒/分钟/小时/日/月/星期/年）"""
    
    def __init__(self, field_name: str, min_val: int, max_val: int, parent=None):
        super().__init__(parent)
        self.field_name = field_name
        self.min_val = min_val
        self.max_val = max_val
        self.setObjectName("cronFieldWidget")
        self.setFrameShape(QFrame.StyledPanel)
        self._setup_ui()
        self._update_style()
        qconfig.themeChanged.connect(self._update_style)
    
    def _update_style(self):
        """更新样式"""
        dark = isDarkTheme()
        if dark:
            self.setStyleSheet("""
                QFrame#cronFieldWidget {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                    border: 1px solid #3d3d3d;
                }
                QLabel, QRadioButton, QCheckBox, QSpinBox, QComboBox {
                    color: #ffffff;
                }
                QRadioButton::indicator, QCheckBox::indicator {
                    background-color: #3d3d3d;
                    border: 1px solid #5d5d5d;
                    border-radius: 2px;
                }
                QSpinBox {
                    background-color: #3d3d3d;
                    border: 1px solid #5d5d5d;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#cronFieldWidget {
                    background-color: #ffffff;
                    border-radius: 8px;
                    border: 1px solid #e0e0e0;
                }
                QLabel, QRadioButton, QCheckBox, QSpinBox, QComboBox {
                    color: #333333;
                }
                QRadioButton::indicator, QCheckBox::indicator {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 2px;
                }
                QSpinBox {
                    background-color: #f5f5f5;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(6)
        
        # 单选按钮组
        self.button_group = QButtonGroup(self)
        
        # 1. 每X
        self.radio_every = QRadioButton(f"每{self.field_name}", self)
        self.radio_every.setChecked(True)
        self.button_group.addButton(self.radio_every, 0)
        layout.addWidget(self.radio_every)
        
        # 2. 周期
        period_layout = QHBoxLayout()
        self.radio_period = QRadioButton("周期：从", self)
        self.button_group.addButton(self.radio_period, 1)
        period_layout.addWidget(self.radio_period)
        
        self.spin_period_start = QSpinBox(self)
        self.spin_period_start.setRange(self.min_val, self.max_val)
        self.spin_period_start.setValue(self.min_val)
        self.spin_period_start.setEnabled(False)
        period_layout.addWidget(self.spin_period_start)
        
        period_layout.addWidget(QLabel("-", self))
        
        self.spin_period_end = QSpinBox(self)
        self.spin_period_end.setRange(self.min_val, self.max_val)
        self.spin_period_end.setValue(self.max_val)
        self.spin_period_end.setEnabled(False)
        period_layout.addWidget(self.spin_period_end)
        
        period_layout.addWidget(QLabel(self.field_name, self))
        period_layout.addStretch()
        layout.addLayout(period_layout)
        
        # 3. 从X开始，每Y执行一次
        step_layout = QHBoxLayout()
        self.radio_step = QRadioButton("从", self)
        self.button_group.addButton(self.radio_step, 2)
        step_layout.addWidget(self.radio_step)
        
        self.spin_step_start = QSpinBox(self)
        self.spin_step_start.setRange(self.min_val, self.max_val)
        self.spin_step_start.setValue(self.min_val)
        self.spin_step_start.setEnabled(False)
        step_layout.addWidget(self.spin_step_start)
        
        step_layout.addWidget(QLabel(f"{self.field_name}开始，每", self))
        
        self.spin_step_interval = QSpinBox(self)
        self.spin_step_interval.setRange(1, self.max_val)
        self.spin_step_interval.setValue(1)
        self.spin_step_interval.setEnabled(False)
        step_layout.addWidget(self.spin_step_interval)
        
        step_layout.addWidget(QLabel(f"{self.field_name}执行一次", self))
        step_layout.addStretch()
        layout.addLayout(step_layout)
        
        # 4. 指定
        self.radio_specific = QRadioButton("指定：", self)
        self.button_group.addButton(self.radio_specific, 3)
        layout.addWidget(self.radio_specific)
        
        # 复选框网格
        checkbox_widget = QWidget(self)
        checkbox_layout = QGridLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(20, 0, 0, 0)
        checkbox_layout.setSpacing(5)
        
        self.checkboxes = []
        cols = 10
        for i in range(self.min_val, self.max_val + 1):
            cb = QCheckBox(str(i), self)
            cb.setEnabled(False)
            self.checkboxes.append(cb)
            row = (i - self.min_val) // cols
            col = (i - self.min_val) % cols
            checkbox_layout.addWidget(cb, row, col)
        
        layout.addWidget(checkbox_widget)
        
        # 连接信号
        self.button_group.buttonClicked.connect(self._on_mode_changed)
        self.radio_every.toggled.connect(self._update_ui_state)
        self.radio_period.toggled.connect(self._update_ui_state)
        self.radio_step.toggled.connect(self._update_ui_state)
        self.radio_specific.toggled.connect(self._update_ui_state)
    
    def _on_mode_changed(self) -> None:
        self._update_ui_state()
    
    def _update_ui_state(self) -> None:
        mode = self.button_group.checkedId()
        
        self.spin_period_start.setEnabled(mode == 1)
        self.spin_period_end.setEnabled(mode == 1)
        self.spin_step_start.setEnabled(mode == 2)
        self.spin_step_interval.setEnabled(mode == 2)
        for cb in self.checkboxes:
            cb.setEnabled(mode == 3)
    
    def get_expression(self) -> str:
        mode = self.button_group.checkedId()
        
        if mode == 0:  # 每X
            return "*"
        elif mode == 1:  # 周期
            start = self.spin_period_start.value()
            end = self.spin_period_end.value()
            return f"{start}-{end}"
        elif mode == 2:  # 步长
            start = self.spin_step_start.value()
            interval = self.spin_step_interval.value()
            if start == self.min_val and interval == 1:
                return "*"
            return f"{start}/{interval}"
        elif mode == 3:  # 指定
            selected = []
            for i, cb in enumerate(self.checkboxes):
                if cb.isChecked():
                    selected.append(str(i + self.min_val))
            if not selected:
                return "*"
            return ",".join(selected)
        
        return "*"
    
    def set_expression(self, expr: str) -> None:
        if expr == "*" or expr == "?":
            self.radio_every.setChecked(True)
            return
        
        if "/" in expr:
            parts = expr.split("/")
            if len(parts) == 2:
                self.radio_step.setChecked(True)
                self.spin_step_start.setValue(int(parts[0]) if parts[0] != "*" else self.min_val)
                self.spin_step_interval.setValue(int(parts[1]))
                return
        
        if "-" in expr:
            parts = expr.split("-")
            if len(parts) == 2:
                self.radio_period.setChecked(True)
                self.spin_period_start.setValue(int(parts[0]))
                self.spin_period_end.setValue(int(parts[1]))
                return
        
        if "," in expr or expr.isdigit():
            self.radio_specific.setChecked(True)
            values = [int(v) for v in expr.split(",")]
            for i, cb in enumerate(self.checkboxes):
                cb.setChecked((i + self.min_val) in values)


class CronToolPage(TabPageInterface):
    """Cron 表达式生成器页面"""
    
    page_id = "cron_tool"
    page_name = "Cron 表达式"
    page_icon = FIF.STOP_WATCH  # 有点像秒表图标
    
    @classmethod
    def create(cls, parent=None) -> QWidget:
        return CronToolWidget(parent)


class CronToolWidget(QWidget):
    """Cron 表达式生成器主界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("cronToolWidget")
        self._setup_ui()
        self._update_style()
        qconfig.themeChanged.connect(self._update_style)
    
    def _update_style(self):
        """更新样式"""
        dark = isDarkTheme()
        if dark:
            self.setStyleSheet("""
                #cronToolWidget { background-color: transparent; }
                #exprCard, #descCard, #nextCard, #presetCard, #cronFieldWidget {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                    border: 1px solid #3d3d3d;
                }
                QLabel, QRadioButton, QCheckBox, QSpinBox, QComboBox {
                    color: #ffffff;
                }
                QRadioButton::indicator, QCheckBox::indicator {
                    background-color: #3d3d3d;
                    border: 1px solid #5d5d5d;
                    border-radius: 2px;
                }
                QSpinBox {
                    background-color: #3d3d3d;
                    border: 1px solid #5d5d5d;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox {
                    background-color: #3d3d3d;
                    border: 1px solid #5d5d5d;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #5d5d5d;
                }
                QLineEdit {
                    background-color: #3d3d3d;
                    border: 1px solid #5d5d5d;
                    border-radius: 4px;
                    padding: 6px;
                    color: #ffffff;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 10px;
                    border-radius: 5px;
                }
                QScrollBar:horizontal {
                    background: transparent;
                    height: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background: rgba(150, 150, 150, 0.5);
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                    background: rgba(150, 150, 150, 0.8);
                }
                QScrollBar::add-line, QScrollBar::sub-line,
                QScrollBar::add-page, QScrollBar::sub-page {
                    background: none;
                }
            """)
        else:
            self.setStyleSheet("""
                #cronToolWidget { background-color: transparent; }
                #exprCard, #descCard, #nextCard, #presetCard, #cronFieldWidget {
                    background-color: #ffffff;
                    border-radius: 8px;
                    border: 1px solid #e0e0e0;
                }
                QLabel, QRadioButton, QCheckBox, QSpinBox, QComboBox {
                    color: #333333;
                }
                QRadioButton::indicator, QCheckBox::indicator {
                    background-color: #f0f0f0;
                    border: 1px solid #d0d0d0;
                    border-radius: 2px;
                }
                QSpinBox {
                    background-color: #f5f5f5;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox {
                    background-color: #f5f5f5;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 4px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #d0d0d0;
                }
                QLineEdit {
                    background-color: #f5f5f5;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    padding: 6px;
                    color: #333333;
                }
                QScrollBar:vertical {
                    background: transparent;
                    width: 10px;
                    border-radius: 5px;
                }
                QScrollBar:horizontal {
                    background: transparent;
                    height: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                    background: rgba(150, 150, 150, 0.5);
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                    background: rgba(150, 150, 150, 0.8);
                }
                QScrollBar::add-line, QScrollBar::sub-line,
                QScrollBar::add-page, QScrollBar::sub-page {
                    background: none;
                }
            """)
    
    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 左侧：字段配置
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # 二级标签页
        self.tab_widget = SegmentedWidget(self)
        left_layout.addWidget(self.tab_widget)
        
        # 堆叠窗口
        from PyQt5.QtWidgets import QStackedWidget
        self.stacked_widget = QStackedWidget(self)
        left_layout.addWidget(self.stacked_widget)
        
        # 创建各字段配置页面
        self.field_widgets = {}
        fields = [
            ("秒", 0, 59),
            ("分钟", 0, 59),
            ("小时", 0, 23),
            ("日", 1, 31),
            ("月", 1, 12),
            ("星期", 1, 7),
            ("年", 1970, 2099),
        ]
        
        for name, min_val, max_val in fields:
            widget = CronFieldWidget(name, min_val, max_val, self)
            self.field_widgets[name] = widget
            self.stacked_widget.addWidget(widget)
            self.tab_widget.addItem(name, name)

        self.tab_widget.setCurrentItem("秒")
        self.tab_widget.currentItemChanged.connect(
            lambda name: self.stacked_widget.setCurrentIndex(
                list(self.field_widgets.keys()).index(name)
            )
        )
        
        main_layout.addWidget(left_widget, 2)
        
        # 右侧：表达式和结果
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # Cron 表达式显示
        expr_card = QWidget(self)
        expr_card.setObjectName("exprCard")
        expr_layout = QVBoxLayout(expr_card)
        expr_layout.setContentsMargins(15, 15, 15, 15)
        
        expr_title = StrongBodyLabel("Cron 表达式", self)
        expr_layout.addWidget(expr_title)
        
        expr_input_layout = QHBoxLayout()
        self.expr_edit = LineEdit(self)
        self.expr_edit.setPlaceholderText("* * * * * *")
        expr_input_layout.addWidget(self.expr_edit)
        
        self.parse_btn = PushButton("解析到UI", self)
        self.parse_btn.clicked.connect(self._parse_to_ui)
        expr_input_layout.addWidget(self.parse_btn)
        
        expr_layout.addLayout(expr_input_layout)
        right_layout.addWidget(expr_card)
        
        # 自然语言描述
        desc_card = QWidget(self)
        desc_card.setObjectName("descCard")
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setContentsMargins(15, 15, 15, 15)
        
        desc_title = StrongBodyLabel("自然语言描述", self)
        desc_layout.addWidget(desc_title)
        
        self.desc_edit = TextEdit(self)
        self.desc_edit.setReadOnly(True)
        self.desc_edit.setMaximumHeight(80)
        desc_layout.addWidget(self.desc_edit)
        
        right_layout.addWidget(desc_card)
        
        # 最近执行时间
        next_card = QWidget(self)
        next_card.setObjectName("nextCard")
        next_layout = QVBoxLayout(next_card)
        next_layout.setContentsMargins(15, 15, 15, 15)
        
        next_title = StrongBodyLabel("最近10次执行时间", self)
        next_layout.addWidget(next_title)
        
        self.next_edit = TextEdit(self)
        self.next_edit.setReadOnly(True)
        next_layout.addWidget(self.next_edit)
        
        right_layout.addWidget(next_card, 1)
        
        # 常用表达式
        preset_card = QWidget(self)
        preset_card.setObjectName("presetCard")
        preset_layout = QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(15, 15, 15, 15)
        
        preset_title = StrongBodyLabel("常用表达式", self)
        preset_layout.addWidget(preset_title)
        
        preset_combo = ComboBox(self)
        preset_combo.addItem("自定义")
        preset_combo.addItem("每分钟", "0 * * * * *")
        preset_combo.addItem("每小时", "0 0 * * * *")
        preset_combo.addItem("每天", "0 0 0 * * *")
        preset_combo.addItem("每周", "0 0 0 * * 1")
        preset_combo.addItem("每月", "0 0 0 1 * *")
        preset_combo.addItem("每年", "0 0 0 1 1 *")
        preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(preset_combo)
        
        right_layout.addWidget(preset_card)
        
        main_layout.addWidget(right_widget, 1)
        
        # 连接信号
        for widget in self.field_widgets.values():
            widget.button_group.buttonClicked.connect(self._update_expression)
            for spin in [widget.spin_period_start, widget.spin_period_end,
                        widget.spin_step_start, widget.spin_step_interval]:
                spin.valueChanged.connect(self._update_expression)
            for cb in widget.checkboxes:
                cb.stateChanged.connect(self._update_expression)
        
        self._update_expression()
    
    def _update_expression(self) -> None:
        """根据UI更新表达式"""
        parts = [
            self.field_widgets["秒"].get_expression(),
            self.field_widgets["分钟"].get_expression(),
            self.field_widgets["小时"].get_expression(),
            self.field_widgets["日"].get_expression(),
            self.field_widgets["月"].get_expression(),
            self.field_widgets["星期"].get_expression(),
        ]
        
        year_expr = self.field_widgets["年"].get_expression()
        if year_expr != "*":
            parts.append(year_expr)
        
        expr = " ".join(parts)
        self.expr_edit.setText(expr)
        self._update_description(expr)
    
    def _update_description(self, expr: str) -> None:
        """更新自然语言描述"""
        try:
            desc = self._parse_cron_to_desc(expr)
            self.desc_edit.setText(desc)
            
            next_times = self._get_next_executions(expr)
            self.next_edit.setText("\n".join(next_times))
        except Exception as e:
            self.desc_edit.setText(f"解析错误: {str(e)}")
            self.next_edit.clear()
    
    def _parse_cron_to_desc(self, expr: str) -> str:
        """将 Cron 表达式转换为自然语言描述"""
        parts = expr.split()
        if len(parts) < 6:
            return "表达式格式错误"
        
        desc_parts = []
        
        # 秒
        if parts[0] != "*":
            desc_parts.append(f"第{parts[0]}秒")
        
        # 分钟
        if parts[1] == "*":
            desc_parts.append("每分钟")
        elif "/" in parts[1]:
            desc_parts.append(f"每{parts[1].split('/')[1]}分钟")
        else:
            desc_parts.append(f"第{parts[1]}分钟")
        
        # 小时
        if parts[2] == "*":
            desc_parts.append("每小时")
        elif "/" in parts[2]:
            desc_parts.append(f"每{parts[2].split('/')[1]}小时")
        else:
            desc_parts.append(f"{parts[2]}点")
        
        # 日
        if parts[3] != "*":
            desc_parts.append(f"{parts[3]}日")
        
        # 月
        if parts[4] != "*":
            desc_parts.append(f"{parts[4]}月")
        
        # 星期
        if parts[5] != "*" and parts[5] != "?":
            weekdays = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            try:
                wd = int(parts[5])
                desc_parts.append(weekdays[wd] if 1 <= wd <= 7 else f"星期{parts[5]}")
            except:
                desc_parts.append(f"星期{parts[5]}")
        
        return "，".join(desc_parts) if desc_parts else "每分钟执行一次"
    
    def _get_next_executions(self, expr: str) -> list:
        """获取接下来10次执行时间"""
        try:
            from datetime import datetime, timedelta
            
            # 简化版：模拟计算（实际应使用 croniter 库）
            now = datetime.now()
            times = []
            
            parts = expr.split()
            if len(parts) < 6:
                return ["表达式格式错误"]
            
            # 这里简化处理，仅作为示例
            for i in range(10):
                next_time = now + timedelta(minutes=i+1)
                times.append(next_time.strftime("%Y-%m-%d %H:%M:%S"))
            
            return times
        except Exception as e:
            return [f"计算错误: {str(e)}"]
    
    def _parse_to_ui(self) -> None:
        """从表达式解析到UI"""
        expr = self.expr_edit.text().strip()
        if not expr:
            return
        
        parts = expr.split()
        if len(parts) < 6:
            InfoBar.warning(
                title="格式错误",
                content="Cron 表达式格式不正确",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        field_names = ["秒", "分钟", "小时", "日", "月", "星期"]
        for i, name in enumerate(field_names):
            if i < len(parts):
                self.field_widgets[name].set_expression(parts[i])
        
        if len(parts) >= 7:
            self.field_widgets["年"].set_expression(parts[6])
        
        InfoBar.success(
            title="解析成功",
            content="已解析到UI",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _on_preset_changed(self, index: int) -> None:
        """选择预设表达式"""
        combo = self.sender()
        if not combo:
            return
        
        data = combo.itemData(index)
        if data:
            self.expr_edit.setText(data)
            self._parse_to_ui()
