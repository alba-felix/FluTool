"""AI 助手主界面组件"""

import time
from typing import Optional
from collections import deque

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidgetItem,
    QMessageBox,
)
from qfluentwidgets import (
    ComboBox,
    FluentIcon as FIF,
    StrongBodyLabel,
    isDarkTheme,
    RoundMenu,
    Action,
    InfoBar,
    InfoBarPosition,
    qconfig,
)

from core.ai import AIChatService, AISettingsBridge, AISearchBridge
from plugins.ai_assistant.service import AIAssistantService
from .chat_input import ChatInputWidget
from .chat_message import ChatMessageList
from .sidebar import AISidebar
from .workers import AIChatWorker, OllamaModelFetchWorker


class AIAssistantWidget(QWidget):
    """AI 助手插件基础界面"""

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = AIAssistantService()

        self.ai_settings = getattr(core, "ai_settings", AISettingsBridge())
        self.chat_service = getattr(core, "ai_chat_service", None)
        if self.chat_service is None:
            self.chat_service = AIChatService(
                settings_bridge=self.ai_settings,
                search_bridge=AISearchBridge(core.search_manager),
            )

        self.current_conversation_id: Optional[int] = None
        self._setup_ui()
        self._apply_theme_style()

        qconfig.themeChanged.connect(self._on_theme_changed)

        self._initialized = False
        QTimer.singleShot(50, self._delayed_init)

    def _on_theme_changed(self):
        """主题变更统一处理"""
        self._apply_theme_style()
        self.chat_view._on_theme_changed()
        self.chat_input._on_theme_changed()

    def _delayed_init(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._load_provider_and_models()
        QTimer.singleShot(50, self._load_or_create_conversation)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_from_settings()

    def _refresh_from_settings(self) -> None:
        current_provider = self.provider_combo.currentText()
        current_model = self.model_combo.currentText()

        self._load_provider_and_models()

        provider_index = self.provider_combo.findText(current_provider)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        else:
            default_provider = self.ai_settings.get_default_provider()
            idx = self.provider_combo.findText(default_provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)

        model_index = self.model_combo.findText(current_model)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)

    def _setup_ui(self) -> None:
        self.setObjectName("aiAssistantWidget")
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._sidebar = AISidebar(self)
        self._sidebar.setObjectName("aiSidebar")
        self._sidebar.setNewChatCallback(self._create_conversation)
        self._sidebar.history_list.itemClicked.connect(self._on_conversation_selected)
        self._sidebar.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._sidebar.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
        self._sidebar.search_requested.connect(self._on_search_conversations)
        self._sidebar.clear_search_requested.connect(self._on_clear_search)

        root_layout.addWidget(self._sidebar)

        right_widget = QWidget()
        right_widget.setObjectName("aiRightPanel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        top_bar = QHBoxLayout()
        self.provider_combo = ComboBox(self)
        self.model_combo = ComboBox(self)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        top_bar.addWidget(StrongBodyLabel("厂商"))
        top_bar.addWidget(self.provider_combo)
        top_bar.addWidget(StrongBodyLabel("模型"))
        top_bar.addWidget(self.model_combo)
        top_bar.addStretch()
        right_layout.addLayout(top_bar)

        self.chat_view = ChatMessageList(self)
        right_layout.addWidget(self.chat_view, 1)

        self.chat_input = ChatInputWidget(self)
        self.chat_input.send_clicked.connect(self._on_chat_send)
        self.chat_input.stop_clicked.connect(self._on_stop_generation)
        right_layout.addWidget(self.chat_input)

        root_layout.addWidget(right_widget, 1)

        self._chat_worker: Optional[AIChatWorker] = None
        self._ollama_fetch_worker: Optional[OllamaModelFetchWorker] = None
        self._current_ai_bubble = None
        self._stream_timer = None
        self._text_queue = None
        self._pending_ollama_default_model = ""

    def _apply_theme_style(self) -> None:
        dark = isDarkTheme()
        text_color = "#ffffff" if dark else "#222222"
        hover_bg = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.04)"
        selected_bg = "rgba(0,120,212,0.25)" if dark else "rgba(0,120,212,0.10)"

        self.setStyleSheet(f"""
            #aiAssistantWidget {{
                background: transparent;
            }}
            #aiSidebar {{
                background: transparent;
                border: none;
            }}
            #aiRightPanel {{
                background: transparent;
            }}
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                height: 36px;
                border-radius: 6px;
                padding: 4px 10px;
                color: {text_color};
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background: {hover_bg};
            }}
            QListWidget::item:selected {{
                background: {selected_bg};
                color: #0078d4;
            }}
        """)

    def _show_history_context_menu(self, pos) -> None:
        item = self._sidebar.history_list.itemAt(pos)
        if not item:
            return
        menu = RoundMenu(parent=self)

        rename_action = Action("重命名", self)
        rename_action.triggered.connect(lambda: self._rename_conversation(item))
        menu.addAction(rename_action)

        menu.addSeparator()

        delete_action = Action("删除此会话", self)
        delete_action.triggered.connect(lambda: self._delete_conversation(item))
        menu.addAction(delete_action)
        menu.exec_(self._sidebar.history_list.mapToGlobal(pos))

    def _rename_conversation(self, item: QListWidgetItem) -> None:
        from qfluentwidgets import MessageBoxBase, SubtitleLabel, LineEdit

        conv_id = item.data(Qt.UserRole)
        if conv_id is None:
            return

        conv_id = int(conv_id)
        current_title = item.text()

        class RenameDialog(MessageBoxBase):
            def __init__(self, parent, title):
                super().__init__(parent)
                self.titleLabel = SubtitleLabel("重命名会话", self)
                self.viewLayout.addWidget(self.titleLabel)

                self.input_edit = LineEdit(self)
                self.input_edit.setText(title)
                self.input_edit.setClearButtonEnabled(True)
                self.input_edit.selectAll()
                self.input_edit.returnPressed.connect(self.yesButton.click)
                self.viewLayout.addWidget(self.input_edit)

                self.yesButton.setText("确定")
                self.cancelButton.setText("取消")
                self.widget.setMinimumWidth(300)

            def get_text(self):
                return self.input_edit.text().strip()

        dialog = RenameDialog(self, current_title)
        if dialog.exec():
            new_title = dialog.get_text()
            if new_title and new_title != current_title:
                self.service.update_conversation_title(conv_id, new_title)
                item.setText(new_title)
                item.setToolTip(new_title)

    def _delete_conversation(self, item: QListWidgetItem) -> None:
        conv_id = item.data(Qt.UserRole)
        if conv_id is None:
            return
        conv_id = int(conv_id)
        self.service.delete_conversation(conv_id)
        if self.current_conversation_id == conv_id:
            self.current_conversation_id = None
            self.chat_view.clear_messages()
        self._sidebar.history_list.takeItem(self._sidebar.history_list.row(item))
        if self._sidebar.history_list.count() == 0:
            self._create_conversation()

    def _load_provider_and_models(self) -> None:
        self.provider_combo.clear()
        self.model_combo.clear()

        models = self.chat_service.get_enabled_models()
        if not models:
            self.provider_combo.setPlaceholderText("暂无可用模型")
            self.provider_combo.setEnabled(False)
            self.model_combo.setEnabled(False)
            return

        self.provider_combo.setEnabled(True)
        self.model_combo.setEnabled(True)

        self.provider_combo.addItem("")

        providers = sorted(set(model.provider for model in models))
        for provider in providers:
            self.provider_combo.addItem(provider)

        self.provider_combo.setCurrentIndex(0)
        self.model_combo.clear()
        self.model_combo.setPlaceholderText("请先选择提供商")

    def _refresh_models_for_provider(self, provider: str) -> None:
        self.model_combo.clear()
        if not provider:
            return

        provider_config = self.ai_settings.get_provider_config(provider)
        default_model = provider_config.get("default_model", "")
        models_list = provider_config.get("models", [])

        if provider == "ollama":
            self._pending_ollama_default_model = default_model
            self.model_combo.addItem("加载中...")
            self.model_combo.setEnabled(False)
            self._start_ollama_model_fetch(provider_config.get("base_url", "http://localhost:11434"))
            return

        if models_list:
            for model in models_list:
                self.model_combo.addItem(model)
            if default_model:
                model_index = self.model_combo.findText(default_model)
                if model_index >= 0:
                    self.model_combo.setCurrentIndex(model_index)
            return

        if default_model:
            self.model_combo.addItem(default_model)

        models = self.chat_service.get_enabled_models()
        selected = [m for m in models if m.provider == provider and m.model_id != default_model]
        for model in selected:
            self.model_combo.addItem(model.model_id)

        if default_model:
            model_index = self.model_combo.findText(default_model)
            if model_index >= 0:
                self.model_combo.setCurrentIndex(model_index)

    def _start_ollama_model_fetch(self, base_url: str) -> None:
        if self._ollama_fetch_worker is not None:
            self._ollama_fetch_worker.stop()
            self._ollama_fetch_worker = None

        self._ollama_fetch_worker = OllamaModelFetchWorker(base_url)
        self._ollama_fetch_worker.finished_signal.connect(self._on_ollama_models_fetched)
        self._ollama_fetch_worker.error_signal.connect(self._on_ollama_models_error)
        self._ollama_fetch_worker.start()

    def _on_ollama_models_fetched(self, models: list) -> None:
        self.model_combo.clear()
        self.model_combo.setEnabled(True)

        default_model = self._pending_ollama_default_model

        if models:
            for model in models:
                self.model_combo.addItem(model)
            if default_model:
                model_index = self.model_combo.findText(default_model)
                if model_index >= 0:
                    self.model_combo.setCurrentIndex(model_index)
        elif default_model:
            self.model_combo.addItem(default_model)

        self._ollama_fetch_worker = None

    def _on_ollama_models_error(self, error_msg: str) -> None:
        self.model_combo.clear()
        self.model_combo.setEnabled(True)

        default_model = self._pending_ollama_default_model

        if default_model:
            self.model_combo.addItem(default_model)

        self._ollama_fetch_worker = None

    def _on_provider_changed(self, provider: str) -> None:
        if not provider:
            self.model_combo.clear()
            self.model_combo.setPlaceholderText("请先选择提供商")
            return
        self._refresh_models_for_provider(provider)
        self.ai_settings.set_default_provider(provider)

    def _load_or_create_conversation(self) -> None:
        conversations = self.service.get_conversations()
        if not conversations:
            self._create_conversation()
            return
        self._sidebar.history_list.clear()
        for conv in conversations:
            title = conv.get("title", "新会话") or "新会话"
            conv_id = conv.get("id")
            if conv_id is None:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, conv_id)
            item.setToolTip(title)
            self._sidebar.history_list.addItem(item)
        first_item = self._sidebar.history_list.item(0)
        if first_item:
            self._sidebar.history_list.setCurrentItem(first_item)
            self._on_conversation_selected(first_item)

    def _create_conversation(self) -> None:
        provider = self.provider_combo.currentText() or ""
        if not provider:
            provider = self.ai_settings.get_default_provider() or "default"
        model_id = self.model_combo.currentText() or ""
        if not model_id:
            model_id = self.ai_settings.get_default_model() or "default"

        try:
            conversation_id = self.service.add_conversation(
                title="新会话",
                provider=provider,
                model_id=model_id,
            )
            self.current_conversation_id = conversation_id
            self.chat_view.clear_messages()
            self._refresh_history_list()
            for i in range(self._sidebar.history_list.count()):
                item = self._sidebar.history_list.item(i)
                if item and item.data(Qt.UserRole) == conversation_id:
                    self._sidebar.history_list.setCurrentItem(item)
                    break
        except Exception as e:
            if hasattr(self.core, 'logger'):
                self.core.logger.error(f"创建会话失败: {e}")

    def _on_search_conversations(self, keyword: str) -> None:
        if not keyword.strip():
            self._refresh_history_list()
            return

        self._sidebar.history_list.clear()
        conversations = self.service.search_conversations(keyword, limit=100)

        if not conversations:
            item = QListWidgetItem(f'无搜索结果: "{keyword}"')
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self._sidebar.history_list.addItem(item)
            return

        for conv in conversations:
            title = conv.get("title", "新会话") or "新会话"
            conv_id = conv.get("id")
            if conv_id is None:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, conv_id)
            item.setToolTip(f"{title}\n(匹配搜索: {keyword})")
            self._sidebar.history_list.addItem(item)

    def _on_clear_search(self) -> None:
        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        self._sidebar.history_list.clear()
        conversations = self.service.get_conversations()
        for conv in conversations:
            title = conv.get("title", "新会话") or "新会话"
            conv_id = conv.get("id")
            if conv_id is None:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, conv_id)
            item.setToolTip(title)
            self._sidebar.history_list.addItem(item)

    def _on_conversation_selected(self, item: QListWidgetItem) -> None:
        self._on_stop_generation()
        conversation_id = item.data(Qt.UserRole)
        if conversation_id is None:
            return
        self.current_conversation_id = int(conversation_id)
        self.chat_view.clear_messages()
        messages = self.service.get_messages(self.current_conversation_id)
        for message in messages:
            is_user = message.get("role") == "user"
            content = message.get("content", "")
            self.chat_view.add_message(content, is_user)

    def select_conversation(self, conversation_id: int) -> None:
        """按 ID 选中并加载历史会话（供全局搜索跳转）"""
        history_list = self._sidebar.history_list
        for row in range(history_list.count()):
            item = history_list.item(row)
            if item is None or item.data(Qt.UserRole) is None:
                continue
            if int(item.data(Qt.UserRole)) == int(conversation_id):
                history_list.setCurrentItem(item)
                self._on_conversation_selected(item)
                return

    def _on_chat_send(self, text: str, attachments: list) -> None:
        if not text and not attachments:
            return
        if self.current_conversation_id is None:
            self._create_conversation()
        if self.current_conversation_id is None:
            return

        provider = self.provider_combo.currentText() or self.ai_settings.get_default_provider()
        model_id = self.model_combo.currentText() or self.ai_settings.get_default_model()

        if not provider:
            QMessageBox.warning(self, "提示", "请先选择AI提供商")
            return
        if not model_id:
            QMessageBox.warning(self, "提示", "请先选择模型")
            return
        self.ai_settings.set_default_provider(provider)
        self.ai_settings.set_default_model(model_id)

        content = text
        display_content = text
        attach_files = []

        for attach in attachments:
            file_name = attach.get('file_name', '未知文件')
            mime_type = attach.get('mime_type', '')
            attach_content = attach.get('content', '')
            base64_content = attach.get('base64_content', '')
            is_text = attach.get('is_text', False)
            is_image = attach.get('is_image', False)

            attach_files.append(file_name)

            if is_text and attach_content:
                content += f"\n--- {file_name} ---\n{attach_content[:500000]}\n---"
            elif is_image and base64_content:
                content += f"\n[图片: {file_name} (base64长度: {len(base64_content)})]"
            else:
                content += f"\n[文件: {file_name} ({mime_type})]"

        if attach_files:
            display_content = text + "\n" + ", ".join([f"[{f}]" for f in attach_files])
        self.chat_view.add_message(display_content, is_user=True, attachments=attachments)

        self._is_first_message = self.service.get_message_count(self.current_conversation_id) == 0
        self._first_message_content = text[:100]

        self.service.add_message(
            conversation_id=self.current_conversation_id,
            role="user",
            content=content,
        )

        search_enabled = self.chat_input.is_search_enabled()

        self._current_ai_bubble = self.chat_view.add_message("思考中...", is_user=False)
        self._is_thinking = True

        self.chat_input.set_sending_state(True)

        self._text_queue = deque()
        self._displayed_length = 0
        self._is_streaming = True
        self._last_callback_length = 0
        self._first_content_received = False

        self._stream_timer = QTimer(self)
        self._stream_timer.timeout.connect(self._process_stream_queue)
        self._stream_timer.start(30)
        self._last_stream_received = time.monotonic()

        enable_web_search = search_enabled

        conversation_history = []
        if self.current_conversation_id:
            history_messages = self.service.get_messages(self.current_conversation_id)
            if history_messages:
                conversation_history = [
                    {"role": msg.get("role"), "content": msg.get("content")}
                    for msg in history_messages
                    if msg.get("role") in ("user", "assistant") and msg.get("content")
                ]

        self._chat_worker = AIChatWorker(
            self.chat_service,
            content,
            provider,
            model_id,
            enable_web_search=enable_web_search,
            conversation_history=conversation_history,
        )
        self._chat_worker.stream_update.connect(self._on_stream_update)
        self._chat_worker.finished_signal.connect(self._on_chat_finished)
        self._chat_worker.error_signal.connect(self._on_chat_error)
        self._chat_worker.start()

    STREAM_TIMEOUT = 60

    def _process_stream_queue(self):
        if self._is_streaming and hasattr(self, '_last_stream_received'):
            elapsed = time.monotonic() - self._last_stream_received
            if elapsed > self.STREAM_TIMEOUT:
                self._on_chat_error(f"响应超时（{self.STREAM_TIMEOUT}秒无数据）")
                return

        if not self._is_streaming and not self._text_queue:
            self._stream_timer.stop()
            return

        chars_to_show = min(2, len(self._text_queue))
        new_text = ""
        for _ in range(chars_to_show):
            if self._text_queue:
                new_text += self._text_queue.popleft()

        if new_text and self._current_ai_bubble:
            if self._is_thinking:
                self._is_thinking = False
                self._first_content_received = True
                self._current_ai_bubble.update_text(new_text)
            else:
                self._displayed_length += len(new_text)
                self._current_ai_bubble.append_text(new_text)

    def _on_stream_update(self, text: str):
        self._last_stream_received = time.monotonic()
        new_chars = text[self._last_callback_length:]
        self._last_callback_length = len(text)
        for char in new_chars:
            self._text_queue.append(char)

    def _on_chat_finished(self, response):
        self._is_streaming = False
        self.chat_input.set_sending_state(False)

        if self._stream_timer:
            self._stream_timer.stop()

        assistant_text = response.content if not response.error else f"请求失败: {response.error}"

        if self._current_ai_bubble:
            self._current_ai_bubble.update_text(assistant_text)

        self.service.add_message(
            conversation_id=self.current_conversation_id,
            role="assistant",
            content=assistant_text,
            status="done" if not response.error else "error",
        )

        if hasattr(self, '_is_first_message') and self._is_first_message and not response.error:
            self._auto_generate_title()
            self._is_first_message = False

        self._chat_worker = None
        self._current_ai_bubble = None
        self._text_queue = None

    def _auto_generate_title(self) -> None:
        if not self.current_conversation_id:
            return

        content = getattr(self, '_first_message_content', '')
        if not content:
            return

        title = content[:20]
        if len(content) > 20:
            title += "..."

        self.service.update_conversation(self.current_conversation_id, title=title)

        for i in range(self._sidebar.history_list.count()):
            item = self._sidebar.history_list.item(i)
            if item and item.data(Qt.UserRole) == self.current_conversation_id:
                item.setText(title)
                item.setToolTip(title)
                break

    def _on_chat_error(self, error_msg: str):
        self._is_streaming = False
        self.chat_input.set_sending_state(False)

        if self._stream_timer:
            self._stream_timer.stop()

        error_text = f"请求失败: {error_msg}"
        if self._current_ai_bubble:
            self._current_ai_bubble.update_text(error_text)

        self.service.add_message(
            conversation_id=self.current_conversation_id,
            role="assistant",
            content=error_text,
            status="error",
        )

        self._chat_worker = None
        self._current_ai_bubble = None
        self._text_queue = None

        InfoBar.error(
            title="请求失败",
            content=error_msg,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self,
        )

    def _on_stop_generation(self):
        if self._chat_worker:
            self._chat_worker.stop()
            self._chat_worker = None

        self._is_streaming = False
        self.chat_input.set_sending_state(False)

        if self._stream_timer:
            self._stream_timer.stop()

        if self._current_ai_bubble:
            current_text = self._current_ai_bubble.text
            if current_text:
                self.service.add_message(
                    conversation_id=self.current_conversation_id,
                    role="assistant",
                    content=current_text,
                    status="stopped",
                )

        self._current_ai_bubble = None
        self._text_queue = None
