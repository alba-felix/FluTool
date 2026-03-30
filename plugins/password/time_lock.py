"""定时密码锁 - 时间密码查看功能"""

import json
import time
import base64
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QApplication, QGroupBox, QGridLayout
)

from qfluentwidgets import (
    PushButton, LineEdit, SpinBox, ComboBox, BodyLabel,
    StrongBodyLabel, CardWidget, InfoBar, InfoBarPosition,
    MessageBoxBase, SubtitleLabel, MessageBox
)
from qfluentwidgets import FluentIcon as FIF

from core import get_app_data_path


# ----------------------------- 加密/解密（XOR + Base64）-----------------------------
SECRET_KEY = b'simple-time-lock-2026'


def encrypt_password(plain: str) -> str:
    """加密密码"""
    plain_bytes = plain.encode('utf-8')
    encrypted_bytes = bytes([plain_bytes[i] ^ SECRET_KEY[i % len(SECRET_KEY)] for i in range(len(plain_bytes))])
    return base64.b64encode(encrypted_bytes).decode('utf-8')


def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    encrypted_bytes = base64.b64decode(encrypted)
    plain_bytes = bytes([encrypted_bytes[i] ^ SECRET_KEY[i % len(SECRET_KEY)] for i in range(len(encrypted_bytes))])
    return plain_bytes.decode('utf-8')


def format_remaining(seconds: float) -> str:
    """格式化剩余时间"""
    if seconds <= 0:
        return "已解锁"
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")
    return " ".join(parts)


# ----------------------------- 配置文件操作 -----------------------------
CONFIG_FILE = "time_lock_data.json"


def get_config_path() -> Path:
    """获取配置文件路径"""
    return get_app_data_path(f"config/{CONFIG_FILE}")


def save_config(encrypted_pwd: str, unlock_timestamp: float) -> None:
    """保存配置"""
    data = {
        "encrypted_password": encrypted_pwd,
        "unlock_timestamp": unlock_timestamp
    }
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)


