from typing import Any, Dict, List

from core.settings import AISettingsManager
from core.ai.types import AIModelInfo
from core.api_key_manager import get_api_key_manager


class AISettingsBridge:
    """AI 配置桥接层，适配 AISettingsManager 的字段格式"""

    def __init__(self, settings_manager: AISettingsManager = None):
        self._settings = settings_manager or AISettingsManager()
        self._api_key_manager = get_api_key_manager()

    def get_default_provider(self) -> str:
        return self._settings.get_default_provider()

    def set_default_provider(self, provider: str) -> None:
        self._settings.set_default_provider(provider)

    def get_default_model(self) -> str:
        return self._settings.get_default_model()

    def set_default_model(self, model_id: str) -> None:
        self._settings.set_default_model(model_id)

    def get_models(self) -> List[AIModelInfo]:
        parsed = self._settings.get_models()
        return [AIModelInfo(**item) for item in parsed]

    def save_models(self, models: List[AIModelInfo]) -> None:
        payload = [
            {
                "provider": model.provider,
                "model_id": model.model_id,
                "display_name": model.display_name,
                "enabled": model.enabled,
                "capabilities": model.capabilities,
            }
            for model in models
        ]
        self._settings.save_models(payload)

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        config = self._settings.get_provider_config(provider)
        if config:
            config["api_key"] = self._api_key_manager.get(provider)
        return config
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """设置提供商的 API Key"""
        self._api_key_manager.set(provider, api_key)
    
    def get_api_key(self, provider: str) -> str:
        """获取提供商的 API Key"""
        return self._api_key_manager.get(provider)
