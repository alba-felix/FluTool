import json
import requests
from typing import Callable

from core.ai.provider_base import AIProviderAdapter
from core.ai.types import AIChatRequest, AIChatResponse


class OpenAICompatibleAdapter(AIProviderAdapter):
    """OpenAI-compatible 适配器"""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def chat_stream(
        self, request: AIChatRequest, callback: Callable[[str], None]
    ) -> AIChatResponse:
        """流式聊天请求"""
        if not request.messages:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                finish_reason="stop",
                error="没有可发送的消息",
            )

        provider_config = request.provider_config or {}
        base_url = str(provider_config.get("base_url", "")).strip()
        api_key = str(provider_config.get("api_key", "")).strip()
        timeout_sec = int(provider_config.get("timeout_sec", request.timeout_sec))
        extra_headers = provider_config.get("extra_headers", {})
        if not base_url:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error=f"{request.provider} 的 API 地址为空",
            )

        endpoint = self._build_endpoint(base_url)
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if isinstance(extra_headers, dict):
            headers.update({str(k): str(v) for k, v in extra_headers.items()})

        messages = []
        for message in request.messages:
            role = message.role if message.role in {"system", "user", "assistant"} else "user"
            messages.append({"role": role, "content": message.content})

        payload = {
            "model": request.model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        # 支持 web_search（如 deepseek-reasoner）
        if request.provider_config.get("web_search"):
            payload["web_search"] = True

        full_content = ""
        finish_reason = "stop"
        error_msg = ""

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=timeout_sec,
                stream=True,
            )
            if response.status_code >= 400:
                error_text = response.text[:300]
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error=f"请求失败({response.status_code}): {error_text}",
                    provider_meta={"status_code": response.status_code},
                )

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content_chunk = delta.get("content", "")
                            if content_chunk:
                                full_content += content_chunk
                                callback(full_content)
                            finish_reason = choices[0].get("finish_reason", finish_reason)
                    except json.JSONDecodeError:
                        continue

        except requests.RequestException as exc:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content=full_content,
                error=f"网络请求异常: {exc}",
                provider_meta={"endpoint": endpoint},
            )
        except Exception as exc:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content=full_content,
                error=f"解析响应异常: {exc}",
                provider_meta={"endpoint": endpoint},
            )

        return AIChatResponse(
            provider=request.provider,
            model_id=request.model_id,
            content=full_content,
            finish_reason=finish_reason,
            provider_meta={"endpoint": endpoint},
        )

    def chat(self, request: AIChatRequest) -> AIChatResponse:
        if not request.messages:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                finish_reason="stop",
                error="没有可发送的消息",
            )

        provider_config = request.provider_config or {}
        base_url = str(provider_config.get("base_url", "")).strip()
        api_key = str(provider_config.get("api_key", "")).strip()
        timeout_sec = int(provider_config.get("timeout_sec", request.timeout_sec))
        extra_headers = provider_config.get("extra_headers", {})
        if not base_url:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error=f"{request.provider} 的 API 地址为空",
            )

        endpoint = self._build_endpoint(base_url)
        headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        if isinstance(extra_headers, dict):
            headers.update({str(k): str(v) for k, v in extra_headers.items()})

        messages = []
        for message in request.messages:
            role = message.role if message.role in {"system", "user", "assistant"} else "user"
            messages.append({"role": role, "content": message.content})

        payload = {
            "model": request.model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=timeout_sec,
            )
            if response.status_code >= 400:
                error_text = response.text[:300]
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error=f"请求失败({response.status_code}): {error_text}",
                    provider_meta={"status_code": response.status_code},
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error="上游返回为空 choices",
                    provider_meta={"raw": data},
                )

            first_choice = choices[0]
            message = first_choice.get("message", {})
            content = str(message.get("content", "")).strip()
            finish_reason = str(first_choice.get("finish_reason", "stop"))
            usage = data.get("usage")
            if not isinstance(usage, dict):
                usage = None

            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content=content,
                finish_reason=finish_reason,
                usage=usage,
                provider_meta={"endpoint": endpoint, "status_code": response.status_code},
            )
        except requests.RequestException as exc:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error=f"网络请求异常: {exc}",
                provider_meta={"endpoint": endpoint},
            )
        except Exception as exc:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error=f"解析响应异常: {exc}",
                provider_meta={"endpoint": endpoint},
            )

    @staticmethod
    def _build_endpoint(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return f"{normalized}/chat/completions"
