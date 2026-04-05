"""
AI 助手聊天输入框组件
参考 DeepSeek 风格布局
"""
import os
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QFileDialog,
)
from PyQt5.QtGui import QImage, QKeyEvent
from qfluentwidgets import (
    TextEdit,
    ToolButton,
    PrimaryToolButton,
    ToggleButton,
    FluentIcon as FIF,
    isDarkTheme,
)


class ChatTextEdit(TextEdit):
    """自定义输入框：Enter发送，Alt+Enter换行"""

    send_requested = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key_Return or key == Qt.Key_Enter:
            if modifiers & Qt.AltModifier:
                # Alt + Enter: 插入换行
                cursor = self.textCursor()
                cursor.insertText("\n")
            else:
                # Enter: 发送消息
                self.send_requested.emit()
                return
        else:
            super().keyPressEvent(event)


class AttachmentItem(QWidget):
    """附件预览项"""

    removed = pyqtSignal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = file_path.split("/")[-1].split("\\")[-1]
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedHeight(36)
        self.setMinimumWidth(160)
        self.setMaximumWidth(240)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # 文件图标
        icon_btn = ToolButton(FIF.DOCUMENT, self)
        icon_btn.setFixedSize(24, 24)
        icon_btn.setEnabled(False)
        layout.addWidget(icon_btn)

        # 文件名
        name_label = PushButton(self.file_name, self)
        name_label.setFlat(True)
        name_label.setEnabled(False)
        name_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(name_label, 1)

        # 删除按钮
        remove_btn = ToolButton(FIF.CLOSE, self)
        remove_btn.setFixedSize(20, 20)
        remove_btn.setToolTip("移除")
        remove_btn.clicked.connect(lambda: self.removed.emit(self.file_path))
        layout.addWidget(remove_btn)

        self._apply_style()

    def _apply_style(self):
        dark = isDarkTheme()
        bg = "rgba(255,255,255,0.08)" if dark else "rgba(0,0,0,0.06)"
        border = "rgba(255,255,255,0.12)" if dark else "rgba(0,0,0,0.08)"
        text_color = "#ffffff" if dark else "#222222"

        self.setStyleSheet(f"""
            AttachmentItem {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            AttachmentItem QPushButton {{
                color: {text_color};
                font-size: 12px;
            }}
        """)


