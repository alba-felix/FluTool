"""
剪切板插件
提供剪切板历史记录管理功能，支持文本、图片、文件
"""
import os
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QUrl, QTimer, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon, QPainter, QColor, QFont
from PyQt5.QtWidgets import QFileDialog, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QFrame, QSplitter
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, StrongBodyLabel,
    setCustomStyleSheet, isDarkTheme, qconfig, TextEdit,
    MessageBox, TransparentToolButton, CaptionLabel,
    RoundMenu, SubtitleLabel, BodyLabel, ScrollArea
)
from core import PluginInterface, get_app_data_path
from storage.database import DatabaseManager


THUMBNAIL_SIZE = 80


class ClipboardItemWidget(QWidget):
    """剪切板列表项组件"""
    
    def __init__(self, item_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self._setup_ui()
    
    def _setup_ui(self):
        """构建界面"""
        self.setFixedHeight(90)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        content_type = self.item_data.get("type", "text")
        
        # 缩略图/图标区域
        self.thumb_label = QLabel(self)
        self.thumb_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setObjectName("thumbLabel")
        
        if content_type == "image":
            thumbnail = self._create_thumbnail(self.item_data.get("content", ""))
            if thumbnail:
                self.thumb_label.setPixmap(thumbnail)
            else:
                self.thumb_label.setText("📷")
                self.thumb_label.setStyleSheet("font-size: 32px;")
        elif content_type == "text":
            self.thumb_label.setText("📝")
            self.thumb_label.setStyleSheet("font-size: 32px;")
        elif content_type == "urls":
            self.thumb_label.setText("📁")
            self.thumb_label.setStyleSheet("font-size: 32px;")
        
        layout.addWidget(self.thumb_label)
        
        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # 时间和类型
        header_layout = QHBoxLayout()
        time_label = CaptionLabel(self.item_data.get("timestamp", ""), self)
        time_label.setObjectName("timeLabel")
        header_layout.addWidget(time_label)
        
        type_label = CaptionLabel(self._get_type_text(), self)
        type_label.setObjectName("typeLabel")
        header_layout.addWidget(type_label)
        header_layout.addStretch()
        
        info_layout.addLayout(header_layout)
        
        # 预览内容
        preview_text = self._get_preview_text()
        self.preview_label = BodyLabel(preview_text, self)
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMaximumHeight(40)
        info_layout.addWidget(self.preview_label, 1)
        
        layout.addLayout(info_layout, 1)
        
        self._apply_style()
    
    def _create_thumbnail(self, base64_data: str) -> Optional[QPixmap]:
        """从 base64 数据创建缩略图"""
        try:
            image_data = base64.b64decode(base64_data)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data, "PNG")
            
            if pixmap.isNull():
                return None
            
            return pixmap.scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
        except Exception:
            return None
    
    def _get_type_text(self) -> str:
        """获取类型文本"""
        content_type = self.item_data.get("type", "text")
        type_map = {
            "text": "文本",
            "image": "图片",
            "urls": "文件"
        }
        return type_map.get(content_type, "未知")
    
    def _get_preview_text(self) -> str:
        """获取预览文本"""
        content_type = self.item_data.get("type", "text")
        
        if content_type == "text":
            text = self.item_data.get("content", "")
            return text[:100] + "..." if len(text) > 100 else text
        elif content_type == "image":
            size_info = self._get_image_size(self.item_data.get("content", ""))
            return f"图片尺寸: {size_info}" if size_info else "图片"
        elif content_type == "urls":
            content = self.item_data.get("content", [])
            if isinstance(content, list):
                if len(content) == 1:
                    return os.path.basename(content[0])
                return f"{len(content)} 个文件"
        return ""
    
    def _get_image_size(self, base64_data: str) -> str:
        """获取图片尺寸"""
        try:
            image_data = base64.b64decode(base64_data)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data, "PNG")
            return f"{pixmap.width()}x{pixmap.height()}"
        except Exception:
            return ""
    
    def _apply_style(self):
        """应用样式"""
        dark = isDarkTheme()
        
        bg = "#2d2d2d" if dark else "#ffffff"
        border = "#3d3d3d" if dark else "#e0e0e0"
        text_color = "#ffffff" if dark else "#1f1f1f"
        secondary_color = "#888888" if dark else "#666666"
        accent_bg = "rgba(0,120,212,0.15)" if dark else "rgba(0,120,212,0.1)"
        
        self.setStyleSheet(f"""
            ClipboardItemWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            #thumbLabel {{
                background-color: {"#1e1e1e" if dark else "#f5f5f5"};
                border-radius: 6px;
            }}
            #timeLabel {{
                color: {secondary_color};
                font-size: 11px;
            }}
            #typeLabel {{
                color: #0078d4;
                font-size: 11px;
                background: {accent_bg};
                padding: 2px 8px;
                border-radius: 4px;
            }}
            #previewLabel {{
                color: {text_color};
                font-size: 13px;
            }}
        """)


