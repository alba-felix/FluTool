from typing import Optional
from collections import deque

from PyQt5.QtCore import Qt, QVariantAnimation, QEasingCurve, pyqtSignal, QRect, QTimer, QThread
from PyQt5.QtGui import QPainter, QColor
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
    ListWidget,
    StrongBodyLabel,
    isDarkTheme, ToolButton,
    LineEdit,
    PushButton,
)

from core import PluginInterface
from core.ai import AIChatService, AISettingsBridge, AISearchBridge
from storage.repositories import AIRepository
from .chat_input import ChatInputWidget
from .chat_message import ChatMessageList


class AIChatWorker(QThread):
    """AI聊天工作线程 - 防止UI阻塞"""

    stream_update = pyqtSignal(str)  # 流式更新信号
    finished_signal = pyqtSignal(object)  # 完成信号，传递AIChatResponse
    error_signal = pyqtSignal(str)  # 错误信号

    def __init__(self, chat_service, user_text: str, provider: str, model_id: str, enable_web_search: bool = False):
        super().__init__()
        self.chat_service = chat_service
        self.user_text = user_text
        self.provider = provider
        self.model_id = model_id
        self.enable_web_search = enable_web_search
        self._is_running = True
        self._response = None

    def run(self):
        """执行聊天请求"""
        try:
            def stream_callback(text: str):
                if self._is_running:
                    self.stream_update.emit(text)

            self._response = self.chat_service.send_message(
                user_text=self.user_text,
                provider=self.provider,
                model_id=self.model_id,
                stream_callback=stream_callback,
                enable_web_search=self.enable_web_search,
            )

            if self._is_running:
                self.finished_signal.emit(self._response)
        except Exception as e:
            if self._is_running:
                self.error_signal.emit(str(e))

    def stop(self):
        """停止生成"""
        self._is_running = False
        self.wait(1000)  # 等待1秒让线程结束


class SidebarToggleButton(QWidget):
    """侧边栏切换按钮"""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._isCompacted = True
        self._isHover = False
        self._isPressed = False
        self.setFixedSize(48, 36)
        self.setCursor(Qt.PointingHandCursor)

    def setCompacted(self, isCompacted: bool):
        if isCompacted == self._isCompacted:
            return
        self._isCompacted = isCompacted
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.setPen(Qt.NoPen)

        if self._isPressed:
            painter.setOpacity(0.7)

        c = 255 if isDarkTheme() else 0
        if self._isHover:
            painter.setBrush(QColor(c, c, c, 10))
            painter.drawRoundedRect(self.rect(), 5, 5)

        from qfluentwidgets.common.icon import drawIcon
        drawIcon(FIF.MENU, painter, QRect(16, 10, 16, 16))

        if not self._isCompacted:
            painter.setPen(QColor(c, c, c))
            font = painter.font()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(QRect(44, 0, self.width() - 52, self.height()), Qt.AlignVCenter, "收起")

    def enterEvent(self, e):
        self._isHover = True
        self.update()

    def leaveEvent(self, e):
        self._isHover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._isPressed = True
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._isPressed = False
            self.update()
            if self.rect().contains(e.pos()):
                self.clicked.emit()


