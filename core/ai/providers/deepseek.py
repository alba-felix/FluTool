"""
DeepSeek AI 提供商适配器
支持 1M 上下文、硬盘缓存、思考模式
"""
import json
import hashlib
import os
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime

import requests

from core.ai.provider_base import AIProviderAdapter
from core.ai.types import AIChatRequest, AIChatResponse


class DeepSeekCacheManager:
    """DeepSeek 上下文缓存管理器 - 硬盘缓存
    
    注意：只缓存单轮对话（无历史上下文），因为：
    1. 多轮对话的消息列表每次都变化，无法命中
    2. DeepSeek API 服务端已支持 prefix_cache
    """
    
    DEFAULT_CACHE_DIR = "data/ai_cache/deepseek"
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or self.DEFAULT_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self.cache_dir / "cache_index.json"
        self._load_index()
    
    def _load_index(self):
        """加载缓存索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    self._index = json.load(f)
            except Exception:
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self):
        """保存缓存索引"""
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)
    
    def _compute_cache_key(self, user_message: str, model: str, system_prompt: str = "") -> str:
        """计算缓存键 - 基于单轮消息"""
        cache_input = f"{model}:{system_prompt}:{user_message}"
        return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()[:32]
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def should_use_cache(self, messages: List[Dict[str, str]]) -> bool:
        """判断是否应该使用缓存 - 只缓存单轮对话"""
        user_messages = [m for m in messages if m.get("role") == "user"]
        return len(user_messages) == 1
    
    def get_cached_response(self, messages: List[Dict[str, str]], model: str) -> Optional[Dict[str, Any]]:
        """获取缓存的响应 - 只对单轮对话生效"""
        if not self.should_use_cache(messages):
            return None
        
        user_message = ""
        system_prompt = ""
        for m in messages:
            if m.get("role") == "user":
                user_message = m.get("content", "")
            elif m.get("role") == "system":
                system_prompt = m.get("content", "")
        
        if not user_message:
            return None
        
        cache_key = self._compute_cache_key(user_message, model, system_prompt)
        cache_file = self._get_cache_file(cache_key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            cache_entry = self._index.get(cache_key, {})
            cache_entry["last_hit"] = datetime.now().isoformat()
            cache_entry["hit_count"] = cache_entry.get("hit_count", 0) + 1
            self._index[cache_key] = cache_entry
            self._save_index()
            
            return cached.get("response")
        except Exception:
            return None
    
    def save_response(self, messages: List[Dict[str, str]], model: str, response: Dict[str, Any]):
        """保存响应到缓存 - 只缓存单轮对话"""
        if not self.should_use_cache(messages):
            return
        
        user_message = ""
        system_prompt = ""
        for m in messages:
            if m.get("role") == "user":
                user_message = m.get("content", "")
            elif m.get("role") == "system":
                system_prompt = m.get("content", "")
        
        if not user_message:
            return
        
        cache_key = self._compute_cache_key(user_message, model, system_prompt)
        cache_file = self._get_cache_file(cache_key)
        
        cache_data = {
            "model": model,
            "user_message": user_message,
            "system_prompt": system_prompt,
            "response": response,
            "created_at": datetime.now().isoformat(),
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
        self._index[cache_key] = {
            "created_at": cache_data["created_at"],
            "hit_count": 0,
        }
        self._save_index()
    
    def clear_cache(self):
        """清空缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file != self._index_file:
                cache_file.unlink()
        self._index = {}
        self._save_index()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_hits = sum(entry.get("hit_count", 0) for entry in self._index.values())
        return {
            "total_entries": len(self._index),
            "total_hits": total_hits,
            "cache_dir": str(self.cache_dir),
        }


