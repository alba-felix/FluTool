"""
网络信息插件
提供网络配置查看、IP转换、Ping、DNS等功能
"""
import socket
import subprocess
from typing import List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPlainTextEdit, QLabel, QFrame, QSizePolicy
)
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, isDarkTheme, qconfig,
    TransparentToolButton, StrongBodyLabel, SubtitleLabel,
    BodyLabel, CardWidget, TextEdit, ScrollArea
)
from core import PluginInterface


class CommandThread(QThread):
    """命令执行线程"""
    finished = pyqtSignal(str)
    
    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self.command = command
    
    def run(self):
        try:
            if self.command.startswith("ping"):
                result = subprocess.run(
                    self.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    timeout=30
                )
            else:
                result = subprocess.run(
                    self.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    timeout=10
                )
            output = result.stdout + result.stderr
            self.finished.emit(output)
        except subprocess.TimeoutExpired:
            self.finished.emit("命令执行超时")
        except Exception as e:
            self.finished.emit(f"执行错误: {str(e)}")


class IPv4LongCard(CardWidget):
    """IPv4和Long值互转卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        layout.addWidget(StrongBodyLabel("📶 IPv4地址和Long值互转", self))
        
        ipv4_layout = QHBoxLayout()
        ipv4_layout.addWidget(BodyLabel("IPv4:", self))
        self.ipv4_input = LineEdit(self)
        self.ipv4_input.setPlaceholderText("例如: 192.168.1.1")
        ip_regex = QRegExp(r"^(\d{1,3}\.){0,3}\d{0,3}$")
        self.ipv4_input.setValidator(QRegExpValidator(ip_regex, self))
        ipv4_layout.addWidget(self.ipv4_input)
        layout.addLayout(ipv4_layout)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.to_long_btn = PushButton("⬇️ 转 Long", self)
        self.to_long_btn.clicked.connect(self._ipv4_to_long)
        btn_layout.addWidget(self.to_long_btn)
        self.to_ipv4_btn = PushButton("⬆️ 转 IPv4", self)
        self.to_ipv4_btn.clicked.connect(self._long_to_ipv4)
        btn_layout.addWidget(self.to_ipv4_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        long_layout = QHBoxLayout()
        long_layout.addWidget(BodyLabel("Long:", self))
        self.long_input = LineEdit(self)
        self.long_input.setPlaceholderText("例如: 3232235777")
        long_regex = QRegExp(r"^\d*$")
        self.long_input.setValidator(QRegExpValidator(long_regex, self))
        long_layout.addWidget(self.long_input)
        layout.addLayout(long_layout)
    
    def _ipv4_to_long(self):
        ipv4 = self.ipv4_input.text().strip()
        if not ipv4:
            return
        try:
            parts = ipv4.split(".")
            if len(parts) != 4:
                raise ValueError("IPv4格式错误")
            long_value = 0
            for part in parts:
                if not 0 <= int(part) <= 255:
                    raise ValueError("IPv4格式错误")
                long_value = (long_value << 8) | int(part)
            self.long_input.setText(str(long_value))
        except Exception as e:
            InfoBar.error(
                title="转换失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _long_to_ipv4(self):
        long_str = self.long_input.text().strip()
        if not long_str:
            return
        try:
            long_value = int(long_str)
            if long_value < 0 or long_value > 4294967295:
                raise ValueError("Long值超出范围")
            ipv4 = f"{(long_value >> 24) & 255}.{(long_value >> 16) & 255}.{(long_value >> 8) & 255}.{long_value & 255}"
            self.ipv4_input.setText(ipv4)
        except Exception as e:
            InfoBar.error(
                title="转换失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )


class PingCard(CardWidget):
    """PING卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._parent_widget = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        layout.addWidget(StrongBodyLabel("📡 PING", self))
        
        input_layout = QHBoxLayout()
        self.host_input = LineEdit(self)
        self.host_input.setPlaceholderText("输入域名或IP地址")
        input_layout.addWidget(self.host_input)
        self.ping_btn = PushButton("Ping", self)
        self.ping_btn.clicked.connect(self._do_ping)
        input_layout.addWidget(self.ping_btn)
        layout.addLayout(input_layout)
    
    def set_parent_widget(self, widget):
        self._parent_widget = widget
    
    def _do_ping(self):
        host = self.host_input.text().strip()
        if not host:
            return
        if self._parent_widget and hasattr(self._parent_widget, 'run_command'):
            self._parent_widget.run_command(f"ping {host} -n 4")


