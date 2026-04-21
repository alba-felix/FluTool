"""Hex 字符串转换工具"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel
)
from PyQt5.QtCore import Qt
from qfluentwidgets import PushButton, TextEdit, StrongBodyLabel, InfoBar, InfoBarPosition

from .page_interface import TabPageInterface


class HexConverterPage(TabPageInterface):
    """Hex 字符串转换页面"""

    page_id = "hex_converter"
    page_name = "Hex 转换"

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return HexConverterWidget(parent)


class HexConverterWidget(QWidget):
    """Hex 转换工具界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 标题
        # title = StrongBodyLabel("Hex 字符串转换", self)
        # title.setStyleSheet("font-size: 18px; font-weight: bold;")
        # layout.addWidget(title)

        # 使用说明
        help_text = QLabel(
            "使用说明：\n"
            "1. 在文本框中输入要转换的内容\n"
            "2. 如果要将普通文本转换为十六进制，点击\"十六进制(Hex)\"按钮\n"
            "3. 如果要将十六进制转换为普通文本，点击\"字符串(Str)\"按钮\n\n",
            self
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(help_text)

        # 输入框
        self.input_edit = TextEdit(self)
        self.input_edit.setPlaceholderText("在此输入要转换的内容...")
        self.input_edit.setMinimumHeight(200)
        layout.addWidget(self.input_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.to_hex_btn = PushButton("十六进制(Hex)", self)
        self.to_hex_btn.clicked.connect(self._to_hex)
        btn_layout.addWidget(self.to_hex_btn)

        self.to_str_btn = PushButton("字符串(Str)", self)
        self.to_str_btn.clicked.connect(self._to_str)
        btn_layout.addWidget(self.to_str_btn)

        self.clear_btn = PushButton("清空", self)
        self.clear_btn.clicked.connect(self._clear)
        btn_layout.addWidget(self.clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 输出框
        self.output_edit = TextEdit(self)
        self.output_edit.setPlaceholderText("转换结果将显示在这里...")
        self.output_edit.setMinimumHeight(200)
        self.output_edit.setReadOnly(True)
        layout.addWidget(self.output_edit)

        # 复制按钮
        self.copy_btn = PushButton("复制结果", self)
        self.copy_btn.clicked.connect(self._copy_result)
        layout.addWidget(self.copy_btn)

        layout.addStretch()

    def _to_hex(self) -> None:
        """将字符串转换为十六进制"""
        text = self.input_edit.toPlainText().strip()
        if not text:
            InfoBar.warning(
                title="输入为空",
                content="请输入要转换的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            import binascii
            hex_str = binascii.hexlify(text.encode('utf-8')).decode('utf-8')
            self.output_edit.setPlainText(hex_str)
            InfoBar.success(
                title="转换成功",
                content="已转换为十六进制",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="转换失败",
                content=f"错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _to_str(self) -> None:
        """将十六进制转换为字符串"""
        hex_text = self.input_edit.toPlainText().strip()
        if not hex_text:
            InfoBar.warning(
                title="输入为空",
                content="请输入要转换的十六进制内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            import binascii
            # 移除可能的空格和换行
            hex_text = hex_text.replace(' ', '').replace('\n', '')
            # 检查是否为有效的十六进制
            if len(hex_text) % 2 != 0:
                raise ValueError("十六进制字符串长度必须为偶数")
            
            result = binascii.unhexlify(hex_text).decode('utf-8', errors='replace')
            self.output_edit.setPlainText(result)
            InfoBar.success(
                title="转换成功",
                content="已转换为字符串",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="转换失败",
                content=f"错误：{str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _clear(self) -> None:
        """清空输入和输出"""
        self.input_edit.clear()
        self.output_edit.clear()

    def _copy_result(self) -> None:
        """复制结果到剪贴板"""
        result = self.output_edit.toPlainText()
        if result:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(result)
            InfoBar.success(
                title="已复制",
                content="结果已复制到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            InfoBar.warning(
                title="无内容",
                content="没有可复制的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
