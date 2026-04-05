from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AIModelInfo:
    """模型元信息"""

    provider: str
    model_id: str
    display_name: str
    enabled: bool = True
    capabilities: List[str] = field(default_factory=list)


@dataclass
class AIMessage:
    """统一消息结构"""

    role: str
    content: str
    tool_name: str = ""
    tool_payload: str = ""


@dataclass
class AIChatRequest:
    """统一聊天请求"""

    provider: str
    model_id: str
    messages: List[AIMessage]
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = True
    timeout_sec: int = 30
    provider_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIChatResponse:
    """统一聊天响应"""

    provider: str
    model_id: str
    content: str
    finish_reason: str = "stop"
    usage: Optional[Dict[str, int]] = None
    provider_meta: Optional[Dict[str, Any]] = None
    error: str = ""
