"""环境变量插件"""
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import winreg
except ImportError:  # pragma: no cover
    winreg = None

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget
)
from qfluentwidgets import (
    LineEdit, FluentIcon as FIF, isDarkTheme, qconfig,
    TransparentToolButton
)
from core import PluginInterface
from ui import CustomFluentIcon


SYSTEM_ENV_REG_PATH = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
USER_ENV_REG_PATH = r"Environment"
MAX_SEARCH_RESULTS = 20
SECRET_NAME_PARTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PWD", "CREDENTIAL")


@dataclass(frozen=True)
class EnvVarEntry:
    name: str
    value: str
    scope: str
    reg_type: Optional[int] = None
    type_name: str = ""
    expanded_value: Optional[str] = None


def registry_type_name(reg_type: Optional[int]) -> str:
    if winreg is None or reg_type is None:
        return ""

    type_names = {
        winreg.REG_SZ: "REG_SZ",
        winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
        winreg.REG_MULTI_SZ: "REG_MULTI_SZ",
        winreg.REG_DWORD: "REG_DWORD",
        winreg.REG_QWORD: "REG_QWORD",
        winreg.REG_BINARY: "REG_BINARY",
    }
    return type_names.get(reg_type, f"REG_{reg_type}")


def registry_value_to_text(value: Any, reg_type: Optional[int]) -> Tuple[str, Optional[str]]:
    if value is None:
        return "", None

    if winreg is not None and reg_type == winreg.REG_MULTI_SZ:
        if isinstance(value, (list, tuple)):
            return "; ".join(str(item) for item in value), None
        return str(value), None

    if winreg is not None and reg_type == winreg.REG_BINARY:
        try:
            return bytes(value).hex(" "), None
        except (TypeError, ValueError):
            return str(value), None

    text = str(value)
    if winreg is not None and reg_type == winreg.REG_EXPAND_SZ:
        expanded_value = os.path.expandvars(text)
        return text, expanded_value if expanded_value != text else None

    return text, None


def get_registry_env_vars(root, sub_key: str, scope: str) -> List[EnvVarEntry]:
    if winreg is None:
        return []

    access_options = [winreg.KEY_READ]
    if hasattr(winreg, "KEY_WOW64_64KEY"):
        access_options.insert(0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)

    for access in access_options:
        entries = []
        try:
            with winreg.OpenKey(root, sub_key, 0, access) as key:
                index = 0
                while True:
                    try:
                        name, value, reg_type = winreg.EnumValue(key, index)
                    except OSError:
                        break

                    text, expanded_value = registry_value_to_text(value, reg_type)
                    entries.append(EnvVarEntry(
                        name=str(name),
                        value=text,
                        scope=scope,
                        reg_type=reg_type,
                        type_name=registry_type_name(reg_type),
                        expanded_value=expanded_value,
                    ))
                    index += 1
            return entries
        except OSError:
            continue

    return []


def _read_registry_index(root, sub_key: str) -> Dict[str, EnvVarEntry]:
    """读取注册表环境变量，返回 {name: entry} 字典"""
    entries = get_registry_env_vars(root, sub_key, "")
    return {e.name: e for e in entries}


def _build_env_snapshot() -> Dict[str, str]:
    """当前进程实际生效的所有环境变量"""
    return dict(os.environ)


def get_system_env_vars() -> List[EnvVarEntry]:
    """系统环境变量：注册表 + 未归类的运行时变量"""
    snapshot = _build_env_snapshot()

    if winreg is None:
        return dict_to_entries(snapshot, "system", "")

    system_reg = _read_registry_index(winreg.HKEY_LOCAL_MACHINE, SYSTEM_ENV_REG_PATH)
    user_reg_names = set(_read_registry_index(winreg.HKEY_CURRENT_USER, USER_ENV_REG_PATH))

    results = {}
    for name, entry in system_reg.items():
        results[name] = EnvVarEntry(
            name=name, value=snapshot.get(name, entry.value), scope="system",
            reg_type=entry.reg_type, type_name=entry.type_name,
            expanded_value=entry.expanded_value,
        )

    for name, value in snapshot.items():
        if name not in results and name not in user_reg_names:
            results[name] = EnvVarEntry(name=name, value=value, scope="system")

    return sorted(results.values(), key=lambda e: normalize_search_text(e.name))


