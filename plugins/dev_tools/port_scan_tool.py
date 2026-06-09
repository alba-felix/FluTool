"""端口监听检测工具"""

import subprocess
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame
)
from qfluentwidgets import (
    FluentIcon as FIF, LineEdit, TransparentToolButton,
    StrongBodyLabel, isDarkTheme, qconfig
)

from plugins.text_tools.page_interface import TabPageInterface


class NetstatThread(QThread):
    """netstat 命令执行线程"""
    finished = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                "netstat -ano",
                shell=True,
                capture_output=True,
                text=True,
                encoding='gbk',
                timeout=15
            )
            self.finished.emit(result.stdout + result.stderr)
        except subprocess.TimeoutExpired:
            self.finished.emit("命令执行超时")
        except Exception as e:
            self.finished.emit(f"执行错误: {str(e)}")


class PortScanToolWidget(QWidget):
    """端口监听检测工具"""

    _TABLE_DARK_QSS = """
        QTableWidget {
            background-color: #1e1e1e;
            alternate-background-color: #252525;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            color: #d0d0d0;
            gridline-color: #333333;
        }
        QTableWidget::item:selected {
            background-color: #404040;
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-top: none;
            padding: 6px 8px;
            color: #ffffff;
            font-weight: bold;
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
    """
    _TABLE_LIGHT_QSS = """
        QTableWidget {
            background-color: #fafafa;
            alternate-background-color: #f0f0f0;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            color: #333333;
            gridline-color: #e8e8e8;
        }
        QTableWidget::item:selected {
            background-color: #d0d0d0;
            color: #333333;
        }
        QHeaderView::section {
            background-color: #f5f5f5;
            border: 1px solid #e0e0e0;
            border-top: none;
            padding: 6px 8px;
            color: #333333;
            font-weight: bold;
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
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: Optional[NetstatThread] = None
        self._all_connections: List[Tuple[str, str, str, str, str]] = []
        self.setObjectName("portScanWidget")
        self._setup_ui()
        self._sync_theme()
        qconfig.themeChanged.connect(self._sync_theme)

    def _setup_ui(self):
        self.setStyleSheet("#portScanWidget { background-color: transparent; }")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("portScanCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题行
        header = QHBoxLayout()
        header.addWidget(StrongBodyLabel("端口监听检测", card))
        header.addStretch()
        self.count_label = StrongBodyLabel("", card)
        header.addWidget(self.count_label)
        self.refresh_btn = TransparentToolButton(FIF.SYNC, card)
        self.refresh_btn.setToolTip("刷新")
        self.refresh_btn.clicked.connect(self._do_scan)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        # 搜索框
        self.search_input = LineEdit(card)
        self.search_input.setPlaceholderText("过滤（端口号 / 协议 / PID / 地址）...")
        self.search_input.textChanged.connect(self._filter)
        layout.addWidget(self.search_input)

        # 表格
        self.table = QTableWidget(card)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["协议", "本地地址", "外部地址", "状态", "PID"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.setMinimumHeight(200)
        self.table.setFont(QFont("Consolas", 9))
        layout.addWidget(self.table)

        main_layout.addWidget(card)

    def _sync_theme(self):
        """同步主题样式"""
        dark = isDarkTheme()

        # 卡片背景
        if dark:
            card_qss = (
                "#portScanCard { background-color: #2d2d2d;"
                " border-radius: 8px; border: 1px solid #3d3d3d; }"
            )
        else:
            card_qss = (
                "#portScanCard { background-color: #ffffff;"
                " border-radius: 8px; border: 1px solid #e0e0e0; }"
            )
        self.setStyleSheet(
            "#portScanWidget { background-color: transparent; }\n" + card_qss
        )

        # 表格样式直接设到 table 上，避免层级传播问题
        self.table.setStyleSheet(
            self._TABLE_DARK_QSS if dark else self._TABLE_LIGHT_QSS
        )

    def _do_scan(self):
        if self._thread and self._thread.isRunning():
            self._thread.terminate()
        self._thread = NetstatThread(self)
        self._thread.finished.connect(self._on_scan_result)
        self._thread.start()

    def _on_scan_result(self, output: str):
        lines = output.strip().split("\n")
        self._all_connections = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("Active") or stripped.startswith("Proto"):
                continue
            parts = stripped.split()
            if len(parts) < 5:
                continue
            proto = parts[0]
            local = parts[1]
            foreign = parts[2]
            state = parts[3] if proto.upper() == "TCP" else "*"
            pid = parts[-1]
            self._all_connections.append((proto, local, foreign, state, pid))

        self._apply_data(self._all_connections)

    def _apply_data(self, connections: List[Tuple[str, str, str, str, str]]):
        self.table.setRowCount(0)
        self.table.setRowCount(len(connections))

        for row, (proto, local, foreign, state, pid) in enumerate(connections):
            self.table.setItem(row, 0, QTableWidgetItem(proto))
            self.table.setItem(row, 1, QTableWidgetItem(local))
            self.table.setItem(row, 2, QTableWidgetItem(foreign))
            self.table.setItem(row, 3, QTableWidgetItem(state))
            self.table.setItem(row, 4, QTableWidgetItem(pid))

        # 先按内容调整列宽，再将本地/外部地址列设为 Stretch
        self.table.resizeColumnsToContents()
        header = self.table.horizontalHeader()
        for col in (0, 3, 4):
            width = header.sectionSize(col)
            header.setSectionResizeMode(col, QHeaderView.Interactive)
            header.resizeSection(col, max(width, 60))
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        self.count_label.setText(
            f"共 {len(connections)} 条连接" if connections else ""
        )

    def _filter(self, text: str):
        if not text.strip():
            self._apply_data(self._all_connections)
            return
        lower = text.strip().lower()
        filtered = [
            conn for conn in self._all_connections
            if any(lower in field.lower() for field in conn)
        ]
        self._apply_data(filtered)


class PortScanToolPage(TabPageInterface):
    """端口监听检测页面"""

    page_id = "port_scan"
    page_name = "端口检测"
    page_icon = FIF.SEARCH

    @classmethod
    def create(cls, parent=None) -> QWidget:
        widget = PortScanToolWidget(parent)
        widget._do_scan()
        return widget