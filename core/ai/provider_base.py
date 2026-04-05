from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

from .types import AIChatRequest, AIChatResponse


class AIProviderAdapter(ABC):
    """提供商适配器抽象基类"""

    provider_name: str = "unknown"

    @abstractmethod
    def chat(self, request: AIChatRequest) -> AIChatResponse:
        """发送聊天请求并返回统一响应"""

    def chat_stream(
        self, request: AIChatRequest, callback: Callable[[str], None]
    ) -> AIChatResponse:
        """流式聊天请求，逐块返回内容
        
        默认实现：先获取完整响应，然后逐字回调
        子类可以重写此方法以实现真正的流式传输
        """
        response = self.chat(request)
        if response.content and not response.error:
            # 逐字回调，由UI层控制显示节奏
            for i in range(1, len(response.content) + 1):
                callback(response.content[:i])
        return response


class AIProviderRegistry:
    """提供商注册表"""

    def __init__(self):
        self._adapters: Dict[str, AIProviderAdapter] = {}

    def register(self, adapter: AIProviderAdapter) -> None:
        if adapter is None:
            return
        if not adapter.provider_name:
            return
        self._adapters[adapter.provider_name] = adapter

    def get(self, provider_name: str) -> Optional[AIProviderAdapter]:
        return self._adapters.get(provider_name)

    def contains(self, provider_name: str) -> bool:
        return provider_name in self._adapters

    def all_providers(self):
        return list(self._adapters.keys())
