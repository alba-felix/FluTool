import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt5.QtCore import QSettings
from utils.crypto_utils import CharCryptoTool


class SettingsManager:
    """基础设置管理器 - 使用注册表存储通用配置"""
    
    _CRYPTO_KEY = 20260406

    def __init__(self, organization: str = "FluTool", application: str = "App"):
        self._settings = QSettings(organization, application)
        self._crypto = CharCryptoTool()

    def _encrypt_value(self, value: str) -> str:
        if not value:
            return ""
        return self._crypto.shift_encrypt(value, self._CRYPTO_KEY)

    def _decrypt_value(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._crypto.shift_decrypt(value, self._CRYPTO_KEY)
        except Exception:
            return value

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


class FileSettingsManager:
    """文件设置管理器 - 使用 JSON 文件存储配置"""
    
    _CRYPTO_KEY = 20260406
    
    def __init__(self, config_path: Path):
        self._config_path = config_path
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self._crypto = CharCryptoTool()
        self._load()
    
    def _load(self) -> None:
        """从文件加载配置"""
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}
        else:
            self._data = {}
    
    def _save(self) -> None:
        """保存配置到文件"""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def _encrypt_value(self, value: str) -> str:
        if not value:
            return ""
        return self._crypto.shift_encrypt(value, self._CRYPTO_KEY)

    def _decrypt_value(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._crypto.shift_decrypt(value, self._CRYPTO_KEY)
        except Exception:
            return value
    
    def get(self, key: str, default=None):
        """获取配置值，支持点号分隔的键路径"""
        keys = key.split('/')
        data = self._data
        for k in keys:
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return default
        return data
    
    def set(self, key: str, value) -> None:
        """设置配置值，支持点号分隔的键路径"""
        keys = key.split('/')
        data = self._data
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self._save()
    
    def remove(self, key: str) -> None:
        """删除配置值"""
        keys = key.split('/')
        data = self._data
        for k in keys[:-1]:
            if isinstance(data, dict) and k in data:
                data = data[k]
            else:
                return
        if keys[-1] in data:
            del data[keys[-1]]
            self._save()
    
    def contains(self, key: str) -> bool:
        """检查键是否存在"""
        return self.get(key) is not None


class AISettingsManager:
    """AI 配置管理器 - 使用文件存储"""

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
            "default_model": "doubao-seed-1-6-251015",
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
            "default_model": "qwen2.5:7b",
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
            "model_id": "doubao-seed-1-6-251015",
            "display_name": "豆包 Seed 1.6",
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
            "model_id": "qwen2.5:7b",
            "display_name": "Qwen 2.5 7B",
            "enabled": True,
            "capabilities": ["chat"],
        },
    ]

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "ai_settings.json"
        
        self._file_manager = FileSettingsManager(config_path)
        self._provider_templates = self._load_provider_templates()
        self._ensure_defaults()
        self._migrate_from_registry()

    def _load_provider_templates(self) -> Dict[str, Dict[str, Any]]:
        """加载提供商模板（从 ai_providers.json）"""
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

    def _ensure_defaults(self) -> None:
        """确保默认配置存在"""
        # 确保默认提供商设置
        if not self._file_manager.get("default_provider"):
            self._file_manager.set("default_provider", "deepseek")
        
        # 确保默认模型设置
        if not self._file_manager.get("default_model"):
            self._file_manager.set("default_model", "deepseek-chat")
        
        # 确保 providers 配置存在
        if not self._file_manager.get("providers"):
            self._file_manager.set("providers", {})
        
        # 确保 models 配置存在
        if not self._file_manager.get("models"):
            default_models = [m.copy() for m in self.DEFAULT_MODELS]
            self._file_manager.set("models", default_models)
        
        # 为每个提供商设置默认值
        for provider_id, template in self._provider_templates.items():
            prefix = f"providers/{provider_id}"
            if not self._file_manager.get(f"{prefix}/base_url"):
                self._file_manager.set(f"{prefix}/base_url", template.get("base_url", ""))
            if not self._file_manager.get(f"{prefix}/enabled"):
                self._file_manager.set(f"{prefix}/enabled", template.get("enabled", True))
            if not self._file_manager.get(f"{prefix}/default_model"):
                self._file_manager.set(f"{prefix}/default_model", template.get("default_model", ""))
            if not self._file_manager.get(f"{prefix}/timeout_sec"):
                self._file_manager.set(f"{prefix}/timeout_sec", template.get("timeout_sec", 60))
            if not self._file_manager.get(f"{prefix}/extra_headers"):
                self._file_manager.set(f"{prefix}/extra_headers", template.get("custom_headers", {}))

    def _migrate_from_registry(self) -> None:
        """从注册表迁移数据到文件"""
        try:
            registry = QSettings("FluTool", "App")
            
            # 迁移默认提供商
            old_default_provider = registry.value("ai/default_provider", "")
            if old_default_provider and not self._file_manager.get("default_provider"):
                self._file_manager.set("default_provider", old_default_provider)
            
            # 迁移默认模型
            old_default_model = registry.value("ai/default_model", "")
            if old_default_model and not self._file_manager.get("default_model"):
                self._file_manager.set("default_model", old_default_model)
            
            # 迁移提供商配置
            for provider_id in self._provider_templates.keys():
                registry_prefix = f"ai/providers/{provider_id}"
                file_prefix = f"providers/{provider_id}"
                
                # 迁移 API Key（需要解密再加密）
                old_api_key = registry.value(f"{registry_prefix}/api_key", "")
                if old_api_key and not self._file_manager.get(f"{file_prefix}/api_key"):
                    try:
                        # 尝试解密旧的加密值
                        crypto = CharCryptoTool()
                        decrypted = crypto.shift_decrypt(old_api_key, 20260406)
                        self._file_manager.set(f"{file_prefix}/api_key", decrypted)
                    except:
                        # 如果不是加密的，直接保存
                        self._file_manager.set(f"{file_prefix}/api_key", old_api_key)
                
                # 迁移其他字段
                for field in ["base_url", "default_model", "timeout_sec"]:
                    old_value = registry.value(f"{registry_prefix}/{field}", "")
                    if old_value and not self._file_manager.get(f"{file_prefix}/{field}"):
                        self._file_manager.set(f"{file_prefix}/{field}", old_value)
                
                # 迁移 enabled
                old_enabled = registry.value(f"{registry_prefix}/enabled", "")
                if old_enabled and not self._file_manager.get(f"{file_prefix}/enabled"):
                    self._file_manager.set(f"{file_prefix}/enabled", old_enabled.lower() == "true")
                
                # 迁移 extra_headers
                old_headers = registry.value(f"{registry_prefix}/extra_headers_json", "")
                if old_headers and not self._file_manager.get(f"{file_prefix}/extra_headers"):
                    try:
                        headers = json.loads(old_headers)
                        self._file_manager.set(f"{file_prefix}/extra_headers", headers)
                    except:
                        pass
            
            # 迁移模型列表
            old_models = registry.value("ai/models/catalog_json", "")
            if old_models:
                try:
                    models = json.loads(old_models)
                    if models and not self._file_manager.get("models"):
                        self._file_manager.set("models", models)
                except:
                    pass
                    
        except Exception as e:
            print(f"迁移注册表数据失败: {e}")

    @staticmethod
    def _to_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def get_default_provider(self) -> str:
        value = str(self._file_manager.get("default_provider", "")).strip()
        if value:
            return value
        for provider_id, config in self._provider_templates.items():
            if self._to_bool(config.get("is_default", False), False):
                return provider_id
        return "deepseek"

    def set_default_provider(self, provider: str) -> None:
        self._file_manager.set("default_provider", provider)

    def get_default_model(self) -> str:
        value = str(self._file_manager.get("default_model", "")).strip()
        if value:
            return value
        default_provider = self.get_default_provider()
        provider_config = self.get_provider_config(default_provider)
        return str(provider_config.get("default_model", "deepseek-chat"))

    def set_default_model(self, model_id: str) -> None:
        self._file_manager.set("default_model", model_id)

    def get_models(self) -> List[Dict[str, Any]]:
        models = self._file_manager.get("models", [])
        if not models:
            return [m.copy() for m in self.DEFAULT_MODELS]
        return models

    def save_models(self, models: List[Dict[str, Any]]) -> None:
        self._file_manager.set("models", models)

    def list_providers(self) -> List[Dict[str, Any]]:
        providers = []
        for provider_id in self._provider_templates.keys():
            providers.append(self.get_provider_config(provider_id))
        return providers

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        template = self._provider_templates.get(provider, {})
        prefix = f"providers/{provider}"
        
        extra_headers = self._file_manager.get(f"{prefix}/extra_headers", {})
        if not isinstance(extra_headers, dict):
            extra_headers = {}
        
        timeout_sec = self._file_manager.get(f"{prefix}/timeout_sec", template.get("timeout_sec", 60))
        try:
            timeout_sec = int(timeout_sec)
        except:
            timeout_sec = 60

        return {
            "provider_id": provider,
            "name": str(template.get("name", provider)),
            "provider_type": str(template.get("provider_type", provider)),
            "base_url": str(self._file_manager.get(f"{prefix}/base_url", template.get("base_url", ""))),
            "api_key": str(self._file_manager.get(f"{prefix}/api_key", "")).strip(),
            "default_model": str(
                self._file_manager.get(f"{prefix}/default_model", template.get("default_model", ""))
            ).strip(),
            "enabled": self._to_bool(
                self._file_manager.get(f"{prefix}/enabled", template.get("enabled", True)), 
                True
            ),
            "timeout_sec": timeout_sec,
            "extra_headers": extra_headers,
            "extra_headers_json": json.dumps(extra_headers, ensure_ascii=False),
            "models": template.get("models", []),
        }

    def save_provider_config(self, provider: str, config: Dict[str, Any]) -> None:
        prefix = f"providers/{provider}"
        if "base_url" in config:
            self._file_manager.set(f"{prefix}/base_url", str(config.get("base_url", "")))
        if "api_key" in config:
            self._file_manager.set(f"{prefix}/api_key", str(config.get("api_key", "")).strip())
        if "enabled" in config:
            self._file_manager.set(f"{prefix}/enabled", self._to_bool(config.get("enabled"), True))
        if "default_model" in config:
            self._file_manager.set(f"{prefix}/default_model", str(config.get("default_model", "")).strip())
        if "timeout_sec" in config:
            try:
                timeout_value = int(config.get("timeout_sec", 60))
            except:
                timeout_value = 60
            self._file_manager.set(f"{prefix}/timeout_sec", timeout_value)
        if "extra_headers" in config:
            headers = config.get("extra_headers", {})
            if isinstance(headers, dict):
                self._file_manager.set(f"{prefix}/extra_headers", headers)
