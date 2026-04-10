"""快捷替换面板"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QGridLayout
from qfluentwidgets import CheckBox, PushButton, FluentIcon as FIF, isDarkTheme
from ui import CustomFluentIcon as CFIF


class QuickReplacePanel(QWidget):
    """快捷替换面板"""

    replace_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("quickReplacePanel")
        self._setup_ui()
        self._apply_style()

    def _apply_style(self):
        """应用样式"""
        dark = isDarkTheme()
        if dark:
            bg_color = "#2d2d2d"
            border_color = "#3d3d3d"
        else:
            bg_color = "#f5f5f5"
            border_color = "#e0e0e0"
        
        self.setStyleSheet(f"""
            QuickReplacePanel {{
                background-color: {bg_color};
                border-left: 1px solid {border_color};
            }}
            CheckBox {{
                spacing: 8px;
            }}
        """)

    def _setup_ui(self):
        """设置UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)

        scroll_layout.addWidget(self._create_section("空白处理", [
            ("trim_blank", "去除空格"),
            ("trim_blank_row", "去除空白行"),
            ("clear_tab", "去除Tab"),
        ]))

        scroll_layout.addWidget(self._create_section("数字转换", [
            ("scientific_to_normal", "科学计数法→普通数字"),
            ("normal_to_scientific", "普通数字→科学计数法"),
            ("to_thousandth", "数字转千分位"),
            ("to_normal_num", "千分位转普通数字"),
        ]))

        scroll_layout.addWidget(self._create_section("命名转换", [
            ("underline_to_hump", "下划线→驼峰"),
            ("hump_to_underline", "驼峰→下划线"),
            ("upper_to_lower", "大写→小写"),
            ("lower_to_upper", "小写→大写"),
        ]))

        scroll_layout.addWidget(self._create_section("分隔符转换", [
            ("comma_to_enter", "逗号→换行"),
            ("comma_single_quotes_to_enter", "','→换行(去引号)"),
            ("comma_double_quotes_to_enter", "\",\"→换行(去引号)"),
            ("tab_to_enter", "Tab→换行"),
        ]))

        scroll_layout.addWidget(self._create_section("行操作", [
            ("deduplication_by_line", "行去重"),
            ("deduplication_by_line_cnt", "行去重并统计次数"),
            ("reverse_by_row", "行反转"),
            ("sort_a_to_z", "行排序(A-Z)"),
            ("sort_z_to_a", "行排序(Z-A)"),
            ("sort_by_pinyin", "按拼音排序"),
        ]))

        scroll_layout.addWidget(self._create_section("输出格式", [
            ("clear_enter", "去除换行"),
            ("enter_to_comma", "换行→逗号"),
            ("enter_to_comma_single_quotes", "换行→','"),
            ("enter_to_comma_double_quotes", "换行→\"\",\""),
        ]))

        scroll_layout.addWidget(self._create_section("转义处理", [
            ("escape", "转义"),
            ("unescape", "反转义"),
        ]))

        scroll_layout.addStretch(1)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self._execute_btn = PushButton("执行替换", self, FIF.PLAY)
        self._execute_btn.clicked.connect(self.replace_triggered.emit)
        btn_layout.addWidget(self._execute_btn)
        
        main_layout.addLayout(btn_layout)

        self._checkboxes = self._find_all_checkboxes()

    def _create_section(self, title: str, items: list) -> QWidget:
        """创建分组"""
        section = QWidget()
        section.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(section)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        for key, text in items:
            checkbox = CheckBox(text)
            checkbox.setObjectName(f"cb_{key}")
            layout.addWidget(checkbox)

        return section

    def _find_all_checkboxes(self) -> dict:
        """查找所有复选框"""
        checkboxes = {}
        for checkbox in self.findChildren(CheckBox):
            name = checkbox.objectName()
            if name.startswith("cb_"):
                key = name[3:]
                checkboxes[key] = checkbox
        return checkboxes

    def get_options(self) -> dict:
        """获取所有选项状态"""
        return {key: cb.isChecked() for key, cb in self._checkboxes.items()}

    def reset_options(self):
        """重置所有选项"""
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(False)
