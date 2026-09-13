"""硬件信息工具 - WMI 只读查询、后台加载器与信息页基类

通过 win32com 访问 WMI（root\\cimv2）做只读查询，所有耗时查询在独立
QThread 中执行，避免阻塞主线程 UI。
"""

import pythoncom
import win32com.client
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
)
from qfluentwidgets import (
    FluentIcon as FIF, PushButton, BodyLabel, StrongBodyLabel,
    CardWidget, setCustomStyleSheet, isDarkTheme, qconfig,
)


# ---------------------------------------------------------------------------
# WMI 只读查询
# ---------------------------------------------------------------------------

def wmi_connect() -> Any:
    """建立只读 WMI 连接（必须在调用线程内执行，需先 CoInitialize）"""
    return win32com.client.GetObject(
        "winmgmts:{impersonationLevel=impersonate}!//./root/cimv2"
    )


def wmi_query(wmi: Any, wql: str) -> List[Dict[str, Any]]:
    """执行 WQL 只读查询，返回字典列表。

    数组型属性会被拼接成字符串；查询失败返回空列表。
    """
    rows: List[Dict[str, Any]] = []
    try:
        for obj in wmi.ExecQuery(wql):
            row: Dict[str, Any] = {}
            for prop in obj.Properties_:
                val = prop.Value
                if isinstance(val, (list, tuple)):
                    val = ", ".join(str(v) for v in val) if val else ""
                row[prop.Name] = val
            rows.append(row)
    except Exception:
        return []
    return rows


# ---------------------------------------------------------------------------
# 后台加载器
# ---------------------------------------------------------------------------

class HardwareLoader(QThread):
    """后台加载硬件信息，完成后通过 dataReady 信号回传结果字典。

    task 接收已连接的 wmi 对象，返回 {'groups': [...]} 或 {'_error': '...'}。
    """

    dataReady = pyqtSignal(dict)

    def __init__(self, task: Callable[[Any], dict], parent: QWidget = None):
        super().__init__(parent)
        self._task = task

    def run(self) -> None:
        pythoncom.CoInitialize()
        data: dict = {}
        try:
            wmi = wmi_connect()
            data = self._task(wmi) or {}
        except Exception as e:  # noqa: BLE001
            data = {"_error": str(e)}
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
        self.dataReady.emit(data)


# ---------------------------------------------------------------------------
# 数值格式化辅助
# ---------------------------------------------------------------------------

def fmt_size(value: Any) -> str:
    """将字节数格式化为可读字符串"""
    try:
        b = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if b <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while b >= 1024 and i < len(units) - 1:
        b /= 1024
        i += 1
    return f"{b:.2f} {units[i]}"


def fmt_datetime(value: Any) -> str:
    """将 CIM_DATETIME 格式化为 'YYYY-MM-DD HH:MM:SS'"""
    if not value:
        return "N/A"
    s = str(value)
    try:
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}:{s[12:14]}"
    except Exception:
        return s


def fmt_int(value: Any, suffix: str = "") -> str:
    try:
        v = int(value)
        return f"{v}{suffix}" if suffix else str(v)
    except (TypeError, ValueError):
        return "N/A"


def fmt_str(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


# ---------------------------------------------------------------------------
# 信息页基类
# ---------------------------------------------------------------------------

class BaseHardwarePage(QWidget):
    """硬件信息页基类：标题 + 刷新按钮 + 滚动键值卡片区 + 后台加载。

    子类只需实现 ``build_data(self, wmi) -> dict``，
    返回 {'groups': [{'title': str, 'rows': [(label, value), ...]}, ...]}。
    """

    page_id: str = ""
    page_name: str = ""
    page_title: str = ""

    def __init__(self, parent: QWidget = None, core: Any = None):
        super().__init__(parent)
        self.core = core
        self._loader: Optional[HardwareLoader] = None
        self._setup_ui()

    @classmethod
    def create(cls, parent: QWidget = None, core: Any = None) -> QWidget:
        return cls(parent, core=core)

    # ==================== UI ====================

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = StrongBodyLabel(self.page_title or self.page_name, self)
        header.addWidget(title)
        header.addStretch()

        self.refresh_btn = PushButton("刷新", self)
        self.refresh_btn.setIcon(FIF.SYNC)
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        self.status_label = BodyLabel("", self)
        self.status_label.setObjectName("hwStatusLabel")
        setCustomStyleSheet(
            self.status_label,
            "QLabel#hwStatusLabel { color: gray; font-size: 9pt; }",
            "QLabel#hwStatusLabel { color: #888; font-size: 9pt; }",
        )
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch()

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

    # ==================== 数据加载 ====================

    def refresh(self) -> None:
        """触发后台加载"""
        if self._loader is not None and self._loader.isRunning():
            return
        self.status_label.setText("正在读取硬件信息...")
        self.refresh_btn.setEnabled(False)

        self._loader = HardwareLoader(self.build_data, self)
        self._loader.dataReady.connect(self._on_data_ready)
        self._loader.start()

    def build_data(self, wmi: Any) -> dict:
        """子类实现：基于 wmi 连接返回分组数据"""
        raise NotImplementedError

    def _on_data_ready(self, data: dict) -> None:
        self.refresh_btn.setEnabled(True)
        if data.get("_error"):
            self.status_label.setText(f"读取失败：{data['_error']}")
            return
        self.status_label.setText("")
        self._render(data)

    # ==================== 渲染 ====================

    def _render(self, data: dict) -> None:
        groups = data.get("groups", [])
        self._clear_content()

        if not groups:
            self.status_label.setText("未获取到硬件信息（当前设备可能未提供相关数据）")
            return

        for group in groups:
            self.content_layout.insertWidget(
                self.content_layout.count() - 1,
                self._build_group_card(group),
            )

    def _build_group_card(self, group: Dict[str, Any]) -> CardWidget:
        card = CardWidget(self.content)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        title = StrongBodyLabel(group.get("title", ""), card)
        card_layout.addWidget(title)

        for label, value in group.get("rows", []):
            row = QHBoxLayout()
            row.setSpacing(8)
            key = BodyLabel(fmt_str(label), card)
            key.setObjectName("hwKeyLabel")
            setCustomStyleSheet(
                key,
                "QLabel#hwKeyLabel { color: gray; min-width: 120px; }",
                "QLabel#hwKeyLabel { color: #888; min-width: 120px; }",
            )
            val = BodyLabel(fmt_str(value), card)
            val.setWordWrap(True)
            row.addWidget(key)
            row.addWidget(val, 1)
            card_layout.addLayout(row)

        return card

    def _clear_content(self) -> None:
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout: QHBoxLayout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
