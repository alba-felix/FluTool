"""AI 助手工作线程"""

from PyQt5.QtCore import QThread, pyqtSignal

from core.ai.types import AIMessage


class AIChatWorker(QThread):
    """AI聊天工作线程 - 防止UI阻塞"""

    stream_update = pyqtSignal(str)
    finished_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, chat_service, user_text: str, provider: str, model_id: str, enable_web_search: bool = False, conversation_history: list = None):
        super().__init__()
        self.chat_service = chat_service
        self.user_text = user_text
        self.provider = provider
        self.model_id = model_id
        self.enable_web_search = enable_web_search
        self.conversation_history = conversation_history or []
        self._is_running = True
        self._response = None

    def run(self):
        try:
            def stream_callback(text: str):
                if self._is_running:
                    self.stream_update.emit(text)

            history_messages = None
            if self.conversation_history:
                history_messages = [
                    AIMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", "")
                    )
                    for msg in self.conversation_history
                    if msg.get("role") in ("user", "assistant") and msg.get("content")
                ]

            self._response = self.chat_service.send_message(
                user_text=self.user_text,
                provider=self.provider,
                model_id=self.model_id,
                stream_callback=stream_callback,
                enable_web_search=self.enable_web_search,
                conversation_history=history_messages,
            )

            if self._is_running:
                self.finished_signal.emit(self._response)
        except Exception as e:
            if self._is_running:
                self.error_signal.emit(str(e))

    def stop(self):
        self._is_running = False
        self.wait(1000)


class OllamaModelFetchWorker(QThread):
    """Ollama模型列表获取工作线程 - 防止UI阻塞"""

    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self._is_running = True

    def run(self):
        import requests
        try:
            clean_url = self.base_url.replace("/v1", "").rstrip("/")
            api_url = f"{clean_url}/api/tags"
            response = requests.get(api_url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models if m.get("name")]
                if self._is_running:
                    self.finished_signal.emit(model_names)
            else:
                if self._is_running:
                    self.error_signal.emit(f"HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            if self._is_running:
                self.error_signal.emit("Connection refused")
        except requests.exceptions.Timeout:
            if self._is_running:
                self.error_signal.emit("Timeout")
        except Exception as e:
            if self._is_running:
                self.error_signal.emit(str(e))

    def stop(self):
        self._is_running = False
        self.wait(500)