def get_user_env_vars() -> List[EnvVarEntry]:
    """用户环境变量：注册表（不重复显示 system 已有的）"""
    snapshot = _build_env_snapshot()

    if winreg is None:
        return []

    user_reg = _read_registry_index(winreg.HKEY_CURRENT_USER, USER_ENV_REG_PATH)
    system_reg_names = set(_read_registry_index(winreg.HKEY_LOCAL_MACHINE, SYSTEM_ENV_REG_PATH))

    results = {}
    for name, entry in user_reg.items():
        if name not in system_reg_names:
            results[name] = EnvVarEntry(
                name=name, value=snapshot.get(name, entry.value), scope="user",
                reg_type=entry.reg_type, type_name=entry.type_name,
                expanded_value=entry.expanded_value,
            )

    return sorted(results.values(), key=lambda e: normalize_search_text(e.name))


def dict_to_entries(values: Dict[str, str], scope: str, type_name: str = "") -> List[EnvVarEntry]:
    return [
        EnvVarEntry(name=str(name), value=str(value), scope=scope, type_name=type_name)
        for name, value in values.items()
    ]


def normalize_search_text(text: Any) -> str:
    return str(text or "").casefold()


def tokenize_query(query: str) -> List[str]:
    return [part for part in normalize_search_text(query).split() if part]


def _path_segments(value: str) -> List[str]:
    return [segment.strip() for segment in str(value or "").split(os.pathsep) if segment.strip()]


def _entry_search_texts(entry: EnvVarEntry) -> List[str]:
    texts = [entry.name, entry.value, entry.scope, entry.type_name]
    if entry.expanded_value:
        texts.append(entry.expanded_value)
    texts.extend(_path_segments(entry.value))
    if entry.expanded_value:
        texts.extend(_path_segments(entry.expanded_value))
    return texts


def _token_score(token: str, entry: EnvVarEntry) -> float:
    name = normalize_search_text(entry.name)
    value = normalize_search_text(entry.value)
    expanded_value = normalize_search_text(entry.expanded_value)
    scope = normalize_search_text(entry.scope)
    type_name = normalize_search_text(entry.type_name)

    if token == name:
        return 100
    if name.startswith(token):
        return 90
    if token in name:
        return 80

    best_score = 0.0
    for segment in _path_segments(entry.value) + _path_segments(entry.expanded_value or ""):
        normalized_segment = normalize_search_text(segment)
        basename = normalize_search_text(os.path.basename(segment.rstrip("\\/")))
        if token == basename or token == normalized_segment:
            best_score = max(best_score, 75)
        elif basename.startswith(token):
            best_score = max(best_score, 70)
        elif token in basename or token in normalized_segment:
            best_score = max(best_score, 65)

    if token in value:
        best_score = max(best_score, 50)
    if expanded_value and token in expanded_value:
        best_score = max(best_score, 45)
    if token in scope or token in type_name:
        best_score = max(best_score, 20)

    return best_score


def score_env_match(query: str, entry: EnvVarEntry) -> float:
    tokens = tokenize_query(query)
    if not tokens:
        return 1

    scores = [_token_score(token, entry) for token in tokens]
    if any(score <= 0 for score in scores):
        return 0
    return sum(scores) / len(scores) + min(len(tokens) - 1, 3)


def filter_and_sort_env_entries(entries: List[EnvVarEntry], query: str) -> List[EnvVarEntry]:
    if not query or not query.strip():
        return sorted(entries, key=lambda entry: normalize_search_text(entry.name))

    scored_entries = []
    for entry in entries:
        score = score_env_match(query, entry)
        if score > 0:
            scored_entries.append((score, entry))

    scored_entries.sort(key=lambda item: (-item[0], normalize_search_text(item[1].name)))
    return [entry for _, entry in scored_entries]


def truncate_value(value: str, max_length: int = 120) -> str:
    if len(value) <= max_length:
        return value
    return value[:max_length - 3] + "..."


def is_secret_entry(entry: EnvVarEntry) -> bool:
    name = entry.name.upper()
    return any(part in name for part in SECRET_NAME_PARTS)


def scope_label(scope: str) -> str:
    return {
        "system": "系统",
        "user": "用户",
        "python": "Python",
    }.get(scope, scope)