class ClipboardWidget(QWidget):
    """剪切板历史组件"""
    
    PLUGIN_ID = "clipboard"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.db = DatabaseManager()
        self.clipboard_data: List[Dict[str, Any]] = []
        self.max_history = 100
        self._is_monitoring = True
        self._monitor_initialized = False
        
        self._init_paths()
        self._setup_ui()
    
    def showEvent(self, event):
        """窗口显示时初始化"""
        super().showEvent(event)
        if not self._monitor_initialized:
            self._load_clipboard_history()
            self._setup_clipboard_monitor()
            self._update_list_view()
            self._monitor_initialized = True
    
    def _init_paths(self):
        """初始化路径"""
        self.data_dir = get_app_data_path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.json_file = self.data_dir / "clipboard.json"
    
    def _setup_ui(self):
        """构建界面"""
        self.setObjectName("clipboardWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索剪切板历史...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._search_clipboard)
        header_layout.addWidget(self.search_input, 1)
        
        self.monitor_btn = TransparentToolButton(FIF.PAUSE, self)
        self.monitor_btn.setToolTip("暂停监控")
        self.monitor_btn.clicked.connect(self._toggle_monitor)
        header_layout.addWidget(self.monitor_btn)
        
        clear_btn = TransparentToolButton(FIF.DELETE, self)
        clear_btn.setToolTip("清空历史")
        clear_btn.clicked.connect(self._clear_history)
        header_layout.addWidget(clear_btn)
        
        export_btn = TransparentToolButton(FIF.SAVE, self)
        export_btn.setToolTip("导出")
        export_btn.clicked.connect(self._export_history)
        header_layout.addWidget(export_btn)
        
        main_layout.addLayout(header_layout)
        
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        self.edit_input = LineEdit(self)
        self.edit_input.setPlaceholderText("输入文本，按回车添加到剪切板...")
        self.edit_input.returnPressed.connect(self._add_and_pin_text)
        input_layout.addWidget(self.edit_input, 1)
        
        add_btn = PushButton("添加", self)
        add_btn.setIcon(FIF.ADD)
        add_btn.clicked.connect(self._add_and_pin_text)
        input_layout.addWidget(add_btn)
        
        main_layout.addLayout(input_layout)
        
        # 使用 QListWidget 显示缩略图列表
        self.list_widget = QListWidget(self)
        self.list_widget.setSpacing(8)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        self._apply_list_style()
        qconfig.themeChangedFinished.connect(self._apply_list_style)
        
        main_layout.addWidget(self.list_widget)
        
        self.status_label = CaptionLabel("就绪", self)
        main_layout.addWidget(self.status_label)
    
    def _apply_list_style(self):
        """应用列表样式"""
        dark = isDarkTheme()
        
        bg = "transparent" if dark else "transparent"
        scroll_bg = "#2d2d2d" if dark else "#f0f0f0"
        scroll_handle = "#4d4d4d" if dark else "#c0c0c0"
        
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {scroll_bg};
                width: 10px;
                border-radius: 5px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {scroll_handle};
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
    
    def _setup_clipboard_monitor(self):
        """设置剪切板监控"""
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_change)
        self._last_clipboard_hash = None
        self._clipboard_check_timer = QTimer(self)
        self._clipboard_check_timer.timeout.connect(self._check_clipboard_content)
        self._clipboard_check_timer.start(500)
    
    def _check_clipboard_content(self):
        """定时检查剪切板内容（确保最小化时也能捕获）"""
        if not self._is_monitoring:
            return
        
        mime_data = self.clipboard.mimeData()
        if not mime_data:
            return
        
        current_hash = self._calculate_mime_hash(mime_data)
        if current_hash and current_hash != self._last_clipboard_hash:
            self._last_clipboard_hash = current_hash
            self._on_clipboard_change()
    
    def _calculate_mime_hash(self, mime_data) -> Optional[str]:
        """计算剪切板内容的哈希值"""
        if mime_data.hasImage():
            image = mime_data.imageData()
            if isinstance(image, QImage):
                return f"img_{image.width()}_{image.height()}_{image.sizeInBytes()}"
        elif mime_data.hasText():
            text = mime_data.text()
            return f"text_{hash(text)}"
        elif mime_data.hasUrls():
            urls = mime_data.urls()
            return f"urls_{hash(tuple(str(u.toString()) for u in urls))}"
        return None
    
    def _toggle_monitor(self):
        """切换监控状态"""
        self._is_monitoring = not self._is_monitoring
        if self._is_monitoring:
            self.monitor_btn.setIcon(FIF.PAUSE)
            self.monitor_btn.setToolTip("暂停监控")
            self.status_label.setText("监控已开启")
        else:
            self.monitor_btn.setIcon(FIF.PLAY)
            self.monitor_btn.setToolTip("继续监控")
            self.status_label.setText("监控已暂停")
    
    def _on_clipboard_change(self):
        """剪切板内容变化时的处理"""
        if not self._is_monitoring:
            return
        
        mime_data = self.clipboard.mimeData()
        current_hash = self._calculate_mime_hash(mime_data)
        
        if current_hash and current_hash == self._last_clipboard_hash:
            return
        
        self._last_clipboard_hash = current_hash
        
        if mime_data.hasImage():
            image = mime_data.imageData()
            self._add_image_to_history(image)
        elif mime_data.hasUrls():
            urls = mime_data.urls()
            self._add_urls_to_history(urls)
        elif mime_data.hasText():
            text = mime_data.text()
            if text.strip():
                self._add_text_to_history(text)
    
    def _add_text_to_history(self, text: str):
        """添加文本到历史记录"""
        if self.clipboard_data and self.clipboard_data[0].get('type') == 'text' and self.clipboard_data[0].get('content') == text:
            return
        
        item_id = self.db.add_clipboard_item("text", text)
        item_data = {
            "id": item_id,
            "type": "text",
            "content": text,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.clipboard_data.insert(0, item_data)
        
        if len(self.clipboard_data) > self.max_history:
            removed = self.clipboard_data.pop()
            if 'id' in removed:
                self.db.delete_clipboard_item(removed['id'])
        
        self._update_list_view()
    
    def _add_image_to_history(self, image):
        """添加图片到剪切板历史"""
        if isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        elif isinstance(image, QPixmap):
            pixmap = image
        else:
            return
        
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        image_data = byte_array.toBase64().data().decode()
        
        item_id = self.db.add_clipboard_item("image", image_data, "png")
        self.clipboard_data.insert(0, {
            "id": item_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "image",
            "content": image_data,
            "format": "png"
        })
        
        if len(self.clipboard_data) > self.max_history:
            removed = self.clipboard_data.pop()
            if 'id' in removed:
                self.db.delete_clipboard_item(removed['id'])
        
        self._update_list_view()
    
    def _add_urls_to_history(self, urls):
        """添加URLs到剪切板历史"""
        paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        
        if not paths:
            return
        
        if self.clipboard_data and self.clipboard_data[0].get("type") == "urls" and self.clipboard_data[0].get("content") == paths:
            return
        
        item_id = self.db.add_clipboard_item("urls", json.dumps(paths))
        self.clipboard_data.insert(0, {
            "id": item_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "urls",
            "content": paths
        })
        
        if len(self.clipboard_data) > self.max_history:
            removed = self.clipboard_data.pop()
            if 'id' in removed:
                self.db.delete_clipboard_item(removed['id'])
        
        self._update_list_view()
    
    def _update_list_view(self):
        """更新列表视图"""
        self.list_widget.clear()
        
        for item_data in self.clipboard_data:
            list_item = QListWidgetItem(self.list_widget)
            item_widget = ClipboardItemWidget(item_data, self)
            list_item.setSizeHint(item_widget.sizeHint())
            list_item.setData(Qt.UserRole, item_data)
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """单击项"""
        pass
    
    def _on_item_double_clicked(self, item: QListWidgetItem):
        """双击项 - 复制到剪切板"""
        self._copy_item_to_clipboard(item)
    
    def _copy_item_to_clipboard(self, item: QListWidgetItem):
        """复制项到剪切板"""
        item_data = item.data(Qt.UserRole)
        
        if not isinstance(item_data, dict):
            return
        
        content_type = item_data.get("type", "text")
        
        try:
            if content_type == "text":
                self.clipboard.setText(item_data["content"])
                self.status_label.setText("已复制文本到剪切板")
            elif content_type == "image":
                image_data = base64.b64decode(item_data["content"])
                pixmap = QPixmap()
                pixmap.loadFromData(image_data, "PNG")
                self.clipboard.setPixmap(pixmap)
                self.status_label.setText("已复制图片到剪切板")
            elif content_type == "urls":
                urls = [QUrl.fromLocalFile(path) for path in item_data["content"]]
                mime_data = self.clipboard.mimeData().__class__()
                mime_data.setUrls(urls)
                self.clipboard.setMimeData(mime_data)
                self.status_label.setText(f"已复制 {len(urls)} 个文件到剪切板")
            
            InfoBar.success(
                title="复制成功",
                content=self.status_label.text(),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="复制失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _show_context_menu(self, pos):
        """显示右键菜单"""
        from PyQt5.QtGui import QCursor
        from PyQt5.QtWidgets import QAction
        
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        
        menu = RoundMenu(parent=self)
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(lambda: self._copy_item_to_clipboard(item))
        menu.addAction(copy_action)
        
        pin_action = QAction("置顶", self)
        pin_action.triggered.connect(lambda: self._pin_item(item))
        menu.addAction(pin_action)
        
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_item(item))
        menu.addAction(delete_action)
        
        menu.exec(QCursor.pos())
    
    def _pin_item(self, item: QListWidgetItem):
        """置顶选中项"""
        row = self.list_widget.row(item)
        if row > 0:
            item_data = self.clipboard_data.pop(row)
            self.clipboard_data.insert(0, item_data)
            self._update_list_view()
            self.status_label.setText("已置顶")
    
    def _delete_item(self, item: QListWidgetItem):
        """删除选中项"""
        row = self.list_widget.row(item)
        if row >= 0:
            item_data = self.clipboard_data.pop(row)
            if 'id' in item_data:
                self.db.delete_clipboard_item(item_data['id'])
            self.list_widget.takeItem(row)
            self.status_label.setText("已删除")
    
    def _clear_history(self):
        """清空剪切板历史"""
        box = MessageBox("确认清空", "确定要清空所有剪切板历史记录吗？", self)
        if box.exec():
            self.db.clear_clipboard_history()
            self.clipboard_data.clear()
            self._update_list_view()
            self.status_label.setText("已清空剪切板历史")
            InfoBar.success(
                title="清空成功",
                content="已清空所有剪切板历史记录",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _export_history(self):
        """导出剪切板历史"""
        if not self.clipboard_data:
            InfoBar.warning(
                title="导出失败",
                content="没有历史记录可导出",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出剪切板历史", "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.clipboard_data, f, ensure_ascii=False, indent=2)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for entry in self.clipboard_data:
                            if entry.get('type') == 'text':
                                f.write(f"[{entry['timestamp']}] {entry['content']}\n")
                
                InfoBar.success(
                    title="导出成功",
                    content=f"已导出 {len(self.clipboard_data)} 条记录",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            except Exception as e:
                InfoBar.error(
                    title="导出失败",
                    content=str(e),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _search_clipboard(self):
        """搜索剪切板历史"""
        search_text = self.search_input.text().lower()
        
        self.list_widget.clear()
        
        for item_data in self.clipboard_data:
            content_type = item_data.get("type", "text")
            match = False
            
            if content_type == "text":
                content = item_data["content"].lower()
                if search_text in content or search_text in item_data["timestamp"].lower():
                    match = True
            elif content_type == "image":
                if search_text in "图片 image" or search_text in item_data["timestamp"].lower():
                    match = True
            elif content_type == "urls":
                if isinstance(item_data["content"], list):
                    content = " ".join(item_data["content"]).lower()
                    if search_text in content or search_text in item_data["timestamp"].lower():
                        match = True
            
            if match or not search_text:
                list_item = QListWidgetItem(self.list_widget)
                item_widget = ClipboardItemWidget(item_data, self)
                list_item.setSizeHint(item_widget.sizeHint())
                list_item.setData(Qt.UserRole, item_data)
                self.list_widget.addItem(list_item)
                self.list_widget.setItemWidget(list_item, item_widget)
    
    def _add_and_pin_text(self):
        """添加并置顶文本"""
        text = self.edit_input.text().strip()
        if not text:
            return
        
        self._add_text_to_history(text)
        self.edit_input.clear()
        self.status_label.setText("已添加文本")
    
    def _load_clipboard_history(self):
        """从数据库加载剪切板历史"""
        try:
            data = self.db.get_clipboard_history(self.max_history)
            self.clipboard_data = []
            for item in data:
                item_data = {
                    "id": item["id"],
                    "type": item["type"],
                    "content": item["content"],
                    "timestamp": item["timestamp"]
                }
                if item.get("format"):
                    item_data["format"] = item["format"]
                if item["type"] == "urls":
                    item_data["content"] = json.loads(item["content"])
                self.clipboard_data.append(item_data)
        except Exception as e:
            self.core.logger.error(f"加载剪切板历史失败: {e}")
            self.clipboard_data = []
    
    def load_data(self) -> None:
        """加载数据"""
        if self._monitor_initialized:
            self._load_clipboard_history()
            self._update_list_view()


class Plugin(PluginInterface):
    """剪切板插件"""
    
    PLUGIN_ID = "clipboard"
    PLUGIN_NAME = "剪切板"
    PLUGIN_ICON = FIF.COPY
    PLUGIN_PRIORITY = 10
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return ClipboardWidget(self.core, parent)
    
    def load_data(self) -> None:
        """加载数据"""
        if self._widget:
            self._widget.load_data()
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        from core import SearchResult
        db = DatabaseManager()
        results = []
        items = db.search_clipboard(query)
        for item in items[:20]:
            content = item['content']
            if len(content) > 100:
                content = content[:100] + '...'
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=content,
                description=f"类型: {item['type']} | 时间: {item['timestamp']}",
                icon=self.PLUGIN_ICON,
                relevance=1.0,
                action=lambda c=content: QApplication.clipboard().setText(c),
                metadata={'item_id': item['id']}
            )
            results.append(result)
        return results
