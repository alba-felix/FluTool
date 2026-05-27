"""首次注册对话框"""

from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    LineEdit, BodyLabel, InfoBar, InfoBarPosition,
    PrimaryPushButton, TitleLabel, CaptionLabel
)

from core.auth_service import AuthService
from utils.machine_id import generate_machine_short_code


class RegisterDialog(QDialog):
    """首次注册对话框——仅首次安装时弹出，注册成功后后续启动为无感验证"""

    WIDTH = 400
    HEIGHT = 480

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._auth = AuthService()
        self._init_window()
        self._setup_ui()

    def _init_window(self) -> None:
        self.setWindowTitle("FluTool - 注册")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _setup_ui(self) -> None:
        self._root = QWidget(self)
        self._root.setObjectName("registerRoot")
        self._root.setStyleSheet("""
            #registerRoot {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 12px;
            }
        """)
        self._root.setGeometry(10, 10, self.width() - 20, self.height() - 20)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self._root.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._root)
        layout.setContentsMargins(40, 40, 40, 30)
        layout.setSpacing(16)

        self._build_header(layout)
        self._build_form(layout)
        self._build_buttons(layout)
        layout.addStretch()
        self._build_footer(layout)

    def _build_header(self, parent: QVBoxLayout) -> None:
        title = TitleLabel("FluTool", self._root)
        title.setStyleSheet("color: #0078d4; font-size: 28px;")
        title.setAlignment(Qt.AlignCenter)
        parent.addWidget(title)

        subtitle = BodyLabel("首次使用，请设置账户信息", self._root)
        subtitle.setStyleSheet("color: #888888; font-size: 13px;")
        subtitle.setAlignment(Qt.AlignCenter)
        parent.addWidget(subtitle)
        parent.addSpacing(10)

    def _build_form(self, parent: QVBoxLayout) -> None:
        self._username_input = LineEdit(self._root)
        self._username_input.setPlaceholderText("用户名")
        self._username_input.setClearButtonEnabled(True)
        self._username_input.textChanged.connect(self._on_input_changed)
        parent.addWidget(self._username_input)

        self._password_input = LineEdit(self._root)
        self._password_input.setPlaceholderText("密码")
        self._password_input.setEchoMode(LineEdit.Password)
        self._password_input.setClearButtonEnabled(True)
        self._password_input.textChanged.connect(self._on_input_changed)
        parent.addWidget(self._password_input)

        self._confirm_input = LineEdit(self._root)
        self._confirm_input.setPlaceholderText("确认密码")
        self._confirm_input.setEchoMode(LineEdit.Password)
        self._confirm_input.setClearButtonEnabled(True)
        self._confirm_input.textChanged.connect(self._on_input_changed)
        self._confirm_input.returnPressed.connect(self._on_submit)
        parent.addWidget(self._confirm_input)

        self._error_label = BodyLabel("", self._root)
        self._error_label.setStyleSheet("color: #e81123; font-size: 12px;")
        self._error_label.setAlignment(Qt.AlignCenter)
        self._error_label.hide()
        parent.addWidget(self._error_label)

    def _build_buttons(self, parent: QVBoxLayout) -> None:
        self._submit_btn = PrimaryPushButton("注册", self._root)
        self._submit_btn.setEnabled(False)
        self._submit_btn.clicked.connect(self._on_submit)
        parent.addWidget(self._submit_btn)

    def _build_footer(self, parent: QVBoxLayout) -> None:
        machine_code = generate_machine_short_code()
        label = CaptionLabel(f"本机标识：{machine_code}", self._root)
        label.setStyleSheet("color: #555555;")
        label.setAlignment(Qt.AlignCenter)
        parent.addWidget(label)

    def _on_input_changed(self) -> None:
        self._error_label.hide()
        username = self._username_input.text().strip()
        password = self._password_input.text()
        confirm = self._confirm_input.text()
        self._submit_btn.setEnabled(bool(username and password and confirm))

    def _on_submit(self) -> None:
        username = self._username_input.text().strip()
        password = self._password_input.text()
        confirm = self._confirm_input.text()

        if not username or not password or not confirm:
            self._show_error("请填写完整信息")
            return

        if password != confirm:
            self._show_error("两次密码输入不一致")
            return

        if len(password) < 4:
            self._show_error("密码长度不能少于 4 位")
            return

        success, msg = self._auth.register(username, password)
        if success:
            InfoBar.success(
                title="注册成功",
                content="即将进入主界面，后续启动无需再次登录",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self,
            )
            QTimer.singleShot(1000, self.accept)
        else:
            self._show_error(msg)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()