class EnvVarTableWidget(QWidget):
    """环境变量表格组件"""

    def __init__(self, entries: List[EnvVarEntry], parent=None):
        super().__init__(parent)
        self.entries = entries
        self.visible_entries = []
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索环境变量...")
        self.search_input.textChanged.connect(self._reload_table)
        layout.addWidget(self.search_input)

        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Key", "Value"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont("Consolas", 10))

        layout.addWidget(self.table)
        self._reload_table()

    def _reload_table(self):
        self.visible_entries = filter_and_sort_env_entries(self.entries, self.search_input.text())
        self.table.setRowCount(len(self.visible_entries))

        for row, entry in enumerate(self.visible_entries):
            key_item = QTableWidgetItem(entry.name)
            value_item = QTableWidgetItem(entry.value)

            key_item.setFont(QFont("Consolas", 10))
            value_item.setFont(QFont("Consolas", 10))
            tooltip = self._entry_tooltip(entry)
            key_item.setToolTip(tooltip)
            value_item.setToolTip(tooltip)
            key_item.setData(Qt.UserRole, entry)
            value_item.setData(Qt.UserRole, entry)

            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)

        self._apply_style()

    def _entry_tooltip(self, entry: EnvVarEntry) -> str:
        lines = [f"来源: {scope_label(entry.scope)}"]
        if entry.type_name:
            lines.append(f"类型: {entry.type_name}")
        if entry.expanded_value:
            lines.append(f"展开后: {entry.expanded_value}")
        return "\n".join(lines)

    def _apply_style(self):
        if isDarkTheme():
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: #2d2d2d;
                    alternate-background-color: #3a3a3a;
                    gridline-color: #4d4d4d;
                    border: 1px solid #4d4d4d;
                    selection-background-color: #0078d4;
                    selection-color: white;
                    color: #ffffff;
                }
                QTableWidget::item {
                    padding: 4px;
                    border-right: 1px solid #4d4d4d;
                    border-bottom: 1px solid #4d4d4d;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #3d3d3d;
                    padding: 6px;
                    border: 1px solid #4d4d4d;
                    font-weight: bold;
                    color: #ffffff;
                }
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical {
                    background-color: #4d4d4d;
                    border-radius: 5px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5d5d5d;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
        else:
            self.table.setStyleSheet("""
                QTableWidget {
                    background-color: white;
                    alternate-background-color: #f9f9f9;
                    gridline-color: #e0e0e0;
                    border: 1px solid #e0e0e0;
                    selection-background-color: #0078d4;
                    selection-color: white;
                    color: #333333;
                }
                QTableWidget::item {
                    padding: 4px;
                    border-right: 1px solid #e0e0e0;
                    border-bottom: 1px solid #e0e0e0;
                    color: #333333;
                }
                QHeaderView::section {
                    background-color: #f0f0f0;
                    padding: 6px;
                    border: 1px solid #e0e0e0;
                    font-weight: bold;
                    color: #333333;
                }
                QScrollBar:vertical {
                    background-color: #f0f0f0;
                    width: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical {
                    background-color: #c0c0c0;
                    border-radius: 5px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #a0a0a0;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)

    def set_entries(self, entries: List[EnvVarEntry]):
        self.entries = entries
        self._reload_table()

    def set_env_vars(self, env_vars: Dict[str, str]):
        self.set_entries(dict_to_entries(env_vars, "process"))

    def focus_entry(self, name: str):
        self.search_input.setText(name)
        normalized_name = normalize_search_text(name)
        for row, entry in enumerate(self.visible_entries):
            if normalize_search_text(entry.name) == normalized_name:
                self.table.selectRow(row)
                self.table.scrollToItem(self.table.item(row, 0), QAbstractItemView.PositionAtCenter)
                break


class EnvVarWidget(QWidget):
    """环境变量主组件"""

    PLUGIN_ID = "environment"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core

        self._setup_ui()
        self._apply_style()
        qconfig.themeChangedFinished.connect(self._apply_style)

    def _setup_ui(self):
        self.setObjectName("envVarWidget")

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabPosition(QTabWidget.North)

        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.clicked.connect(self._refresh_all)
        self.tab_widget.setCornerWidget(self.refresh_btn, Qt.TopRightCorner)

        self.system_tab = EnvVarTableWidget(get_system_env_vars(), self)
        self.tab_widget.addTab(self.system_tab, "📜 系统环境变量")

        self.user_tab = EnvVarTableWidget(get_user_env_vars(), self)
        self.tab_widget.addTab(self.user_tab, "👤 用户环境变量")

        self.python_tab = EnvVarTableWidget(self._get_python_properties(), self)
        self.tab_widget.addTab(self.python_tab, "🖖 Python Properties")

        main_layout.addWidget(self.tab_widget)

    def _get_python_properties(self) -> List[EnvVarEntry]:
        props = {
            "Python 版本": sys.version,
            "Python 路径": sys.executable,
            "Python 前缀": sys.prefix,
            "Python 基础前缀": sys.base_prefix,
            "平台": sys.platform,
            "字节顺序": sys.byteorder,
            "最大整数": str(sys.maxsize),
            "文件系统编码": sys.getfilesystemencoding(),
            "默认编码": sys.getdefaultencoding(),
            "标准输入编码": getattr(sys.stdin, 'encoding', 'unknown'),
            "标准输出编码": getattr(sys.stdout, 'encoding', 'unknown'),
            "标准错误编码": getattr(sys.stderr, 'encoding', 'unknown'),
            "递归限制": str(sys.getrecursionlimit()),
            "最大 Unicode": str(sys.maxunicode),
        }

        for i, path in enumerate(sys.path):
            props[f"Python 路径 [{i}]"] = path

        return dict_to_entries(props, "python", "Python")

    def _refresh_all(self):
        self.system_tab.set_entries(get_system_env_vars())
        self.user_tab.set_entries(get_user_env_vars())
        self.python_tab.set_entries(self._get_python_properties())

    def focus_env_var(self, scope: str, name: str) -> None:
        tabs = {
            "system": (0, self.system_tab),
            "user": (1, self.user_tab),
            "python": (2, self.python_tab),
        }
        tab_info = tabs.get(scope)
        if not tab_info:
            return
        index, table = tab_info
        self.tab_widget.setCurrentIndex(index)
        table.focus_entry(name)

    def _apply_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#envVarWidget {
                    background-color: #1e1e1e;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:hover {
                    background-color: #3d3d3d;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    color: #009faa;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#envVarWidget {
                    background-color: #f5f5f5;
                }
                QTabWidget::pane {
                    border: none;
                    background-color: #f5f5f5;
                }
                QTabBar::tab {
                    background-color: #e0e0e0;
                    color: #333333;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:hover {
                    background-color: #d0d0d0;
                }
                QTabBar::tab:selected {
                    background-color: #f5f5f5;
                    color: #009faa;
                }
            """)

        self.system_tab._apply_style()
        self.user_tab._apply_style()
        self.python_tab._apply_style()


class Plugin(PluginInterface):
    """环境变量插件"""

    PLUGIN_ID = "environment"
    PLUGIN_NAME = "环境变量"
    PLUGIN_ICON = CustomFluentIcon.ENV
    PLUGIN_PRIORITY = 18

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return EnvVarWidget(self.core, parent)

    def load_data(self) -> None:
        if self._widget:
            pass

    def supports_search(self) -> bool:
        return True

    def search(self, query: str):
        if not query or not query.strip():
            return []

        from core import SearchResult

        results = []
        entries = get_system_env_vars() + get_user_env_vars()
        scored_entries = []
        for entry in entries:
            score = score_env_match(query, entry)
            if score > 0:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda item: (-item[0], normalize_search_text(item[1].name)))
        for score, entry in scored_entries[:MAX_SEARCH_RESULTS]:
            value = "<hidden>" if is_secret_entry(entry) else truncate_value(entry.value)
            label = scope_label(entry.scope)
            results.append(SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=f"{entry.name} ({label})",
                description=f"{label}环境变量: {value}",
                icon=self.PLUGIN_ICON,
                relevance=min(score / 100, 1.0),
                action=lambda scope=entry.scope, name=entry.name: self._focus_env_var_from_search(scope, name),
                metadata={
                    "scope": entry.scope,
                    "name": entry.name,
                    "type_name": entry.type_name,
                    "value": entry.value,
                },
            ))
        return results

    def _focus_env_var_from_search(self, scope: str, name: str) -> None:
        if self._widget and hasattr(self._widget, "focus_env_var"):
            self._widget.focus_env_var(scope, name)
