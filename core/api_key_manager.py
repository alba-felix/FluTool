"""
API Key 管理器
单独管理各提供商的 API Key，与配置文件分离
本地加密存储，向服务器发送时解密为原文
"""
import json
from pathlib import Path
from typing import Dict, Optional

from .utils import get_app_data_path
from utils.crypto_utils import CharCryptoTool


_CRYPTO_KEY = 20260406
_ENCRYPTED_PREFIX = "!ENC:"


class APIKeyManager:
    """API Key 管理器 - 单独文件存储敏感信息"""
    
    DEFAULT_FILE = "config/local_api_key.json"
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = Path(file_path) if file_path else get_app_data_path(self.DEFAULT_FILE)
        self._keys: Dict[str, str] = {}
        self._crypto = CharCryptoTool()
        self._load()
    
    def _encrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            encrypted = self._crypto.shift_encrypt(value, _CRYPTO_KEY)
            return f"{_ENCRYPTED_PREFIX}{encrypted}"
        except Exception:
            return value

    def _decrypt(self, value: str) -> str:
        if not value:
            return ""
        if value.startswith(_ENCRYPTED_PREFIX):
            try:
                return self._crypto.shift_decrypt(
                    value[len(_ENCRYPTED_PREFIX):], _CRYPTO_KEY
                )
            except Exception:
                pass
        return value

    def _load(self) -> None:
        """从文件加载 API Keys"""
        if self.file_path.exists():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._keys = data.get("api_keys", {})
            except Exception:
                self._keys = {}
        else:
            self._keys = {}
    
    def _save(self) -> None:
        """保存 API Keys 到文件"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "2.0",
            "api_keys": self._keys
        }
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get(self, provider: str) -> str:
        """获取提供商的 API Key（解密后）"""
        raw = self._keys.get(provider, "")
        return self._decrypt(raw)
    
    def set(self, provider: str, api_key: str) -> None:
        """设置提供商的 API Key（加密存储）"""
        encrypted = self._encrypt(api_key)
        if encrypted:
            self._keys[provider] = encrypted
        elif provider in self._keys:
            del self._keys[provider]
        self._save()
    
    def remove(self, provider: str) -> None:
        """删除提供商的 API Key"""
        if provider in self._keys:
            del self._keys[provider]
            self._save()
    
    def get_all(self) -> Dict[str, str]:
        """获取所有 API Keys（解密后）"""
        return {k: self._decrypt(v) for k, v in self._keys.items()}
    
    def has_key(self, provider: str) -> bool:
        """检查是否有 API Key"""
        return bool(self._keys.get(provider))
    
    def migrate_from_settings(self, settings_data: dict) -> int:
        """从旧配置迁移 API Keys"""
        migrated = 0
        providers = settings_data.get("providers", {})
        
        for provider_id, provider_config in providers.items():
            api_key = provider_config.get("api_key", "")
            if api_key and not self.has_key(provider_id):
                self.set(provider_id, api_key)
                migrated += 1
        
        return migrated


_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """获取全局 API Key 管理器实例"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
