"""
AI 助手对话消息组件
左右分布布局：AI在左，用户在右
"""
from typing import Optional
import markdown

from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QScrollArea,
    QTextBrowser,
    QStackedWidget,
)
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFontMetrics
from qfluentwidgets import isDarkTheme, Theme, FluentIcon as FIF, IconWidget


class MessageBubble(QWidget):
    """消息气泡组件 - 带顶部状态栏和Markdown渲染"""

    def __init__(self, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self._is_markdown_mode = False
        self._rendered_chunks = []
        self._current_chunk_index = 0
        self._chunk_size = 1000
        self._setup_ui()
        self._connect_theme_signal()

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # 主布局：图标 + 内容区域
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(8)

        if self.is_user:
            main_layout.addStretch()

        # 图标
        if not self.is_user:
            icon = FIF.ROBOT
            self._icon_widget = IconWidget(icon, self)
            self._icon_widget.setFixedSize(20, 20)
            main_layout.addWidget(self._icon_widget, 0, Qt.AlignTop)

        # 内容区域：垂直布局（状态栏 + 消息文本）
        content_widget = QWidget(self)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # 顶部状态栏
        self._header_widget = QWidget(content_widget)
        header_layout = QHBoxLayout(self._header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        # 角色标签
        self._role_label = QLabel("AI" if not self.is_user else "用户", self._header_widget)
        self._role_label.setObjectName("roleLabel")
        header_layout.addWidget(self._role_label)

        header_layout.addStretch()

        # Markdown切换按钮
        self._md_btn = IconWidget(FIF.CODE, self._header_widget)
        self._md_btn.setFixedSize(16, 16)
        self._md_btn.setCursor(Qt.PointingHandCursor)
        self._md_btn.setToolTip("切换Markdown渲染")
        self._md_btn.mousePressEvent = lambda e: self._toggle_markdown()
        header_layout.addWidget(self._md_btn)

        # 复制按钮
        self._copy_btn = IconWidget(FIF.COPY, self._header_widget)
        self._copy_btn.setFixedSize(16, 16)
        self._copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn.mousePressEvent = lambda e: self._copy_content()
        header_layout.addWidget(self._copy_btn)

        content_layout.addWidget(self._header_widget)

        # 内容区域：使用QStackedWidget切换原文和Markdown
        self._content_stack = QStackedWidget(content_widget)
        self._content_stack.setMaximumWidth(600)

        # 原文标签
        self._label = QLabel(self.text)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setCursor(Qt.IBeamCursor)
        self._content_stack.addWidget(self._label)

        # Markdown浏览器
        self._md_browser = QTextBrowser(content_widget)
        self._md_browser.setOpenExternalLinks(True)
        self._md_browser.setWordWrapMode(1)  # QTextOption.WrapAtWordBoundaryOrAnywhere
        self._content_stack.addWidget(self._md_browser)

        content_layout.addWidget(self._content_stack)

        main_layout.addWidget(content_widget)

        if self.is_user:
            icon = FIF.PEOPLE
            self._icon_widget = IconWidget(icon, self)
            self._icon_widget.setFixedSize(20, 20)
            main_layout.addWidget(self._icon_widget, 0, Qt.AlignTop)
        else:
            main_layout.addStretch()

        self._apply_style()

    def _copy_content(self):
        """复制消息内容到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text)

    def _toggle_markdown(self):
        """切换Markdown渲染模式"""
        self._is_markdown_mode = not self._is_markdown_mode

        if self._is_markdown_mode:
            self._render_markdown()
            self._content_stack.setCurrentIndex(1)
            self._md_btn.setToolTip("退出源代码模式")
        else:
            self._content_stack.setCurrentIndex(0)
            self._md_btn.setToolTip("切换Markdown渲染")

    def _render_markdown(self):
        """分批渲染Markdown内容"""
        self._rendered_chunks = []
        self._current_chunk_index = 0

        # 将文本分成每1000字符的块
        text = self.text
        for i in range(0, len(text), self._chunk_size):
            chunk = text[i:i + self._chunk_size]
            self._rendered_chunks.append(chunk)

        # 渲染第一批
        self._render_next_chunk()

    def _render_next_chunk(self):
        """渲染下一批Markdown内容"""
        if self._current_chunk_index >= len(self._rendered_chunks):
            return

        chunks_to_render = self._rendered_chunks[:self._current_chunk_index + 1]
        content = ''.join(chunks_to_render)

        # 转换为Markdown HTML
        try:
            html_content = markdown.markdown(
                content,
                extensions=['fenced_code', 'tables', 'toc']
            )
        except Exception:
            html_content = f"<pre>{content}</pre>"

        # 应用样式
        dark = isDarkTheme()
        bg_color = "#3d3d3d" if dark else "#f0f0f0"
        text_color = "#ffffff" if dark else "#1f1f1f"
        code_bg = "#2d2d2d" if dark else "#e8e8e8"

        styled_html = f"""
        <html>
        <head>
        <style>
            body {{
                background-color: {bg_color};
                color: {text_color};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                padding: 8px;
                margin: 0;
            }}
            pre {{
                background-color: {code_bg};
                padding: 12px;
                border-radius: 6px;
                overflow-x: auto;
            }}
            code {{
                background-color: {code_bg};
                padding: 2px 6px;
                border-radius: 3px;
                font-family: "Consolas", "Monaco", monospace;
            }}
            pre code {{
                background: none;
                padding: 0;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid {'#555' if dark else '#ddd'};
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: {code_bg};
            }}
            a {{
                color: #0078d4;
            }}
            blockquote {{
                border-left: 4px solid #0078d4;
                margin: 0;
                padding-left: 16px;
                color: {'#aaa' if dark else '#666'};
            }}
        </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        self._md_browser.setHtml(styled_html)
        self._current_chunk_index += 1

        # 如果还有更多块，继续渲染
        if self._current_chunk_index < len(self._rendered_chunks):
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(10, self._render_next_chunk)

    def update_text(self, text: str):
        """更新消息文本（用于流式输出）"""
        self.text = text
        self._label.setText(text)
        # 滚动到底部
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(10, self._scroll_parent_to_bottom)

    def append_text(self, text: str):
        """追加文本（用于流式输出）"""
        self.text += text
        current = self._label.text()
        self._label.setText(current + text)
        # 滚动到底部
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(10, self._scroll_parent_to_bottom)

    def _scroll_parent_to_bottom(self):
        """滚动父容器到底部"""
        parent = self.parent()
        while parent:
            if isinstance(parent, ChatMessageList):
                parent._scroll_to_bottom()
                break
            parent = parent.parent()

    def _connect_theme_signal(self):
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        self._apply_style()
        # 如果当前在Markdown模式，重新渲染以应用新主题
        if self._is_markdown_mode:
            self._current_chunk_index = 0
            self._render_next_chunk()

    def _apply_style(self):
        dark = isDarkTheme()

        if self.is_user:
            bg_color = "#0078d4"
            text_color = "#ffffff"
            header_bg = "#005a9e"
        else:
            if dark:
                bg_color = "#3d3d3d"
                text_color = "#ffffff"
                header_bg = "#2d2d2d"
            else:
                bg_color = "#f0f0f0"
                text_color = "#1f1f1f"
                header_bg = "#e0e0e0"

        # 设置整体内容区域样式（状态栏+消息文本统一背景）
        content_widget = self._label.parent()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 12px;
            }}
        """)

        # 设置状态栏样式（透明背景，只显示文字和按钮）
        self._header_widget.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
            }}
            QLabel#roleLabel {{
                background: transparent;
                color: {text_color};
                font-size: 12px;
                font-weight: bold;
            }}
        """)

        # 设置消息文本样式
        self._label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {text_color};
                padding: 0px 8px 8px 8px;
                font-size: 14px;
                line-height: 1.5;
            }}
        """)

    def disconnect(self):
        from qfluentwidgets import qconfig
        try:
            qconfig.themeChanged.disconnect(self._on_theme_changed)
        except Exception:
            pass


class ChatMessageContainer(QWidget):
    """消息容器（内部使用）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("chatMessageContainer")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 8, 0, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch()

    def add_message(self, text: str, is_user: bool = False):
        """添加消息"""
        bubble = MessageBubble(text, is_user, self)
        self._layout.insertWidget(self._layout.count() - 1, bubble)

    def clear_messages(self):
        """清空消息"""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ChatMessageList(QWidget):
    """对话消息列表（带滚动）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._apply_style()
        self._connect_theme_signal()

    def _setup_ui(self):
        self.setObjectName("chatMessageList")
        self.setAttribute(Qt.WA_StyledBackground, False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("chatScrollArea")
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QScrollArea.NoFrame)
        self._scroll_area.viewport().setAutoFillBackground(False)

        self._container = ChatMessageContainer(self)
        self._scroll_area.setWidget(self._container)

        main_layout.addWidget(self._scroll_area)

    def _connect_theme_signal(self):
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        self._apply_style()
        self._container.setStyleSheet("")
        for i in range(self._container._layout.count()):
            item = self._container._layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                item.widget()._apply_style()

    def _apply_style(self):
        dark = isDarkTheme()
        scroll_bg = "rgba(255,255,255,0.05)" if dark else "rgba(0,0,0,0.05)"
        scroll_handle = "rgba(255,255,255,0.2)" if dark else "rgba(0,0,0,0.2)"

        self.setStyleSheet(f"""
            #chatMessageList {{
                background: transparent;
                border: none;
            }}
            #chatScrollArea {{
                background: transparent;
                border: none;
            }}
            #chatMessageContainer {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {scroll_bg};
                width: 8px;
                border-radius: 4px;
                margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar:sub-page:vertical {{
                background: transparent;
            }}
        """)

    def add_message(self, text: str, is_user: bool = False) -> 'MessageBubble':
        """添加消息，返回消息气泡对象"""
        self._container.add_message(text, is_user)
        self._scroll_to_bottom()
        # 返回最后添加的消息气泡
        count = self._container._layout.count()
        if count > 1:
            item = self._container._layout.itemAt(count - 2)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                return item.widget()
        return None

    def get_last_message(self) -> Optional['MessageBubble']:
        """获取最后一条消息"""
        count = self._container._layout.count()
        if count > 1:
            item = self._container._layout.itemAt(count - 2)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                return item.widget()
        return None

    def clear_messages(self):
        """清空消息"""
        self._container.clear_messages()

    def _scroll_to_bottom(self):
        """滚动到底部"""
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