def load_config() -> Tuple[Optional[str], float]:
    """加载配置"""
    try:
        config_path = get_config_path()
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("encrypted_password"), data.get("unlock_timestamp", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return None, 0


# ----------------------------- 定时密码锁管理器 -----------------------------
class TimeLockManager:
    """定时密码锁管理器"""

    def __init__(self):
        self.encrypted_pwd: Optional[str] = None
        self.unlock_timestamp: float = 0
        self._load()

    def _load(self):
        """加载配置"""
        self.encrypted_pwd, self.unlock_timestamp = load_config()

    def has_password(self) -> bool:
        """是否有设置的密码"""
        return self.encrypted_pwd is not None and len(self.encrypted_pwd) > 0

    def is_unlocked(self) -> bool:
        """是否已解锁"""
        if not self.has_password():
            return False
        return time.time() >= self.unlock_timestamp

    def get_remaining_seconds(self) -> float:
        """获取剩余锁定时间"""
        if not self.has_password():
            return 0
        remain = self.unlock_timestamp - time.time()
        return max(0, remain)

    def set_password(self, password: str, seconds: float) -> None:
        """设置密码"""
        self.encrypted_pwd = encrypt_password(password)
        self.unlock_timestamp = time.time() + seconds
        save_config(self.encrypted_pwd, self.unlock_timestamp)

    def clear_password(self) -> None:
        """清除密码"""
        self.encrypted_pwd = None
        self.unlock_timestamp = 0
        config_path = get_config_path()
        if config_path.exists():
            config_path.unlink()

    def get_password(self) -> Optional[str]:
        """获取明文密码（仅当已解锁时）"""
        if not self.is_unlocked():
            return None
        try:
            return decrypt_password(self.encrypted_pwd)
        except Exception:
            return None


# ----------------------------- 整合的定时密码锁对话框 -----------------------------
class TimeLockDialog(MessageBoxBase):
    """定时密码锁主对话框 - 整合所有功能在一个窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = TimeLockManager()
        self.plain_password = ""

        self.setWindowTitle("定时密码锁")

        self.titleLabel = SubtitleLabel("时间密码锁工具", self)
        self.viewLayout.addWidget(self.titleLabel)

        # ========== 锁定状态区域 ==========
        self.status_group = QGroupBox("锁定状态", self)
        status_layout = QVBoxLayout(self.status_group)

        self.status_label = StrongBodyLabel("", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        self.viewLayout.addWidget(self.status_group)

        # ========== 密码显示区域 ==========
        self.password_group = QGroupBox("密码（加密状态）", self)
        password_layout = QVBoxLayout(self.password_group)

        self.encrypted_edit = LineEdit(self)
        self.encrypted_edit.setReadOnly(True)
        self.encrypted_edit.setText(self.manager.encrypted_pwd if self.manager.encrypted_pwd else "未设置密码")
        password_layout.addWidget(self.encrypted_edit)

        # 明文密码显示（解锁后可见）
        self.plain_label = BodyLabel("", self)
        self.plain_label.setAlignment(Qt.AlignCenter)
        self.plain_label.setWordWrap(True)
        password_layout.addWidget(self.plain_label)

        self.viewLayout.addWidget(self.password_group)

        # ========== 设置新密码区域 ==========
        self.set_group = QGroupBox("设置新密码", self)
        set_layout = QGridLayout(self.set_group)

        # 明文密码输入
        set_layout.addWidget(BodyLabel("明文密码:", self), 0, 0)
        self.password_edit = LineEdit(self)
        self.password_edit.setPlaceholderText("输入要锁定的密码")
        self.password_edit.setEchoMode(LineEdit.Password)
        set_layout.addWidget(self.password_edit, 0, 1)

        # 随机生成按钮
        self.generate_btn = PushButton("随机生成", self)
        self.generate_btn.clicked.connect(self._generate_random_password)
        set_layout.addWidget(self.generate_btn, 0, 2)

        # 锁定时长
        set_layout.addWidget(BodyLabel("锁定时长:", self), 1, 0)

        duration_layout = QHBoxLayout()
        self.lock_value = SpinBox(self)
        self.lock_value.setRange(1, 9999)
        self.lock_value.setValue(1)
        duration_layout.addWidget(self.lock_value)

        self.lock_unit = ComboBox(self)
        self.lock_unit.addItems(["分钟", "小时", "天", "周", "月"])
        self.lock_unit.setCurrentIndex(0)
        duration_layout.addWidget(self.lock_unit)
        duration_layout.addStretch()

        set_layout.addLayout(duration_layout, 1, 1, 1, 2)

        # 设置并锁定按钮
        self.set_lock_btn = PushButton("设置并锁定", self)
        self.set_lock_btn.clicked.connect(self._on_set_password)
        set_layout.addWidget(self.set_lock_btn, 2, 1, 1, 2, Qt.AlignCenter)

        self.viewLayout.addWidget(self.set_group)

        # 底部提示
        self.tip_label = BodyLabel("", self)
        self.tip_label.setWordWrap(True)
        self.tip_label.setAlignment(Qt.AlignCenter)
        self.viewLayout.addWidget(self.tip_label)

        # 按钮设置
        self.yesButton.setText("复制明文密码")
        self.cancelButton.setText("关闭")
        self.widget.setMinimumWidth(500)

        # 初始化状态
        self._update_status()

        # 定时更新状态
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_status)
        self.timer.start(1000)

    def _update_status(self):
        """更新状态显示"""
        if not self.manager.has_password():
            self.status_label.setText("⚠️ 未设置密码")
            self.status_label.setStyleSheet("color: #ffc107;")
            self.encrypted_edit.setText("未设置密码")
            self.plain_label.setText("")
            self.plain_label.setStyleSheet("")
            self.tip_label.setText("请设置新密码")
            self.yesButton.setEnabled(False)
        elif self.manager.is_unlocked():
            self.status_label.setText("✅ 已解锁 - 可双击明文密码区域复制")
            self.status_label.setStyleSheet("color: #28a745;")
            self.encrypted_edit.setText(self.manager.encrypted_pwd)
            # 显示明文密码
            try:
                self.plain_password = decrypt_password(self.manager.encrypted_pwd)
                self.plain_label.setText(f"明文: {self.plain_password}")
                self.plain_label.setStyleSheet("color: #28a745; font-size: 14px; font-weight: bold;")
                # 启用双击复制
                self.plain_label.mouseDoubleClickEvent = self._on_password_double_click
            except Exception:
                self.plain_label.setText("解密失败")
                self.plain_label.setStyleSheet("color: #dc3545;")
            self.tip_label.setText('密码已解锁，可以点击"复制明文密码"按钮或双击上方明文密码复制到剪贴板')
            self.yesButton.setEnabled(True)
        else:
            remain_str = format_remaining(self.manager.get_remaining_seconds())
            self.status_label.setText(f"🔒 锁定中 - 剩余 {remain_str}")
            self.status_label.setStyleSheet("color: #dc3545;")
            self.encrypted_edit.setText(self.manager.encrypted_pwd)
            self.plain_label.setText("********")
            self.plain_label.setStyleSheet("color: #dc3545; font-size: 14px;")
            self.plain_label.mouseDoubleClickEvent = None
            self.tip_label.setText(f"密码已锁定，还需等待 {remain_str} 才能查看")
            self.yesButton.setEnabled(False)

    def _generate_random_password(self):
        """生成随机密码"""
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

        password_chars = [
            random.choice(lowercase),
            random.choice(uppercase),
            random.choice(digits),
            random.choice(special)
        ]

        remaining = random.randint(6, 16)
        all_chars = lowercase + uppercase + digits + special
        password_chars.extend(random.choice(all_chars) for _ in range(remaining))
        random.shuffle(password_chars)
        password = ''.join(password_chars)

        self.password_edit.setText(password)

        # 使用可手动关闭的对话框显示密码
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("随机密码已生成")

        dialog.titleLabel = SubtitleLabel("生成的密码", dialog)
        dialog.viewLayout.addWidget(dialog.titleLabel)

        # 密码显示（可复制）
        password_display = LineEdit(dialog)
        password_display.setText(password)
        password_display.setReadOnly(True)
        password_display.setAlignment(Qt.AlignCenter)
        font = password_display.font()
        font.setPointSize(14)
        font.setBold(True)
        password_display.setFont(font)
        dialog.viewLayout.addWidget(password_display)

        # 提示文字
        tip_label = BodyLabel("请记住此密码，它将用于后续解锁。\n密码已自动填入输入框。", dialog)
        tip_label.setWordWrap(True)
        tip_label.setAlignment(Qt.AlignCenter)
        dialog.viewLayout.addWidget(tip_label)

        dialog.yesButton.setText("复制并关闭")
        dialog.cancelButton.hide()
        dialog.widget.setMinimumWidth(400)

        # 点击确定按钮复制密码
        def on_accept():
            QApplication.clipboard().setText(password)
            InfoBar.success(
                title="已复制",
                content="密码已复制到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        dialog.yesButton.clicked.connect(on_accept)
        dialog.exec()

    def _on_set_password(self):
        """设置新密码"""
        password = self.password_edit.text().strip()
        if not password:
            InfoBar.warning(
                title="提示",
                content="请输入密码",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        value = self.lock_value.value()
        unit = self.lock_unit.currentText()

        if unit == "分钟":
            seconds = value * 60
        elif unit == "小时":
            seconds = value * 3600
        elif unit == "天":
            seconds = value * 86400
        elif unit == "周":
            seconds = value * 7 * 86400
        elif unit == "月":
            now = datetime.now()
            try:
                target_year = now.year + (now.month + value - 1) // 12
                target_month = (now.month + value - 1) % 12 + 1
                days_in_month = [31, 29 if target_year % 4 == 0 and (target_year % 100 != 0 or target_year % 400 == 0) else 28,
                                 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                target_day = min(now.day, days_in_month[target_month - 1])
                target_date = datetime(target_year, target_month, target_day, now.hour, now.minute, now.second)
                seconds = (target_date - now).total_seconds()
            except Exception:
                seconds = value * 30 * 86400
        else:
            seconds = value * 60

        if seconds <= 0:
            InfoBar.warning(
                title="提示",
                content="时长必须大于0",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        # 确认覆盖
        if self.manager.has_password():
            if not MessageBox(
                "确认覆盖",
                "已有定时密码，确定要覆盖吗？",
                self
            ).exec():
                return

        self.manager.set_password(password, seconds)
        self.password_edit.clear()

        InfoBar.success(
            title="设置成功",
            content=f"密码已锁定 {value}{unit}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )
        self._update_status()

    def _on_password_double_click(self, event):
        """双击密码区域复制"""
        if self.plain_password:
            QApplication.clipboard().setText(self.plain_password)
            InfoBar.success(
                title="已复制",
                content="明文密码已复制到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def accept(self):
        """确认按钮点击 - 复制密码"""
        if self.plain_password:
            QApplication.clipboard().setText(self.plain_password)
            InfoBar.success(
                title="已复制",
                content="明文密码已复制到剪贴板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        super().closeEvent(event)
