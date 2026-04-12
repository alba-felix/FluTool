from typing import Callable, List, Optional

from core.ai.provider_base import AIProviderRegistry
from core.ai.providers import OpenAICompatibleAdapter, OllamaAdapter
from core.ai.settings_bridge import AISettingsBridge
from core.ai.types import AIChatRequest, AIChatResponse, AIMessage
from core.ai.search_bridge import AISearchBridge


# 支持 web_search 的模型列表
WEB_SEARCH_MODELS = {
    "deepseek": ["deepseek-reasoner"],  # deepseek 支持搜索的模型
    "doubao": [],  # 豆包暂无
    "qwen": [],  # 通义暂无
    "custom": [],
    "ollama": [],
}


class AIChatService:
    """AI 聊天服务骨架"""

    def __init__(self, settings_bridge: AISettingsBridge, search_bridge: AISearchBridge = None):
        self._settings_bridge = settings_bridge
        self._search_bridge = search_bridge
        self._registry = AIProviderRegistry()
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        self._registry.register(OllamaAdapter())
        for provider_name in ["siliconflow", "ollama_cloud", "deepseek", "doubao", "qwen", "custom"]:
            self._registry.register(OpenAICompatibleAdapter(provider_name))

    def supports_web_search(self, provider: str, model_id: str) -> bool:
        """判断模型是否支持 web_search"""
        provider_models = WEB_SEARCH_MODELS.get(provider, [])
        return model_id in provider_models

    def get_enabled_models(self):
        models = self._settings_bridge.get_models()
        enabled_models = []
        for model in models:
            if not model.enabled:
                continue
            provider_config = self._settings_bridge.get_provider_config(model.provider)
            if not provider_config.get("enabled", True):
                continue
            enabled_models.append(model)
        return enabled_models

    def send_message(
        self,
        user_text: str,
        provider: Optional[str] = None,
        model_id: Optional[str] = None,
        stream_callback: Optional[Callable[[str], None]] = None,
        enable_web_search: bool = False,
    ) -> AIChatResponse:
        if not user_text or not user_text.strip():
            return AIChatResponse(provider="", model_id="", content="", error="消息为空")

        selected_provider = provider or self._settings_bridge.get_default_provider()
        selected_model = model_id or self._settings_bridge.get_default_model()
        provider_config = self._settings_bridge.get_provider_config(selected_provider)
        if not provider_config.get("enabled", True):
            return AIChatResponse(
                provider=selected_provider,
                model_id=selected_model,
                content="",
                error=f"提供商 {selected_provider} 未启用",
            )

        api_key = str(provider_config.get("api_key", "")).strip()
        is_key_optional = selected_provider in {"ollama", "ollama_cloud"}
        if not api_key and not is_key_optional:
            return AIChatResponse(
                provider=selected_provider,
                model_id=selected_model,
                content="",
                error=f"请先在设置中填写 {selected_provider} 的 API Key",
            )

        adapter = self._registry.get(selected_provider)
        if adapter is None:
            return AIChatResponse(
                provider=selected_provider,
                model_id=selected_model,
                content="",
                error=f"未找到提供商适配器: {selected_provider}",
            )

        messages: List[AIMessage] = []
        clean_text = user_text.strip()
        messages.append(AIMessage(role="user", content=clean_text))

        if clean_text.startswith("@搜索 "):
            query = clean_text.replace("@搜索 ", "", 1).strip()
            search_context = self._search_bridge.search_context(query) if self._search_bridge else ""
            if search_context:
                messages.append(
                    AIMessage(
                        role="system",
                        content=f"以下是全局搜索结果:\n{search_context}",
                        tool_name="global_search",
                    )
                )

        # 判断是否启用 web_search
        actual_web_search = False
        if enable_web_search and self.supports_web_search(selected_provider, selected_model):
            actual_web_search = True
            # 在 provider_config 中标记启用 web_search
            provider_config = dict(provider_config)
            provider_config["web_search"] = True

        request = AIChatRequest(
            provider=selected_provider,
            model_id=selected_model,
            messages=messages,
            stream=True,
            timeout_sec=int(provider_config.get("timeout_sec", 30)),
            provider_config=provider_config,
        )

        # 流式处理
        if stream_callback:
            return adapter.chat_stream(request, stream_callback)
        else:
            response = adapter.chat(request)
            return response