class AttachmentData:
    """附件数据"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.file_name = Path(file_path).name
        self.file_size = os.path.getsize(file_path)
        self.mime_type = self._detect_mime_type()
        self.content = None
        self.base64_content = None

    def _detect_mime_type(self) -> str:
        """检测文件 MIME 类型"""
        ext = Path(self.file_path).suffix.lower()
        mime_map = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'text/xml',
            '.csv': 'text/csv',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
        }
        return mime_map.get(ext, 'application/octet-stream')

    def is_text(self) -> bool:
        """是否为文本文件"""
        return self.mime_type.startswith('text/') or self.mime_type in [
            'application/json', 'application/xml'
        ]

    def is_image(self) -> bool:
        """是否为图片文件"""
        return self.mime_type.startswith('image/')

    def read_content(self) -> bool:
        """读取文件内容"""
        try:
            if self.is_text():
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.content = f.read()
                return True
            elif self.is_image():
                with open(self.file_path, 'rb') as f:
                    self.base64_content = base64.b64encode(f.read()).decode('utf-8')
                return True
            else:
                # 其他类型尝试作为文本读取
                with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self.content = f.read()[:10000]  # 限制大小
                return True
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'file_name': self.file_name,
            'file_path': self.file_path,
            'mime_type': self.mime_type,
            'is_text': self.is_text(),
            'is_image': self.is_image(),
            'content': self.content,
            'base64_content': self.base64_content,
        }


class ChatInputWidget(QWidget):
    """聊天输入框组件"""

    send_clicked = pyqtSignal(str, list)  # 文本, 附件数据列表
    stop_clicked = pyqtSignal()  # 停止生成信号
    attach_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._attachments: List[AttachmentData] = []
        self._is_sending = False
        self._setup_ui()
        self._apply_style()
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题切换信号"""
        from qfluentwidgets import qconfig
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        """主题切换时更新样式"""
        self._apply_style()

    def set_sending_state(self, is_sending: bool):
        """设置发送状态"""
        self._is_sending = is_sending
        if is_sending:
            # 发送中：显示停止按钮，禁用输入
            self._send_btn.setIcon(FIF.PAUSE)
            self._send_btn.setToolTip("停止生成")
            self._input_edit.setEnabled(False)
            self._attach_btn.setEnabled(False)
            self._deep_think_btn.setEnabled(False)
            self._search_btn.setEnabled(False)
        else:
            # 空闲：显示发送按钮，启用输入
            self._send_btn.setIcon(FIF.SEND_FILL)
            self._send_btn.setToolTip("发送")
            self._input_edit.setEnabled(True)
            self._attach_btn.setEnabled(True)
            self._deep_think_btn.setEnabled(True)
            self._search_btn.setEnabled(True)
            self._input_edit.setFocus()

    def is_sending(self) -> bool:
        """是否正在发送/生成中"""
        return self._is_sending

    def _setup_ui(self):
        self.setObjectName("chatInputWidget")
        self.setAttribute(Qt.WA_StyledBackground, False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # 附件预览区（横向滚动）
        self._attachment_area = QScrollArea(self)
        self._attachment_area.setObjectName("attachmentArea")
        self._attachment_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._attachment_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._attachment_area.setWidgetResizable(True)
        self._attachment_area.setFixedHeight(44)
        self._attachment_area.setVisible(False)
        self._attachment_area.setFrameShape(QScrollArea.NoFrame)
        self._attachment_area.viewport().setAutoFillBackground(False)

        self._attachment_container = QWidget()
        self._attachment_container.setObjectName("attachmentContainer")
        self._attachment_layout = QHBoxLayout(self._attachment_container)
        self._attachment_layout.setContentsMargins(0, 0, 0, 0)
        self._attachment_layout.setSpacing(8)
        self._attachment_layout.addStretch()
        self._attachment_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._attachment_area.setWidget(self._attachment_container)
        main_layout.addWidget(self._attachment_area)

        # 输入框
        self._input_edit = ChatTextEdit(self)
        self._input_edit.setObjectName("chatInputEdit")
        self._input_edit.setPlaceholderText("有问题，尽管问。可用 @搜索 关键词 联动全局搜索")
        self._input_edit.setMaximumHeight(80)
        self._input_edit.setMinimumHeight(40)
        self._input_edit.send_requested.connect(self._on_send)
        main_layout.addWidget(self._input_edit)

        # 底部工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # 左侧功能按钮
        self._deep_think_btn = ToggleButton("深度思考", self)
        self._deep_think_btn.setIcon(FIF.BRIGHTNESS)
        self._deep_think_btn.setToolTip("开启深度思考模式")
        self._deep_think_btn.setFixedHeight(32)

        self._search_btn = ToggleButton("智能搜索", self)
        self._search_btn.setIcon(FIF.SEARCH)
        self._search_btn.setToolTip("开启智能搜索")
        self._search_btn.setFixedHeight(32)

        toolbar.addWidget(self._deep_think_btn)
        toolbar.addWidget(self._search_btn)
        toolbar.addStretch()

        # 右侧操作按钮
        self._attach_btn = ToolButton(FIF.FOLDER_ADD, self)
        self._attach_btn.setToolTip("添加附件")
        self._attach_btn.setFixedSize(36, 36)
        self._attach_btn.clicked.connect(self._on_attach)

        self._send_btn = PrimaryToolButton(FIF.SEND_FILL, self)
        self._send_btn.setToolTip("发送")
        self._send_btn.setFixedSize(36, 36)
        self._send_btn.clicked.connect(self._on_send)

        toolbar.addWidget(self._attach_btn)
        toolbar.addWidget(self._send_btn)

        main_layout.addLayout(toolbar)

    def _apply_style(self):
        dark = isDarkTheme()
        text_color = "#ffffff" if dark else "#222222"
        scroll_bg = "rgba(255,255,255,0.05)" if dark else "rgba(0,0,0,0.05)"
        scroll_handle = "rgba(255,255,255,0.2)" if dark else "rgba(0,0,0,0.2)"

        self.setStyleSheet(f"""
            #chatInputWidget {{
                background: transparent;
                border: none;
            }}
            #chatInputEdit {{
                background: transparent;
                border: none;
                color: {text_color};
                font-size: 14px;
                padding: 4px;
            }}
            #attachmentArea {{
                background: transparent;
                border: none;
            }}
            #attachmentContainer {{
                background: transparent;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {scroll_bg};
                height: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:horizontal {{
                background: {scroll_handle};
                min-width: 20px;
                border-radius: 3px;
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

    def _on_attach(self):
        """添加附件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择附件",
            "",
            "所有文件 (*.*)"
        )
        for file_path in files:
            if not any(a.file_path == file_path for a in self._attachments):
                self._add_attachment(file_path)

    def _add_attachment(self, file_path: str):
        """添加附件项"""
        attach_data = AttachmentData(file_path)

        # 读取内容
        if not attach_data.read_content():
            return

        self._attachments.append(attach_data)

        item = AttachmentItem(file_path, self)
        item.removed.connect(self._remove_attachment)

        self._attachment_layout.insertWidget(
            self._attachment_layout.count() - 1,
            item
        )

        self._attachment_area.setVisible(True)

    def _remove_attachment(self, file_path: str):
        """移除附件"""
        self._attachments = [a for a in self._attachments if a.file_path != file_path]

        for i in range(self._attachment_layout.count() - 1):
            widget = self._attachment_layout.itemAt(i).widget()
            if isinstance(widget, AttachmentItem) and widget.file_path == file_path:
                widget.deleteLater()
                break

        if not self._attachments:
            self._attachment_area.setVisible(False)

    def _on_send(self):
        """发送消息或停止生成"""
        if self._is_sending:
            # 停止生成
            self.stop_clicked.emit()
            return

        text = self._input_edit.toPlainText().strip()
        if not text and not self._attachments:
            return

        # 将附件数据转换为字典列表
        attach_dicts = [a.to_dict() for a in self._attachments]
        self.send_clicked.emit(text, attach_dicts)

        self._input_edit.clear()
        self._clear_attachments()

    def _clear_attachments(self):
        """清空所有附件"""
        self._attachments.clear()

        while self._attachment_layout.count() > 1:
            item = self._attachment_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._attachment_area.setVisible(False)

    def get_text(self) -> str:
        """获取输入文本"""
        return self._input_edit.toPlainText().strip()

    def get_attachments(self) -> List[AttachmentData]:
        """获取附件列表"""
        return self._attachments.copy()

    def is_deep_think_enabled(self) -> bool:
        """是否开启深度思考"""
        return self._deep_think_btn.isChecked()

    def is_search_enabled(self) -> bool:
        """是否开启智能搜索"""
        return self._search_btn.isChecked()

    def clear(self):
        """清空输入"""
        self._input_edit.clear()
        self._clear_attachments()