class DnsCard(CardWidget):
    """DNS卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._parent_widget = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        layout.addWidget(StrongBodyLabel("🧩 DNS", self))
        
        self.flush_btn = PushButton("🔄 刷新DNS缓存", self)
        self.flush_btn.clicked.connect(self._flush_dns)
        layout.addWidget(self.flush_btn)
    
    def set_parent_widget(self, widget):
        self._parent_widget = widget
    
    def _flush_dns(self):
        if self._parent_widget and hasattr(self._parent_widget, 'run_command'):
            self._parent_widget.run_command("ipconfig /flushdns")


class IpListCard(CardWidget):
    """IP列表卡片"""
    
    def __init__(self, title: str, icon: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.title = title
        self.icon = icon
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(StrongBodyLabel(f"{self.icon} {self.title}", self))
        header_layout.addStretch()
        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setToolTip("刷新")
        header_layout.addWidget(self.refresh_btn)
        layout.addLayout(header_layout)
        
        self.ip_list = TextEdit(self)
        self.ip_list.setReadOnly(True)
        self.ip_list.setFont(QFont("Consolas", 10))
        layout.addWidget(self.ip_list)
    
    def set_ips(self, ips: List[str]):
        self.ip_list.setPlainText("\n".join(ips))


class DomainIpCard(CardWidget):
    """域名获取IP卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        layout.addWidget(StrongBodyLabel("🌐 通过域名获取IP", self))
        
        input_layout = QHBoxLayout()
        self.domain_input = LineEdit(self)
        self.domain_input.setPlaceholderText("输入域名")
        input_layout.addWidget(self.domain_input)
        self.query_btn = PushButton("查询", self)
        self.query_btn.clicked.connect(self._query)
        input_layout.addWidget(self.query_btn)
        layout.addLayout(input_layout)
        
        self.result_label = BodyLabel("", self)
        layout.addWidget(self.result_label)
    
    def _query(self):
        domain = self.domain_input.text().strip()
        if not domain:
            return
        try:
            ip = socket.gethostbyname(domain)
            self.result_label.setText(f"IP: {ip}")
        except Exception as e:
            self.result_label.setText(f"查询失败: {str(e)}")


