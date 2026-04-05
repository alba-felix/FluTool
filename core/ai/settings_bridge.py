from typing import Any, Dict, List

from core.settings import AISettingsManager
from core.ai.types import AIModelInfo


class AISettingsBridge:
    """AI 配置桥接层，统一管理 QSettings 键"""

    def __init__(self, settings_manager: AISettingsManager = None):
        self._settings = settings_manager or AISettingsManager()

    def get_default_provider(self) -> str:
        return str(self._settings.get("ai/default_provider", "deepseek"))

    def set_default_provider(self, provider: str) -> None:
        self._settings.set("ai/default_provider", provider)

    def get_default_model(self) -> str:
        return str(self._settings.get("ai/default_model", "deepseek-chat"))

    def set_default_model(self, model_id: str) -> None:
        self._settings.set("ai/default_model", model_id)

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
        return self._settings.get_provider_config(provider)
