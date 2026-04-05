import json
from pathlib import Path
from typing import Any, Dict, List

from PyQt5.QtCore import QSettings


class SettingsManager:
    def __init__(self, organization: str = "FluTool", application: str = "App"):
        self._settings = QSettings(organization, application)

    def get(self, key: str, default=None):
        return self._settings.value(key, default)

    def set(self, key: str, value) -> None:
        self._settings.setValue(key, value)

    def sync(self) -> None:
        self._settings.sync()

    def remove(self, key: str) -> None:
        self._settings.remove(key)

    def contains(self, key: str) -> bool:
        return self._settings.contains(key)


class AISettingsManager(SettingsManager):
    """AI 配置管理器"""

    DEFAULT_PROVIDERS = [
        {
            "provider_id": "deepseek",
            "name": "DeepSeek",
            "provider_type": "deepseek",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "default_model": "deepseek-chat",
            "enabled": True,
            "is_default": True,
            "timeout_sec": 60,
            "custom_headers": {},
        },
        {
            "provider_id": "doubao",
            "name": "豆包",
            "provider_type": "doubao",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "api_key": "",
            "default_model": "doubao-seed-1-6-250615",
            "enabled": True,
            "is_default": False,
            "timeout_sec": 60,
            "custom_headers": {},
        },
        {
            "provider_id": "qwen",
            "name": "Qwen",
            "provider_type": "qwen",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "",
            "default_model": "qwen-plus",
            "enabled": True,
            "is_default": False,
            "timeout_sec": 60,
            "custom_headers": {},
        },
        {
            "provider_id": "ollama",
            "name": "Ollama",
            "provider_type": "ollama",
            "base_url": "http://localhost:11434",
            "api_key": "",
            "default_model": "gemma3",
            "enabled": True,
            "is_default": False,
            "timeout_sec": 60,
            "custom_headers": {},
        },
        {
            "provider_id": "custom",
            "name": "自定义",
            "provider_type": "custom",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "default_model": "gpt-4o-mini",
            "enabled": False,
            "is_default": False,
            "timeout_sec": 60,
            "custom_headers": {},
        },
    ]

    DEFAULT_MODELS = [
        {
            "provider": "deepseek",
            "model_id": "deepseek-chat",
            "display_name": "DeepSeek Chat",
            "enabled": True,
            "capabilities": ["chat"],
        },
        {
            "provider": "doubao",
            "model_id": "doubao-1.5-pro-32k",
            "display_name": "豆包 Pro 32k",
            "enabled": True,
            "capabilities": ["chat"],
        },
        {
            "provider": "qwen",
            "model_id": "qwen-plus",
            "display_name": "Qwen Plus",
            "enabled": True,
            "capabilities": ["chat"],
        },
        {
            "provider": "ollama",
            "model_id": "gemma3",
            "display_name": "Gemma 3",
            "enabled": True,
            "capabilities": ["chat"],
        },
    ]

    def __init__(self, organization: str = "FluTool", application: str = "App"):
        super().__init__(organization, application)
        self._provider_templates = self._load_provider_templates()
        self._seed_provider_defaults()

    def _load_provider_templates(self) -> Dict[str, Dict[str, Any]]:
        config_path = Path(__file__).parent.parent / "config" / "ai_providers.json"
        if not config_path.exists():
            return {item["provider_id"]: item for item in self.DEFAULT_PROVIDERS}

        try:
            raw_text = config_path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            providers = payload.get("providers", [])
            if not isinstance(providers, list):
                return {item["provider_id"]: item for item in self.DEFAULT_PROVIDERS}
            result = {}
            for provider in providers:
                provider_id = provider.get("provider_id", "")
                if not provider_id:
                    continue
                result[provider_id] = provider
            if result:
                return result
        except Exception:
            pass

        return {item["provider_id"]: item for item in self.DEFAULT_PROVIDERS}

    def _seed_provider_defaults(self) -> None:
        for provider_id, config in self._provider_templates.items():
            prefix = f"ai/providers/{provider_id}"
            if not self.contains(f"{prefix}/base_url"):
                self.set(f"{prefix}/base_url", config.get("base_url", ""))
            if not self.contains(f"{prefix}/enabled"):
                self.set(f"{prefix}/enabled", "true" if config.get("enabled", True) else "false")
            if not self.contains(f"{prefix}/extra_headers_json"):
                self.set(
                    f"{prefix}/extra_headers_json",
                    json.dumps(config.get("custom_headers", {}), ensure_ascii=False),
                )
            if not self.contains(f"{prefix}/timeout_sec"):
                self.set(f"{prefix}/timeout_sec", int(config.get("timeout_sec", 60)))
            if not self.contains(f"{prefix}/default_model"):
                self.set(f"{prefix}/default_model", str(config.get("default_model", "")))

        # 迁移：修复 Ollama 旧配置
        self._migrate_ollama_config()
        # 迁移：同步模型列表
        self._migrate_models_catalog()

    def _migrate_ollama_config(self) -> None:
        """迁移 Ollama 旧配置（移除 /v1 后缀）"""
        prefix = "ai/providers/ollama"
        if self.contains(f"{prefix}/base_url"):
            current_url = str(self.get(f"{prefix}/base_url", ""))
            if current_url.endswith("/v1"):
                self.set(f"{prefix}/base_url", current_url[:-3])
        if self.contains(f"{prefix}/default_model"):
            current_model = str(self.get(f"{prefix}/default_model", ""))
            if current_model in ("qwen2.5:7b", "llama3.1"):
                self.set(f"{prefix}/default_model", "gemma3")

    def _migrate_models_catalog(self) -> None:
        """迁移模型列表，添加缺失的提供商模型"""
        current_models = self.get_models()
        current_providers = {m.get("provider") for m in current_models}
        
        # 检查是否有新的默认模型需要添加
        for default_model in self.DEFAULT_MODELS:
            provider = default_model.get("provider")
            if provider not in current_providers:
                current_models.append(default_model.copy())
        
        # 保存更新后的模型列表
        if len(current_models) > len(current_providers):
            self.save_models(current_models)

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _parse_json_object(value: str) -> Dict[str, str]:
        if not value:
            return {}
        try:
            data = json.loads(value)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def get_default_provider(self) -> str:
        value = str(self.get("ai/default_provider", "")).strip()
        if value:
            return value
        for provider_id, config in self._provider_templates.items():
            if self._to_bool(config.get("is_default", False), False):
                return provider_id
        return "deepseek"

    def set_default_provider(self, provider: str) -> None:
        self.set("ai/default_provider", provider)

    def get_default_model(self) -> str:
        value = str(self.get("ai/default_model", "")).strip()
        if value:
            return value
        default_provider = self.get_default_provider()
        provider_config = self.get_provider_config(default_provider)
        return str(provider_config.get("default_model", "deepseek-chat"))

    def set_default_model(self, model_id: str) -> None:
        self.set("ai/default_model", model_id)

    def get_models(self) -> List[Dict[str, Any]]:
        raw_value = self.get("ai/models/catalog_json", "")
        if not raw_value:
            return self.DEFAULT_MODELS.copy()
        try:
            parsed = json.loads(str(raw_value))
            if not isinstance(parsed, list):
                return self.DEFAULT_MODELS.copy()
            return parsed
        except Exception:
            return self.DEFAULT_MODELS.copy()

    def save_models(self, models: List[Dict[str, Any]]) -> None:
        self.set("ai/models/catalog_json", json.dumps(models, ensure_ascii=False))

    def list_providers(self) -> List[Dict[str, Any]]:
        providers = []
        for provider_id in self._provider_templates.keys():
            providers.append(self.get_provider_config(provider_id))
        return providers

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        template = self._provider_templates.get(provider, {})
        prefix = f"ai/providers/{provider}"
        raw_headers = str(
            self.get(
                f"{prefix}/extra_headers_json",
                json.dumps(template.get("custom_headers", {}), ensure_ascii=False),
            )
        )
        timeout_value = self.get(f"{prefix}/timeout_sec", template.get("timeout_sec", 60))
        try:
            timeout_sec = int(timeout_value)
        except Exception:
            timeout_sec = 60

        return {
            "provider_id": provider,
            "name": str(template.get("name", provider)),
            "provider_type": str(template.get("provider_type", provider)),
            "base_url": str(self.get(f"{prefix}/base_url", template.get("base_url", ""))),
            "api_key": str(self.get(f"{prefix}/api_key", template.get("api_key", ""))).strip(),
            "default_model": str(
                self.get(f"{prefix}/default_model", template.get("default_model", ""))
            ).strip(),
            "enabled": self._to_bool(self.get(f"{prefix}/enabled", template.get("enabled", True)), True),
            "timeout_sec": timeout_sec,
            "extra_headers": self._parse_json_object(raw_headers),
            "extra_headers_json": raw_headers,
        }

    def save_provider_config(self, provider: str, config: Dict[str, Any]) -> None:
        prefix = f"ai/providers/{provider}"
        if "base_url" in config:
            self.set(f"{prefix}/base_url", str(config.get("base_url", "")))
        if "api_key" in config:
            self.set(f"{prefix}/api_key", str(config.get("api_key", "")).strip())
        if "enabled" in config:
            self.set(f"{prefix}/enabled", "true" if self._to_bool(config.get("enabled"), True) else "false")
        if "default_model" in config:
            self.set(f"{prefix}/default_model", str(config.get("default_model", "")).strip())
        if "timeout_sec" in config:
            try:
                timeout_value = int(config.get("timeout_sec", 60))
            except Exception:
                timeout_value = 60
            self.set(f"{prefix}/timeout_sec", timeout_value)
        if "extra_headers" in config:
            headers = config.get("extra_headers", {})
            if isinstance(headers, dict):
                self.set(
                    f"{prefix}/extra_headers_json",
                    json.dumps(headers, ensure_ascii=False),
                )