class NetworkWidget(QWidget):
    """网络信息主组件"""
    
    PLUGIN_ID = "network"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._command_thread: Optional[CommandThread] = None
        
        self._setup_ui()
        self._apply_style()
        qconfig.themeChangedFinished.connect(self._apply_style)
        self._refresh_ipconfig()
    
    def _setup_ui(self):
        self.setObjectName("networkWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)
        
        left_widget = QWidget()
        left_widget.setObjectName("leftPanel")
        self.left_widget = left_widget
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(SubtitleLabel("🖥️ Windows IP 配置", left_widget))
        header_layout.addStretch()
        self.refresh_btn = TransparentToolButton(FIF.SYNC, left_widget)
        self.refresh_btn.setToolTip("刷新(ipconfig)")
        self.refresh_btn.clicked.connect(self._refresh_ipconfig)
        header_layout.addWidget(self.refresh_btn)
        self.refresh_all_btn = TransparentToolButton(FIF.UPDATE, left_widget)
        self.refresh_all_btn.setToolTip("刷新(ipconfig /all)")
        self.refresh_all_btn.clicked.connect(self._refresh_ipconfig_all)
        header_layout.addWidget(self.refresh_all_btn)
        left_layout.addLayout(header_layout)
        
        self.ipconfig_output = QPlainTextEdit(left_widget)
        self.ipconfig_output.setReadOnly(True)
        self.ipconfig_output.setFont(QFont("Consolas", 10))
        self.ipconfig_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        left_layout.addWidget(self.ipconfig_output)
        
        right_widget = QWidget()
        right_widget.setObjectName("rightPanel")
        self.right_widget = right_widget
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)
        
        scroll_area = ScrollArea(right_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        
        self.ipv4_long_card = IPv4LongCard(scroll_content)
        scroll_layout.addWidget(self.ipv4_long_card)
        
        self.ping_card = PingCard(scroll_content)
        self.ping_card.set_parent_widget(self)
        scroll_layout.addWidget(self.ping_card)
        
        self.dns_card = DnsCard(scroll_content)
        self.dns_card.set_parent_widget(self)
        scroll_layout.addWidget(self.dns_card)
        
        self.ipv4_card = IpListCard("📋 获取本机IPv4列表", "📋", scroll_content)
        self.ipv4_card.refresh_btn.clicked.connect(self._refresh_ipv4_list)
        scroll_layout.addWidget(self.ipv4_card)
        
        self.ipv6_card = IpListCard("📋 获取本机IPv6列表", "📋", scroll_content)
        self.ipv6_card.refresh_btn.clicked.connect(self._refresh_ipv6_list)
        scroll_layout.addWidget(self.ipv6_card)
        
        self.domain_card = DomainIpCard(scroll_content)
        scroll_layout.addWidget(self.domain_card)
        
        scroll_area.setWidget(scroll_content)
        scroll_area.enableTransparentBackground()
        scroll_area.viewport().setAutoFillBackground(False)
        
        right_layout.addWidget(scroll_area)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 400])
        
        main_layout.addWidget(splitter)
    
    def _apply_style(self):
        scrollbar_dark = """
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
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4d4d4d;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5d5d5d;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """
        scrollbar_light = """
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
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#networkWidget {
                    background-color: #1e1e1e;
                }
                QSplitter {
                    background-color: #1e1e1e;
                }
                QSplitter::handle {
                    background-color: #3d3d3d;
                }
                QPlainTextEdit {
                    background-color: #252525;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                    color: #ffffff;
                }
                TextEdit {
                    background-color: #252525;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                    color: #ffffff;
                }
            """ + scrollbar_dark)
            self.left_widget.setStyleSheet("background-color: #1e1e1e;")
            self.right_widget.setStyleSheet("background-color: #1e1e1e;")
        else:
            self.setStyleSheet("""
                QWidget#networkWidget {
                    background-color: #f5f5f5;
                }
                QSplitter {
                    background-color: #f5f5f5;
                }
                QSplitter::handle {
                    background-color: #e0e0e0;
                }
                QPlainTextEdit {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    color: #000000;
                }
                TextEdit {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    color: #000000;
                }
            """ + scrollbar_light)
            self.left_widget.setStyleSheet("background-color: #f5f5f5;")
            self.right_widget.setStyleSheet("background-color: #f5f5f5;")
    
    def _refresh_ipconfig(self):
        self.run_command("ipconfig")
    
    def _refresh_ipconfig_all(self):
        self.run_command("ipconfig /all")
    
    def run_command(self, command: str):
        if self._command_thread and self._command_thread.isRunning():
            self._command_thread.terminate()
        
        self._command_thread = CommandThread(command, self)
        self._command_thread.finished.connect(self._on_command_finished)
        self._command_thread.start()
    
    def _on_command_finished(self, output: str):
        self.ipconfig_output.setPlainText(output)
        self._refresh_ipv4_list()
        self._refresh_ipv6_list()
    
    def _refresh_ipv4_list(self):
        ips = []
        try:
            hostname = socket.gethostname()
            addrinfo = socket.getaddrinfo(hostname, None, socket.AF_INET)
            for item in addrinfo:
                ip = item[4][0]
                if ip not in ips:
                    ips.append(ip)
        except Exception:
            ips = ["127.0.0.1"]
        self.ipv4_card.set_ips(ips)
    
    def _refresh_ipv6_list(self):
        ips = []
        try:
            hostname = socket.gethostname()
            addrinfo = socket.getaddrinfo(hostname, None, socket.AF_INET6)
            for item in addrinfo:
                ip = item[4][0]
                if ip not in ips and not ip.startswith("fe80"):
                    ips.append(ip)
        except Exception:
            pass
        self.ipv6_card.set_ips(ips if ips else ["无IPv6地址"])
    
    def load_data(self) -> None:
        pass


class Plugin(PluginInterface):
    """网络信息插件"""
    
    PLUGIN_ID = "network"
    PLUGIN_NAME = "网络信息"
    PLUGIN_ICON = FIF.GLOBE
    PLUGIN_PRIORITY = 19
    
    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        return NetworkWidget(self.core, parent)
    
    def load_data(self) -> None:
        if self._widget:
            self._widget.load_data()
