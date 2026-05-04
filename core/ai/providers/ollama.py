import json
import requests
from typing import Callable

from core.ai.provider_base import AIProviderAdapter
from core.ai.types import AIChatRequest, AIChatResponse


class OllamaAdapter(AIProviderAdapter):
    """Ollama 适配器
    
    API 文档: https://docs.ollama.com/api/chat
    Base URL: http://localhost:11434
    端点: /api/chat
    """
    
    provider_name = "ollama"
    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "gemma3"

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
        base_url = str(provider_config.get("base_url", "")).strip() or self.DEFAULT_BASE_URL
        # Ollama 原生 API 不使用 /v1 前缀，移除它
        base_url = base_url.replace("/v1", "").rstrip("/")
        timeout_sec = int(provider_config.get("timeout_sec", request.timeout_sec))

        endpoint = f"{base_url}/api/chat"

        messages = []
        for message in request.messages:
            role = message.role if message.role in {"system", "user", "assistant"} else "user"
            messages.append({"role": role, "content": message.content})

        model_id = request.model_id or self.DEFAULT_MODEL

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": True,
        }

        full_content = ""
        response = None

        try:
            response = requests.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=(5, timeout_sec),
                stream=True,
            )
            if response.status_code == 404:
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error=f"Ollama 服务未运行或模型 '{model_id}' 未下载。请运行: ollama pull {model_id}",
                    provider_meta={"status_code": 404, "endpoint": endpoint},
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
                try:
                    data = json.loads(line)
                    message = data.get("message", {})
                    content_chunk = message.get("content", "")
                    if content_chunk:
                        full_content += content_chunk
                        callback(full_content)
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

            if not full_content:
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error="Ollama 返回空内容",
                )

            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content=full_content,
                finish_reason="stop",
                provider_meta={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                },
            )
        except requests.exceptions.ConnectionError:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error=f"无法连接 Ollama 服务 ({base_url})。请确保 Ollama 已启动: ollama serve",
                provider_meta={"endpoint": endpoint},
            )
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
        finally:
            if response is not None:
                response.close()

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
        base_url = str(provider_config.get("base_url", "")).strip() or self.DEFAULT_BASE_URL
        # Ollama 原生 API 不使用 /v1 前缀，移除它
        base_url = base_url.replace("/v1", "").rstrip("/")
        timeout_sec = int(provider_config.get("timeout_sec", request.timeout_sec))

        endpoint = f"{base_url}/api/chat"

        messages = []
        for message in request.messages:
            role = message.role if message.role in {"system", "user", "assistant"} else "user"
            messages.append({"role": role, "content": message.content})

        model_id = request.model_id or self.DEFAULT_MODEL

        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
        }

        try:
            response = requests.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=(5, timeout_sec),
            )
            if response.status_code == 404:
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error=f"Ollama 服务未运行或模型 '{model_id}' 未下载。请运行: ollama pull {model_id}",
                    provider_meta={"status_code": 404, "endpoint": endpoint},
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
            message = data.get("message", {})
            content = str(message.get("content", "")).strip()
            
            if not content:
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error="Ollama 返回空内容",
                    provider_meta={"raw": data},
                )

            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content=content,
                finish_reason="stop",
                provider_meta={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "total_duration": data.get("total_duration"),
                    "eval_count": data.get("eval_count"),
                },
            )
        except requests.exceptions.ConnectionError:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error=f"无法连接 Ollama 服务 ({base_url})。请确保 Ollama 已启动: ollama serve",
                provider_meta={"endpoint": endpoint},
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

    def list_models(self, base_url: str = None) -> list:
        """获取可用模型列表"""
        url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        try:
            response = requests.get(
                f"{url}/api/tags",
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
        except Exception:
            pass
        return []
