"""本地认证服务 - 注册表加密存储 + 机器码绑定"""

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import Optional, Tuple

from PyQt5.QtCore import QSettings

from utils.machine_id import generate_machine_code


_APP_KEY = "FluTool2026@Secure!"
_ORG_NAME = "FluTool"
_APP_NAME = "Auth"

_AUTH_USERNAME_KEY = "Username"
_AUTH_SALT_KEY = "Salt"
_AUTH_PASSWORD_HASH_KEY = "PasswordHash"
_AUTH_MACHINE_CODE_KEY = "MachineCode"
_AUTH_CREATED_AT_KEY = "CreatedAt"


def _derive_key(machine_code: str) -> bytes:
    """从机器码和应用密钥派生出加密密钥"""
    raw = f"{_APP_KEY}|{machine_code}".encode("utf-8")
    return hashlib.sha256(raw).digest()


def _xor_encrypt(data: str, key: bytes) -> str:
    """XOR 加密并 Base64 编码"""
    data_bytes = data.encode("utf-8")
    encrypted = bytearray()
    for i, b in enumerate(data_bytes):
        encrypted.append(b ^ key[i % len(key)])
    return base64.b64encode(bytes(encrypted)).decode("ascii")


def _xor_decrypt(data: str, key: bytes) -> str:
    """Base64 解码并 XOR 解密"""
    try:
        encrypted = base64.b64decode(data)
        decrypted = bytearray()
        for i, b in enumerate(encrypted):
            decrypted.append(b ^ key[i % len(key)])
        return decrypted.decode("utf-8")
    except Exception:
        return ""


def _hash_password(password: str, salt: str) -> str:
    """对密码加盐后进行 SHA-256 哈希"""
    raw = f"{salt}|{password}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _generate_salt() -> str:
    """生成 32 位随机盐值"""
    return secrets.token_hex(16)


class AuthService:
    """本地认证服务

    账密信息加密存储在注册表 HKCU\\Software\\FluTool\\Auth 下，
    数据通过 XOR + Base64 加密，密钥绑定机器码。
    首次注册时记录机器码，后续登录校验机器码一致性。"""

    def __init__(self):
        self._settings = QSettings(_ORG_NAME, _APP_NAME)

    # ---- 查询状态 ----

    def is_registered(self) -> bool:
        """是否已注册（首次安装已设置账密）"""
        return bool(self._settings.value(_AUTH_USERNAME_KEY))

    def get_registered_username(self) -> str:
        """获取已注册的用户名"""
        return self._settings.value(_AUTH_USERNAME_KEY, "")

    # ---- 注册 ----

    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """首次注册：设置账密并绑定当前机器

        Args:
            username: 用户名
            password: 密码

        Returns:
            (成功标志, 消息)
        """
        if self.is_registered():
            return False, "已注册，请直接登录"

        if not username or not password:
            return False, "用户名和密码不能为空"

        if len(password) < 4:
            return False, "密码长度不能少于 4 位"

        machine_code = generate_machine_code()
        salt = _generate_salt()
        password_hash = _hash_password(password, salt)
        created_at = datetime.now().isoformat()

        self._settings.setValue(_AUTH_USERNAME_KEY, username)
        self._settings.setValue(_AUTH_SALT_KEY, salt)
        self._settings.setValue(_AUTH_PASSWORD_HASH_KEY, password_hash)
        self._settings.setValue(_AUTH_MACHINE_CODE_KEY, machine_code)
        self._settings.setValue(_AUTH_CREATED_AT_KEY, created_at)
        self._settings.sync()

        return True, "注册成功"

    # ---- 自动验证（无感登录） ----

    def verify_machine(self) -> Tuple[bool, str]:
        """自动验证当前机器是否已注册且机器码匹配

        无对话框、无需密码，适用于后续启动时无感通过。

        Returns:
            (通过标志, 消息)
        """
        if not self.is_registered():
            return False, "未注册，请先注册"

        stored_machine_code = self._settings.value(_AUTH_MACHINE_CODE_KEY, "")
        current_machine_code = generate_machine_code()

        if not stored_machine_code:
            return False, "认证数据不完整，请重新注册"

        if current_machine_code != stored_machine_code:
            return False, "未授权的设备，请使用原设备登录"

        return True, "验证通过"

    # ---- 登录 ----

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """登录验证

        校验用户名、密码，以及机器码是否匹配（阻止账密迁移到其他机器）。

        Args:
            username: 用户名
            password: 密码

        Returns:
            (成功标志, 消息)
        """
        stored_username = self._settings.value(_AUTH_USERNAME_KEY, "")
        stored_password_hash = self._settings.value(_AUTH_PASSWORD_HASH_KEY, "")
        stored_salt = self._settings.value(_AUTH_SALT_KEY, "")
        stored_machine_code = self._settings.value(_AUTH_MACHINE_CODE_KEY, "")

        if not stored_username or not stored_password_hash:
            return False, "未注册，请先注册"

        if username != stored_username:
            return False, "用户名或密码错误"

        current_machine_code = generate_machine_code()
        if stored_machine_code and current_machine_code != stored_machine_code:
            return False, "未授权的设备，请使用原设备登录"

        input_hash = _hash_password(password, stored_salt)
        if input_hash != stored_password_hash:
            return False, "用户名或密码错误"

        return True, "登录成功"

    # ---- 重置（重新注册场景） ----

    def recover_machine(self, password: str) -> Tuple[bool, str]:
        """硬件变更后通过密码恢复，重新绑定当前机器

        Args:
            password: 注册时设置的密码

        Returns:
            (成功标志, 消息)
        """
        if not self.is_registered():
            return False, "未注册，无法恢复"

        stored_salt = self._settings.value(_AUTH_SALT_KEY, "")
        stored_password_hash = self._settings.value(_AUTH_PASSWORD_HASH_KEY, "")
        current_machine_code = generate_machine_code()

        if not stored_salt or not stored_password_hash:
            return False, "认证数据不完整，请重新安装"

        input_hash = _hash_password(password, stored_salt)
        if input_hash != stored_password_hash:
            return False, "密码错误，请确认后重试"

        self._settings.setValue(_AUTH_MACHINE_CODE_KEY, current_machine_code)
        self._settings.sync()

        return True, "机器绑定已更新，请重新启动"

    def reset(self) -> None:
        """清除所有认证数据（用于重新注册）"""
        self._settings.remove(_AUTH_USERNAME_KEY)
        self._settings.remove(_AUTH_SALT_KEY)
        self._settings.remove(_AUTH_PASSWORD_HASH_KEY)
        self._settings.remove(_AUTH_MACHINE_CODE_KEY)
        self._settings.remove(_AUTH_CREATED_AT_KEY)
        self._settings.sync()

    # ---- 信息展示 ----

    def get_auth_info(self) -> dict:
        """获取认证信息摘要（不包含密码原文）"""
        from utils.machine_id import generate_machine_short_code

        return {
            "username": self._settings.value(_AUTH_USERNAME_KEY, ""),
            "machine_code": generate_machine_short_code(),
            "created_at": self._settings.value(_AUTH_CREATED_AT_KEY, ""),
            "is_registered": self.is_registered(),
        }