class DeepSeekAdapter(AIProviderAdapter):
    """DeepSeek 适配器 - 支持 1M 上下文、硬盘缓存、思考模式"""
    
    provider_name = "deepseek"
    
    SUPPORTED_MODELS = {
        "deepseek-chat": {"context": 64000, "description": "通用对话模型"},
        "deepseek-reasoner": {"context": 64000, "description": "推理增强模型"},
        "deepseek-v4-pro": {"context": 1000000, "description": "1M 上下文模型"},
    }
    
    def __init__(self):
        self._cache_manager = DeepSeekCacheManager()
    
    def get_max_context(self, model_id: str) -> int:
        """获取模型最大上下文长度"""
        model_info = self.SUPPORTED_MODELS.get(model_id, {})
        return model_info.get("context", 64000)
    
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
        base_url = str(provider_config.get("base_url", "https://api.deepseek.com")).strip()
        api_key = str(provider_config.get("api_key", "")).strip()
        timeout_sec = int(provider_config.get("timeout_sec", request.timeout_sec))
        
        if not api_key:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error="DeepSeek API Key 为空",
            )
        
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        messages = self._build_messages(request)
        
        payload = {
            "model": request.model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        
        if request.model_id == "deepseek-v4-pro":
            payload["max_tokens"] = min(request.max_tokens or 4096, 4096)
        
        thinking_config = provider_config.get("thinking", {})
        if thinking_config.get("enabled"):
            payload["thinking"] = {"type": "enabled"}
            if thinking_config.get("reasoning_effort"):
                payload["reasoning_effort"] = thinking_config["reasoning_effort"]
        
        if provider_config.get("web_search"):
            payload["web_search"] = True
        
        if provider_config.get("prefix_cache", True):
            payload["prefix_cache"] = {"type": "enabled"}
        
        full_content = ""
        reasoning_content = ""
        finish_reason = "stop"
        error_msg = ""
        response = None
        cache_hit = False
        
        try:
            if provider_config.get("enable_disk_cache", True):
                cached = self._cache_manager.get_cached_response(messages, request.model_id)
                if cached:
                    cache_hit = True
                    full_content = cached.get("content", "")
                    callback(full_content)
                    return AIChatResponse(
                        provider=request.provider,
                        model_id=request.model_id,
                        content=full_content,
                        finish_reason="stop",
                        provider_meta={"cache_hit": True, "source": "disk_cache"},
                    )
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=(5, timeout_sec),
                stream=True,
            )
            
            if response.status_code >= 400:
                error_text = response.text[:500]
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error=f"请求失败({response.status_code}): {error_text}",
                    provider_meta={"status_code": response.status_code},
                )
            
            response.encoding = 'utf-8'
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
                            
                            reasoning_chunk = delta.get("reasoning_content")
                            if reasoning_chunk:
                                reasoning_content += reasoning_chunk
                            
                            content_chunk = delta.get("content") or ""
                            if content_chunk:
                                full_content += content_chunk
                                callback(full_content)
                            
                            finish_reason = choices[0].get("finish_reason") or finish_reason
                    except json.JSONDecodeError:
                        continue
            
            if provider_config.get("enable_disk_cache", True) and full_content:
                self._cache_manager.save_response(
                    messages, request.model_id,
                    {"content": full_content, "reasoning": reasoning_content}
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
        
        return AIChatResponse(
            provider=request.provider,
            model_id=request.model_id,
            content=full_content,
            finish_reason=finish_reason,
            provider_meta={
                "endpoint": endpoint,
                "cache_hit": cache_hit,
                "reasoning_content": reasoning_content if reasoning_content else None,
            },
        )
    
    def chat(self, request: AIChatRequest) -> AIChatResponse:
        """非流式聊天请求"""
        if not request.messages:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                finish_reason="stop",
                error="没有可发送的消息",
            )
        
        provider_config = request.provider_config or {}
        base_url = str(provider_config.get("base_url", "https://api.deepseek.com")).strip()
        api_key = str(provider_config.get("api_key", "")).strip()
        timeout_sec = int(provider_config.get("timeout_sec", request.timeout_sec))
        
        if not api_key:
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content="",
                error="DeepSeek API Key 为空",
            )
        
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        messages = self._build_messages(request)
        
        payload = {
            "model": request.model_id,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        
        if request.model_id == "deepseek-v4-pro":
            payload["max_tokens"] = min(request.max_tokens or 4096, 4096)
        
        thinking_config = provider_config.get("thinking", {})
        if thinking_config.get("enabled"):
            payload["thinking"] = {"type": "enabled"}
            if thinking_config.get("reasoning_effort"):
                payload["reasoning_effort"] = thinking_config["reasoning_effort"]
        
        if provider_config.get("web_search"):
            payload["web_search"] = True
        
        if provider_config.get("prefix_cache", True):
            payload["prefix_cache"] = {"type": "enabled"}
        
        cache_hit = False
        
        try:
            if provider_config.get("enable_disk_cache", True):
                cached = self._cache_manager.get_cached_response(messages, request.model_id)
                if cached:
                    cache_hit = True
                    return AIChatResponse(
                        provider=request.provider,
                        model_id=request.model_id,
                        content=cached.get("content", ""),
                        finish_reason="stop",
                        provider_meta={"cache_hit": True, "source": "disk_cache"},
                    )
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=(5, timeout_sec),
            )
            
            if response.status_code >= 400:
                error_text = response.text[:500]
                return AIChatResponse(
                    provider=request.provider,
                    model_id=request.model_id,
                    content="",
                    error=f"请求失败({response.status_code}): {error_text}",
                    provider_meta={"status_code": response.status_code},
                )
            
            response.encoding = 'utf-8'
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
            content = str(message.get("content") or "").strip()
            reasoning_content = message.get("reasoning_content") or ""
            finish_reason = str(first_choice.get("finish_reason") or "stop")
            usage = data.get("usage")
            
            if provider_config.get("enable_disk_cache", True) and content:
                self._cache_manager.save_response(
                    messages, request.model_id,
                    {"content": content, "reasoning": reasoning_content}
                )
            
            return AIChatResponse(
                provider=request.provider,
                model_id=request.model_id,
                content=content,
                finish_reason=finish_reason,
                usage=usage,
                provider_meta={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "cache_hit": cache_hit,
                    "reasoning_content": reasoning_content if reasoning_content else None,
                },
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
    
    def _build_messages(self, request: AIChatRequest) -> List[Dict[str, str]]:
        """构建消息列表，支持 1M 上下文"""
        messages = []
        max_context = self.get_max_context(request.model_id)
        
        for message in request.messages:
            role = message.role if message.role in {"system", "user", "assistant"} else "user"
            messages.append({"role": role, "content": message.content})
        
        return messages
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self._cache_manager.get_cache_stats()
    
    def clear_cache(self):
        """清空缓存"""
        self._cache_manager.clear_cache()
