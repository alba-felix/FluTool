"""运行时目录和默认文件结构。"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from .utils import get_app_data_path


RUNTIME_DIRS = (
    "config",
    "data",
    "data/icons",
    "data/app_icons",
    "data/img",
    "data/ai_cache",
    "data/ai_cache/deepseek",
    "data/temp_text",
)


DEFAULT_CONFIG: Dict[str, Any] = {
    "Backup": {
        "AutoBackupEnabled": False,
        "AutoBackupPath": "",
    },
    "General": {
        "AutoSave": True,
        "EfficiencyMode": False,
    },
    "QFluentWidgets": {
        "FontFamilies": [
            "Segoe UI",
            "Microsoft YaHei",
            "PingFang SC",
        ],
        "ThemeColor": "#ff0078d4",
        "ThemeMode": "Auto",
    },
    "Navigation": {
        "Expanded": False,
    },
    "Window": {
        "Height": 700,
        "Width": 1000,
    },
}


DEFAULT_AI_PROVIDERS = {
    "providers": [
        {
            "provider_id": "siliconflow",
            "name": "硅基流动",
            "provider_type": "siliconflow",
            "base_url": "https://api.siliconflow.cn/v1",
            "api_key": "",
            "default_model": "Qwen/Qwen2.5-7B-Instruct",
            "enabled": True,
            "is_default": False,
            "timeout_sec": 60,
            "custom_headers": {},
            "models": [
                "Qwen/Qwen2.5-7B-Instruct",
                "Qwen/Qwen3-8B",
                "THUDM/glm-4-9b-chat",
                "Qwen/Qwen2.5-Coder-7B-Instruct",
                "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
                "THUDM/GLM-4.1V-9B-Thinking",
                "deepseek-ai/DeepSeek-OCR",
                "PaddlePaddle/PaddleOCR-VL",
                "BAAI/bge-m3",
                "BAAI/bge-large-zh-v1.5",
            ],
        },
        {
            "provider_id": "deepseek",
            "name": "DeepSeek",
            "provider_type": "deepseek",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "default_model": "deepseek-chat",
            "enabled": True,
            "is_default": True,
            "timeout_sec": 120,
            "custom_headers": {},
            "models": ["deepseek-chat", "deepseek-reasoner", "deepseek-v4-pro"],
            "features": {
                "prefix_cache": True,
                "enable_disk_cache": True,
                "web_search": False,
                "thinking": {
                    "enabled": False,
                    "reasoning_effort": "high",
                },
            },
            "model_info": {
                "deepseek-chat": {
                    "context": 64000,
                    "description": "通用对话模型，支持 64K 上下文",
                },
                "deepseek-reasoner": {
                    "context": 64000,
                    "description": "推理增强模型，支持深度思考",
                },
                "deepseek-v4-pro": {
                    "context": 1000000,
                    "description": "1M 上下文模型，支持超长对话",
                },
            },
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
            "models": [
                "doubao-seedance-1-0-pro-fast-251015",
                "doubao-seedream-4-0-250828",
                "doubao-seed-1-6-251015",
            ],
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
            "models": ["qwen-plus"],
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
            "models": ["qwen2.5:7b"],
        },
        {
            "provider_id": "ollama_cloud",
            "name": "Ollama Cloud",
            "provider_type": "ollama_cloud",
            "base_url": "https://ollama.com/v1",
            "api_key": "",
            "default_model": "qwen3.5:397b-cloud",
            "enabled": True,
            "is_default": False,
            "timeout_sec": 120,
            "custom_headers": {},
            "models": [
                "gpt-oss:20b",
                "gpt-oss:120b",
                "gemma4:31b",
                "qwen3.5:397b-cloud",
            ],
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
            "models": ["gpt-4o-mini"],
        },
    ]
}


DEFAULT_AI_SETTINGS = {
    "version": "1.0",
    "default_provider": "deepseek",
    "default_model": "deepseek-chat",
    "providers": {
        "siliconflow": {
            "base_url": "https://api.siliconflow.cn/v1",
            "default_model": "Qwen/Qwen2.5-7B-Instruct",
            "enabled": True,
            "timeout_sec": 60,
            "extra_headers": {},
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com",
            "default_model": "deepseek-chat",
            "enabled": True,
            "timeout_sec": 120,
            "extra_headers": {},
        },
        "doubao": {
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "default_model": "doubao-seed-1-6-251015",
            "enabled": True,
            "timeout_sec": 60,
            "extra_headers": {},
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "default_model": "qwen-plus",
            "enabled": True,
            "timeout_sec": 60,
            "extra_headers": {},
        },
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "qwen2.5:7b",
            "enabled": True,
            "timeout_sec": 60,
            "extra_headers": {},
        },
        "ollama_cloud": {
            "base_url": "https://ollama.com/v1",
            "default_model": "qwen3.5:397b-cloud",
            "enabled": True,
            "timeout_sec": 120,
            "extra_headers": {},
        },
        "custom": {
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "enabled": False,
            "timeout_sec": 60,
            "extra_headers": {},
        },
    },
    "models": [
        {
            "provider": "siliconflow",
            "model_id": "Qwen/Qwen2.5-7B-Instruct",
            "display_name": "Qwen 2.5 7B (免费)",
            "enabled": True,
            "capabilities": ["chat"],
        },
        {
            "provider": "siliconflow",
            "model_id": "Qwen/Qwen3-8B",
            "display_name": "Qwen 3 8B (免费)",
            "enabled": True,
            "capabilities": ["chat"],
        },
        {
            "provider": "siliconflow",
            "model_id": "Qwen/Qwen2.5-Coder-7B-Instruct",
            "display_name": "Qwen 2.5 Coder 7B (免费)",
            "enabled": True,
            "capabilities": ["chat", "code"],
        },
        {
            "provider": "deepseek",
            "model_id": "deepseek-chat",
            "display_name": "DeepSeek Chat",
            "enabled": True,
            "capabilities": ["chat"],
        },
        {
            "provider": "deepseek",
            "model_id": "deepseek-reasoner",
            "display_name": "DeepSeek Reasoner",
            "enabled": True,
            "capabilities": ["chat", "reasoning"],
        },
        {
            "provider": "deepseek",
            "model_id": "deepseek-v4-pro",
            "display_name": "DeepSeek V4 Pro (1M上下文)",
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
        {
            "provider": "ollama_cloud",
            "model_id": "qwen3.5:397b-cloud",
            "display_name": "Qwen 3.5 397B (Ollama Cloud)",
            "enabled": True,
            "capabilities": ["chat"],
        },
    ],
}


RUNTIME_JSON_FILES: Dict[str, Any] = {
    "config/config.json": DEFAULT_CONFIG,
    "config/ai_providers.json": DEFAULT_AI_PROVIDERS,
    "config/ai_settings.json": DEFAULT_AI_SETTINGS,
    "config/local_api_key.json": {
        "version": "1.0",
        "api_keys": {},
    },
    "config/time_lock_data.json": {
        "encrypted_password": "",
        "unlock_timestamp": 0,
    },
    "data/app_launcher_view.json": {
        "view_mode": "grid",
        "icon_size": 24,
    },
    "data/clipboard.json": [],
    "data/folder_tree_rules.json": {},
    "data/folder_tree_config.json": {
        "scan_depth": -1,
    },
    "data/quick_copy.json": {
        "cards": [],
    },
    "data/todos.json": {
        "todos": [],
    },
    "data/img/image_list.json": [],
    "data/ai_cache/deepseek/cache_index.json": {
        "entries": {},
    },
}


def _write_json_if_missing(path: Path, payload: Any) -> None:
    """只在文件不存在时写入默认 JSON，避免覆盖用户数据。"""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(deepcopy(payload), file, ensure_ascii=False, indent=2)


def ensure_runtime_layout() -> None:
    """确保运行时目录、子目录和默认 JSON 文件存在。"""
    for relative_dir in RUNTIME_DIRS:
        get_app_data_path(relative_dir).mkdir(parents=True, exist_ok=True)

    for relative_file, payload in RUNTIME_JSON_FILES.items():
        _write_json_if_missing(get_app_data_path(relative_file), payload)
