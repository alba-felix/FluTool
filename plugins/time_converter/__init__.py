"""
时间转换插件
提供时间戳与日期时间的相互转换功能
"""
import time
from datetime import datetime, timezone
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication, QFrame
from qfluentwidgets import (
    StrongBodyLabel, BodyLabel, CaptionLabel,
    LineEdit, PushButton, ComboBox,
    FluentIcon as FIF, InfoBar, InfoBarPosition,
    CardWidget, SubtitleLabel, IconWidget
)
from core.plugin_interface import PluginInterface


class TimeConverterWidget(QWidget):
    """时间转换组件"""
    
    PLUGIN_ID = "time_converter"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._setup_ui()
        self._init_timer()
    
    def _setup_ui(self):
        """构建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # === 当前时间显示卡片 ===
        current_card = CardWidget(self)
        current_layout = QVBoxLayout(current_card)
        current_layout.setSpacing(12)
        current_layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        title_row = QHBoxLayout()
        title_icon = IconWidget(FIF.DATE_TIME, self)
        title_icon.setFixedSize(20, 20)
        title_label = SubtitleLabel("当前时间", self)
        title_row.addWidget(title_icon)
        title_row.addWidget(title_label)
        title_row.addStretch()
        current_layout.addLayout(title_row)
        
        # 当前时间行
        time_row = QHBoxLayout()
        time_row.setSpacing(12)
        
        time_label = BodyLabel("当前时间:")
        time_label.setFixedWidth(80)
        
        self.current_time_edit = LineEdit(self)
        self.current_time_edit.setReadOnly(True)
        
        self.copy_time_btn = PushButton("复制", self)
        self.copy_time_btn.setFixedWidth(70)
        self.copy_time_btn.setIcon(FIF.COPY)
        self.copy_time_btn.clicked.connect(lambda: self._copy_text(self.current_time_edit.text()))
        
        time_row.addWidget(time_label)
        time_row.addWidget(self.current_time_edit)
        time_row.addWidget(self.copy_time_btn)
        current_layout.addLayout(time_row)
        
        # Unix时间戳行
        timestamp_row = QHBoxLayout()
        timestamp_row.setSpacing(12)
        
        timestamp_label = BodyLabel("Unix时间戳:")
        timestamp_label.setFixedWidth(80)
        
        self.current_timestamp_edit = LineEdit(self)
        self.current_timestamp_edit.setReadOnly(True)
        
        self.copy_timestamp_btn = PushButton("复制", self)
        self.copy_timestamp_btn.setFixedWidth(70)
        self.copy_timestamp_btn.setIcon(FIF.COPY)
        self.copy_timestamp_btn.clicked.connect(lambda: self._copy_text(self.current_timestamp_edit.text()))
        
        timestamp_row.addWidget(timestamp_label)
        timestamp_row.addWidget(self.current_timestamp_edit)
        timestamp_row.addWidget(self.copy_timestamp_btn)
        current_layout.addLayout(timestamp_row)
        
        main_layout.addWidget(current_card)
        
        # === 时间转换卡片 ===
        convert_card = CardWidget(self)
        convert_layout = QVBoxLayout(convert_card)
        convert_layout.setSpacing(16)
        convert_layout.setContentsMargins(16, 16, 16, 16)
        
        # 标题
        convert_title_row = QHBoxLayout()
        convert_title_icon = IconWidget(FIF.STOP_WATCH, self)
        convert_title_icon.setFixedSize(20, 20)
        convert_title_label = SubtitleLabel("时间转换", self)
        convert_title_row.addWidget(convert_title_icon)
        convert_title_row.addWidget(convert_title_label)
        convert_title_row.addStretch()
        convert_layout.addLayout(convert_title_row)
        
        # 时间戳输入区
        timestamp_section = QVBoxLayout()
        timestamp_section.setSpacing(8)
        
        timestamp_header = QHBoxLayout()
        timestamp_icon = IconWidget(FIF.UNIT, self)
        timestamp_icon.setFixedSize(16, 16)
        timestamp_title = BodyLabel("时间戳 (Unix Timestamp)")
        timestamp_title.setStyleSheet("font-weight: bold;")
        timestamp_header.addWidget(timestamp_icon)
        timestamp_header.addWidget(timestamp_title)
        timestamp_header.addStretch()
        timestamp_section.addLayout(timestamp_header)
        
        timestamp_input_row = QHBoxLayout()
        timestamp_input_row.setSpacing(10)
        
        self.timestamp_edit = LineEdit(self)
        self.timestamp_edit.setPlaceholderText("输入时间戳...")
        self.timestamp_edit.setClearButtonEnabled(True)
        
        copy_btn1 = PushButton("复制", self)
        copy_btn1.setFixedWidth(70)
        copy_btn1.setIcon(FIF.COPY)
        copy_btn1.clicked.connect(lambda: self._copy_text(self.timestamp_edit.text()))
        
        timestamp_input_row.addWidget(self.timestamp_edit)
        timestamp_input_row.addWidget(copy_btn1)
        timestamp_section.addLayout(timestamp_input_row)
        
        convert_layout.addLayout(timestamp_section)
        
        # 控制区：单位 + 按钮
        control_row = QHBoxLayout()
        control_row.setSpacing(12)
        
        # 单位选择
        unit_container = QHBoxLayout()
        unit_container.setSpacing(8)
        unit_label = BodyLabel("单位:")
        self.unit_combo = ComboBox(self)
        self.unit_combo.addItems(["秒(s)", "毫秒(ms)", "微秒(us)", "纳秒(ns)"])
        self.unit_combo.setCurrentIndex(0)
        unit_container.addWidget(unit_label)
        unit_container.addWidget(self.unit_combo)
        unit_container.addStretch()
        
        control_row.addLayout(unit_container)
        control_row.addStretch()
        
        # 转换按钮
        self.down_btn = PushButton("⬇ 时间戳 → 时间", self)
        self.down_btn.setIcon(FIF.DOWN)
        self.down_btn.clicked.connect(self._convert_timestamp_to_datetime)
        
        self.up_btn = PushButton("⬆ 时间 → 时间戳", self)
        self.up_btn.setIcon(FIF.UP)
        self.up_btn.clicked.connect(self._convert_datetime_to_timestamp)
        
        control_row.addWidget(self.down_btn)
        control_row.addWidget(self.up_btn)
        
        convert_layout.addLayout(control_row)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFixedHeight(1)
        convert_layout.addWidget(separator)
        
        # 本地时间输入区
        local_section = QVBoxLayout()
        local_section.setSpacing(8)
        
        local_header = QHBoxLayout()
        local_icon = IconWidget(FIF.CALENDAR, self)
        local_icon.setFixedSize(16, 16)
        local_title = BodyLabel("本地时间 (GMT +8)")
        local_title.setStyleSheet("font-weight: bold;")
        local_header.addWidget(local_icon)
        local_header.addWidget(local_title)
        local_header.addStretch()
        local_section.addLayout(local_header)
        
        local_input_row = QHBoxLayout()
        local_input_row.setSpacing(10)
        
        self.local_time_edit = LineEdit(self)
        self.local_time_edit.setPlaceholderText("输入本地时间...")
        self.local_time_edit.setClearButtonEnabled(True)
        
        copy_btn2 = PushButton("复制", self)
        copy_btn2.setFixedWidth(70)
        copy_btn2.setIcon(FIF.COPY)
        copy_btn2.clicked.connect(lambda: self._copy_text(self.local_time_edit.text()))
        
        local_input_row.addWidget(self.local_time_edit)
        local_input_row.addWidget(copy_btn2)
        local_section.addLayout(local_input_row)
        
        convert_layout.addLayout(local_section)
        
        # 时间格式
        format_row = QHBoxLayout()
        format_row.setSpacing(10)
        
        format_icon = IconWidget(FIF.EDIT, self)
        format_icon.setFixedSize(16, 16)
        format_label = BodyLabel("格式:")
        
        self.format_edit = LineEdit(self)
        self.format_edit.setText("yyyy-MM-dd HH:mm:ss.SSS")
        self.format_edit.setPlaceholderText("时间格式...")
        self.format_edit.setClearButtonEnabled(True)
        
        format_row.addWidget(format_icon)
        format_row.addWidget(format_label)
        format_row.addWidget(self.format_edit)
        
        convert_layout.addLayout(format_row)
        
        main_layout.addWidget(convert_card)
        
        # 底部提示
        main_layout.addStretch(1)
        
        tip_row = QHBoxLayout()
        tip_icon = IconWidget(FIF.INFO, self)
        tip_icon.setFixedSize(14, 14)
        tip_label = CaptionLabel("支持秒、毫秒、微秒、纳秒单位的时间戳转换", self)
        tip_row.addStretch()
        tip_row.addWidget(tip_icon)
        tip_row.addWidget(tip_label)
        tip_row.addStretch()
        main_layout.addLayout(tip_row)
    
    def _init_timer(self):
        """初始化定时器，每秒更新当前时间"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_current_time)
        self.timer.start(1000)
        self._update_current_time()
    
    def _update_current_time(self):
        """更新当前时间和时间戳"""
        now = datetime.now()
        current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.current_time_edit.setText(current_time_str)
        
        timestamp = int(time.time())
        self.current_timestamp_edit.setText(str(timestamp))
    
    def _convert_timestamp_to_datetime(self):
        """将时间戳转换为本地时间"""
        try:
            timestamp_str = self.timestamp_edit.text().strip()
            if not timestamp_str:
                return
            
            unit = self.unit_combo.currentText()
            timestamp = float(timestamp_str)
            
            # 根据单位转换为秒
            if unit == "毫秒(ms)":
                timestamp /= 1000
            elif unit == "微秒(us)":
                timestamp /= 1000000
            elif unit == "纳秒(ns)":
                timestamp /= 1000000000
            
            # 转换为本地时间
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone()
            
            # 获取并转换时间格式
            format_str = self._convert_format(self.format_edit.text().strip() or "%Y-%m-%d %H:%M:%S")
            
            local_time_str = dt.strftime(format_str)
            self.local_time_edit.setText(local_time_str)
            
        except Exception as e:
            InfoBar.error(
                title="转换错误",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _convert_datetime_to_timestamp(self):
        """将本地时间转换为时间戳"""
        try:
            local_time_str = self.local_time_edit.text().strip()
            if not local_time_str:
                return
            
            # 获取并转换时间格式
            format_str = self._convert_format(self.format_edit.text().strip() or "%Y-%m-%d %H:%M:%S")
            
            # 解析时间
            dt = datetime.strptime(local_time_str, format_str)
            
            # 转换为时间戳
            timestamp = dt.timestamp()
            
            # 根据单位转换
            unit = self.unit_combo.currentText()
            if unit == "毫秒(ms)":
                timestamp *= 1000
            elif unit == "微秒(us)":
                timestamp *= 1000000
            elif unit == "纳秒(ns)":
                timestamp *= 1000000000
            
            self.timestamp_edit.setText(str(int(timestamp)))
            
        except Exception as e:
            InfoBar.error(
                title="转换错误",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _convert_format(self, format_str: str) -> str:
        """将Java风格的时间格式转换为Python风格"""
        format_str = format_str.replace("yyyy", "%Y")
        format_str = format_str.replace("MM", "%m")
        format_str = format_str.replace("dd", "%d")
        format_str = format_str.replace("HH", "%H")
        format_str = format_str.replace("mm", "%M")
        format_str = format_str.replace("ss", "%S")
        format_str = format_str.replace("SSS", "%f")[:-3]  # 毫秒只保留3位
        return format_str
    
    def _copy_text(self, text: str):
        """复制文本到剪贴板"""
        if not text:
            return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        InfoBar.success(
            title="复制成功",
            content=f"已复制: {text}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=1500,
            parent=self
        )


class Plugin(PluginInterface):
    """时间转换插件"""
    
    PLUGIN_ID = "time_converter"
    PLUGIN_NAME = "时间转换"
    PLUGIN_ICON = FIF.DATE_TIME
    PLUGIN_PRIORITY = 4
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return TimeConverterWidget(self.core, parent)
    
    def load_data(self) -> None:
        """加载数据"""
        pass