class AISidebar(QWidget):
    """AI 助手侧边栏"""

    COMPACTED_WIDTH = 48
    EXPAND_WIDTH = 260

    search_requested = pyqtSignal(str)  # 搜索请求信号
    clear_search_requested = pyqtSignal()  # 清除搜索信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._isExpanded = False
        self.setAttribute(Qt.WA_StyledBackground)

        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)

        self._toggle_btn = SidebarToggleButton(self)
        self._toggle_btn.clicked.connect(self.toggle)
        self.vBoxLayout.addWidget(self._toggle_btn, 0, Qt.AlignTop | Qt.AlignLeft)

        self._new_chat_btn = ToolButton(FIF.ADD, self)
        self._new_chat_btn.setToolTip("新建会话")
        self._new_chat_btn.setFixedSize(32, 32)
        self._new_chat_btn.clicked.connect(self._on_new_chat)
        self.vBoxLayout.addWidget(self._new_chat_btn, 0, Qt.AlignTop | Qt.AlignLeft)

        # 搜索框容器
        self._search_container = QWidget(self)
        self._search_layout = QHBoxLayout(self._search_container)
        self._search_layout.setContentsMargins(8, 8, 8, 8)
        self._search_layout.setSpacing(4)

        self._search_edit = LineEdit(self)
        self._search_edit.setPlaceholderText("搜索对话...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.returnPressed.connect(self._on_search)
        self._search_edit.textChanged.connect(self._on_search_text_changed)
        self._search_layout.addWidget(self._search_edit, 1)

        self._clear_search_btn = ToolButton(FIF.CANCEL, self)
        self._clear_search_btn.setToolTip("清除搜索")
        self._clear_search_btn.setFixedSize(28, 28)
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        self._clear_search_btn.setVisible(False)
        self._search_layout.addWidget(self._clear_search_btn)

        self.vBoxLayout.addWidget(self._search_container)

        self._new_chat_callback = None

        self.history_list = ListWidget(self)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.history_list.setTextElideMode(Qt.ElideRight)
        self.vBoxLayout.addWidget(self.history_list, 1)

        self._ani = QVariantAnimation(self)
        self._ani.setDuration(150)
        self._ani.setEasingCurve(QEasingCurve.OutQuad)
        self._ani.valueChanged.connect(self._on_ani_value_changed)

        self.setFixedWidth(self.COMPACTED_WIDTH)
        self._update_compacted_state()

    def _on_search(self):
        """执行搜索"""
        keyword = self._search_edit.text().strip()
        if keyword:
            self.search_requested.emit(keyword)
            self._clear_search_btn.setVisible(True)
        else:
            self.clear_search_requested.emit()
            self._clear_search_btn.setVisible(False)

    def _on_search_text_changed(self, text: str):
        """搜索文本变化"""
        if not text.strip():
            self.clear_search_requested.emit()
            self._clear_search_btn.setVisible(False)
        else:
            self._clear_search_btn.setVisible(True)

    def _on_clear_search(self):
        """清除搜索"""
        self._search_edit.clear()
        self.clear_search_requested.emit()
        self._clear_search_btn.setVisible(False)

    def set_search_callback(self, callback):
        """设置搜索回调"""
        self.search_requested.connect(callback)

    def set_clear_search_callback(self, callback):
        """设置清除搜索回调"""
        self.clear_search_requested.connect(callback)

    def _on_ani_value_changed(self, value):
        self.setFixedWidth(int(value))

    def _update_compacted_state(self):
        compacted = not self._isExpanded
        self._toggle_btn.setCompacted(compacted)
        self._new_chat_btn.setVisible(self._isExpanded)
        self._search_container.setVisible(self._isExpanded)
        self.history_list.setVisible(self._isExpanded)

    def toggle(self):
        if self._isExpanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self._isExpanded = True
        self._animate_width(self.EXPAND_WIDTH)
        self._update_compacted_state()

    def collapse(self):
        self._isExpanded = False
        self._animate_width(self.COMPACTED_WIDTH)
        self._update_compacted_state()

    def _animate_width(self, target: int):
        self._ani.stop()
        self._ani.setStartValue(self.width())
        self._ani.setEndValue(target)
        self._ani.start()

    def isExpanded(self) -> bool:
        return self._isExpanded

    def setNewChatCallback(self, callback):
        self._new_chat_callback = callback

    def _on_new_chat(self):
        if self._new_chat_callback:
            self._new_chat_callback()


class AIAssistantWidget(QWidget):
    """AI 助手插件基础界面"""

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.repo = AIRepository()

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
        self._load_provider_and_models()
        self._load_or_create_conversation()

    def showEvent(self, event):
        """窗口显示时刷新设置"""
        super().showEvent(event)
        self._refresh_from_settings()

    def _refresh_from_settings(self) -> None:
        """从设置重新加载提供商和模型"""
        # 保存当前选择
        current_provider = self.provider_combo.currentText()
        current_model = self.model_combo.currentText()

        # 重新加载
        self._load_provider_and_models()

        # 尝试恢复选择，如果没有则使用设置中的默认值
        provider_index = self.provider_combo.findText(current_provider)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)
        else:
            # 使用设置中的默认提供商
            default_provider = self.ai_settings.get_default_provider()
            idx = self.provider_combo.findText(default_provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)

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

        # 对话消息列表（左右分布：AI在左，用户在右）
        self.chat_view = ChatMessageList(self)
        right_layout.addWidget(self.chat_view, 1)

        # 使用新的聊天输入框组件
        self.chat_input = ChatInputWidget(self)
        self.chat_input.send_clicked.connect(self._on_chat_send)
        self.chat_input.stop_clicked.connect(self._on_stop_generation)
        right_layout.addWidget(self.chat_input)

        root_layout.addWidget(right_widget, 1)

        # 工作线程
        self._chat_worker: Optional[AIChatWorker] = None
        self._current_ai_bubble = None
        self._stream_timer = None
        self._text_queue = None

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
        from PyQt5.QtWidgets import QMenu, QAction
        item = self._sidebar.history_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        delete_action = QAction("删除此会话", self)
        delete_action.triggered.connect(lambda: self._delete_conversation(item))
        menu.addAction(delete_action)
        menu.exec_(self._sidebar.history_list.mapToGlobal(pos))

    def _delete_conversation(self, item: QListWidgetItem) -> None:
        conv_id = item.data(Qt.UserRole)
        if conv_id is None:
            return
        conv_id = int(conv_id)
        self.repo.delete_conversation(conv_id)
        if self.current_conversation_id == conv_id:
            self.current_conversation_id = None
            self.chat_view.clear()
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
        providers = sorted(set(model.provider for model in models))
        for provider in providers:
            self.provider_combo.addItem(provider)

        default_provider = self.ai_settings.get_default_provider() or ""
        provider_index = self.provider_combo.findText(default_provider)
        if provider_index >= 0:
            self.provider_combo.setCurrentIndex(provider_index)

        self._refresh_models_for_provider(self.provider_combo.currentText() or "")

    def _refresh_models_for_provider(self, provider: str) -> None:
        self.model_combo.clear()
        if not provider:
            return

        # 从提供商配置获取默认模型
        provider_config = self.ai_settings.get_provider_config(provider)
        default_model = provider_config.get("default_model", "")

        # 添加默认模型到下拉框
        if default_model:
            self.model_combo.addItem(default_model)

        # 也添加模型列表中的其他模型（如果有）
        models = self.chat_service.get_enabled_models()
        selected = [m for m in models if m.provider == provider and m.model_id != default_model]
        for model in selected:
            self.model_combo.addItem(model.model_id)

        # 选中默认模型
        if default_model:
            model_index = self.model_combo.findText(default_model)
            if model_index >= 0:
                self.model_combo.setCurrentIndex(model_index)

    def _on_provider_changed(self, provider: str) -> None:
        if not provider:
            return
        self._refresh_models_for_provider(provider)
        self.ai_settings.set_default_provider(provider)

    def _load_or_create_conversation(self) -> None:
        conversations = self.repo.list_conversations(limit=100)
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
            conversation_id = self.repo.create_conversation(
                title="新会话",
                provider=provider,
                model_id=model_id,
            )
            self.current_conversation_id = conversation_id
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
        """搜索对话历史"""
        if not keyword.strip():
            self._refresh_history_list()
            return

        self._sidebar.history_list.clear()
        conversations = self.repo.search_conversations(keyword, limit=100)

        if not conversations:
            # 显示无结果提示
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
        """清除搜索，恢复完整列表"""
        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        self._sidebar.history_list.clear()
        conversations = self.repo.list_conversations(limit=100)
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
        conversation_id = item.data(Qt.UserRole)
        if conversation_id is None:
            return
        self.current_conversation_id = int(conversation_id)
        self.chat_view.clear_messages()
        messages = self.repo.list_messages(self.current_conversation_id)
        for message in messages:
            is_user = message.get("role") == "user"
            content = message.get("content", "")
            self.chat_view.add_message(content, is_user)

    def _on_chat_send(self, text: str, attachments: list) -> None:
        """处理发送消息 - 使用工作线程防止UI阻塞"""
        if not text and not attachments:
            return
        if self.current_conversation_id is None:
            self._create_conversation()
        if self.current_conversation_id is None:
            return

        provider = self.provider_combo.currentText() or self.ai_settings.get_default_provider()
        model_id = self.model_combo.currentText() or self.ai_settings.get_default_model()
        if not provider or not model_id:
            QMessageBox.warning(self, "提示", "请先选择提供商和模型")
            return
        self.ai_settings.set_default_provider(provider)
        self.ai_settings.set_default_model(model_id)

        # 构建消息内容（包含附件内容）- 只显示文件名在对话框
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

            # 显示用：只显示文件名
            attach_files.append(file_name)

            # 发送给模型的内容：包含完整内容
            if is_text and attach_content:
                content += f"\n--- {file_name} ---\n{attach_content[:500000]}\n---"
            elif is_image and base64_content:
                content += f"\n[图片: {file_name} (base64长度: {len(base64_content)})]"
            else:
                content += f"\n[文件: {file_name} ({mime_type})]"

        # 显示用户消息（右侧）- 简化显示
        if attach_files:
            display_content = text + "\n" + ", ".join([f"[{f}]" for f in attach_files])
        self.chat_view.add_message(display_content, is_user=True)

        # 保存到数据库的是完整内容
        self.repo.add_message(
            conversation_id=self.current_conversation_id,
            role="user",
            content=content,
        )

        # TODO: 处理深度思考和智能搜索选项
        deep_think = self.chat_input.is_deep_think_enabled()
        search_enabled = self.chat_input.is_search_enabled()

        # 创建AI消息气泡（用于流式更新）- 显示思考中
        self._current_ai_bubble = self.chat_view.add_message("思考中...", is_user=False)
        self._is_thinking = True  # 标记正在思考

        # 设置发送状态
        self.chat_input.set_sending_state(True)

        # 流式输出队列和定时器
        self._text_queue = deque()
        self._displayed_length = 0
        self._is_streaming = True
        self._last_callback_length = 0  # 重置回调长度计数器
        self._first_content_received = False  # 标记是否收到第一个内容

        # 创建定时器，每30ms更新一次
        self._stream_timer = QTimer(self)
        self._stream_timer.timeout.connect(self._process_stream_queue)
        self._stream_timer.start(30)

        # 判断是否启用 web_search（智能搜索激活且模型支持）
        enable_web_search = False
        if search_enabled:
            enable_web_search = self.chat_service.supports_web_search(provider, model_id)

        # 创建工作线程
        self._chat_worker = AIChatWorker(
            self.chat_service,
            content,
            provider,
            model_id,
            enable_web_search=enable_web_search,
        )
        self._chat_worker.stream_update.connect(self._on_stream_update)
        self._chat_worker.finished_signal.connect(self._on_chat_finished)
        self._chat_worker.error_signal.connect(self._on_chat_error)
        self._chat_worker.start()

    def _process_stream_queue(self):
        """处理文本队列，逐字显示"""
        if not self._is_streaming and not self._text_queue:
            self._stream_timer.stop()
            return

        # 每次显示1-2个字符
        chars_to_show = min(2, len(self._text_queue))
        new_text = ""
        for _ in range(chars_to_show):
            if self._text_queue:
                new_text += self._text_queue.popleft()

        if new_text and self._current_ai_bubble:
            # 收到第一个内容时，清除"思考中..."状态
            if self._is_thinking:
                self._is_thinking = False
                self._first_content_received = True
                # 替换掉"思考中..."这个初始文本
                self._current_ai_bubble.update_text(new_text)
            else:
                self._displayed_length += len(new_text)
                self._current_ai_bubble.append_text(new_text)

    def _on_stream_update(self, text: str):
        """流式更新回调"""
        # 只添加新增的字符到队列
        new_chars = text[self._last_callback_length:]
        self._last_callback_length = len(text)
        for char in new_chars:
            self._text_queue.append(char)

    def _on_chat_finished(self, response):
        """聊天完成回调"""
        self._is_streaming = False
        self.chat_input.set_sending_state(False)

        # 等待队列处理完成
        if self._stream_timer:
            self._stream_timer.stop()

        assistant_text = response.content if not response.error else f"请求失败: {response.error}"

        # 确保最终内容显示完整
        if self._current_ai_bubble:
            self._current_ai_bubble.update_text(assistant_text)

        # 保存到数据库
        self.repo.add_message(
            conversation_id=self.current_conversation_id,
            role="assistant",
            content=assistant_text,
            status="done" if not response.error else "error",
        )

        # 清理
        self._chat_worker = None
        self._current_ai_bubble = None
        self._text_queue = None

    def _on_chat_error(self, error_msg: str):
        """聊天错误回调"""
        self._is_streaming = False
        self.chat_input.set_sending_state(False)

        if self._stream_timer:
            self._stream_timer.stop()

        # 显示错误消息
        error_text = f"请求失败: {error_msg}"
        if self._current_ai_bubble:
            self._current_ai_bubble.update_text(error_text)

        # 保存错误消息
        self.repo.add_message(
            conversation_id=self.current_conversation_id,
            role="assistant",
            content=error_text,
            status="error",
        )

        # 清理
        self._chat_worker = None
        self._current_ai_bubble = None
        self._text_queue = None

        # 显示错误提示
        QMessageBox.critical(self, "错误", f"AI请求失败:\n{error_msg}")

    def _on_stop_generation(self):
        """停止生成"""
        if self._chat_worker:
            self._chat_worker.stop()
            self._chat_worker = None

        self._is_streaming = False
        self.chat_input.set_sending_state(False)

        if self._stream_timer:
            self._stream_timer.stop()

        # 保存已生成的内容
        if self._current_ai_bubble:
            current_text = self._current_ai_bubble.text
            if current_text:
                self.repo.add_message(
                    conversation_id=self.current_conversation_id,
                    role="assistant",
                    content=current_text,
                    status="stopped",
                )

        self._current_ai_bubble = None
        self._text_queue = None


class Plugin(PluginInterface):
    """AI 助手插件"""

    PLUGIN_ID = "ai_assistant"
    PLUGIN_NAME = "AI 助手"
    PLUGIN_ICON = FIF.ROBOT
    PLUGIN_PRIORITY = 8

    def initialize(self, core) -> None:
        self.core = core
        self.core.logger.info(f"Plugin '{self.get_name()}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return AIAssistantWidget(self.core, parent)
