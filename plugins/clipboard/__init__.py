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

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QUrl, QTimer
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import QFileDialog, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidgetItem, QHeaderView
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, TreeWidget, StrongBodyLabel,
    setCustomStyleSheet, isDarkTheme, qconfig, TextEdit,
    MessageBox, TransparentToolButton, CaptionLabel
)
from core import PluginInterface, get_app_data_path


class ClipboardWidget(QWidget):
    """剪切板历史组件"""
    
    PLUGIN_ID = "clipboard"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.clipboard_data: List[Dict[str, Any]] = []
        self.max_history = 100
        self._is_monitoring = True
        
        self._init_paths()
        self._setup_ui()
        self._load_clipboard_history()
        self._setup_clipboard_monitor()
    
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
        
        self.monitor_btn = TransparentToolButton(FIF.PLAY, self)
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
        
        self.tree = TreeWidget(self)
        self.tree.setHeaderLabels(["时间", "类型", "内容"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tree.setColumnWidth(0, 140)
        self.tree.setColumnWidth(1, 60)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemDoubleClicked.connect(self._copy_to_clipboard)
        self.tree.setSelectionMode(self.tree.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        
        self._apply_tree_style()
        qconfig.themeChangedFinished.connect(self._apply_tree_style)
        
        main_layout.addWidget(self.tree)
        
        self.status_label = CaptionLabel("就绪", self)
        main_layout.addWidget(self.status_label)
    
    def _apply_tree_style(self):
        """应用树形列表样式"""
        header = self.tree.header()
        
        if isDarkTheme():
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: transparent;
                    alternate-background-color: #252525;
                    border: none;
                }
                QTreeWidget::item {
                    padding: 6px;
                    border-radius: 4px;
                }
                QTreeWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QTreeWidget::item:hover {
                    background-color: #3d3d3d;
                }
            """)
            header.setStyleSheet("""
                QHeaderView::section {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: none;
                    border-bottom: 1px solid #3d3d3d;
                    padding: 8px;
                    font-weight: 500;
                }
            """)
        else:
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: transparent;
                    alternate-background-color: #f5f5f5;
                    border: none;
                }
                QTreeWidget::item {
                    padding: 6px;
                    border-radius: 4px;
                }
                QTreeWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QTreeWidget::item:hover {
                    background-color: #e5e5e5;
                }
            """)
            header.setStyleSheet("""
                QHeaderView::section {
                    background-color: #ffffff;
                    color: #000000;
                    border: none;
                    border-bottom: 1px solid #e0e0e0;
                    padding: 8px;
                    font-weight: 500;
                }
            """)
    
    def _setup_clipboard_monitor(self):
        """设置剪切板监控"""
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_change)
    
    def _toggle_monitor(self):
        """切换监控状态"""
        self._is_monitoring = not self._is_monitoring
        if self._is_monitoring:
            self.monitor_btn.setIcon(FIF.PLAY)
            self.monitor_btn.setToolTip("暂停监控")
            self.status_label.setText("监控已开启")
        else:
            self.monitor_btn.setIcon(FIF.PAUSE)
            self.monitor_btn.setToolTip("继续监控")
            self.status_label.setText("监控已暂停")
    
    def _on_clipboard_change(self):
        """剪切板内容变化时的处理"""
        if not self._is_monitoring:
            return
        
        mime_data = self.clipboard.mimeData()
        
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
            self.clipboard_data[0]['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            item_data = {
                "type": "text",
                "content": text,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.clipboard_data.insert(0, item_data)
            
            if len(self.clipboard_data) > self.max_history:
                self.clipboard_data.pop()
        
        self._save_clipboard_history()
        self._update_tree_view()
    
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
        
        self.clipboard_data.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "image",
            "content": image_data,
            "format": "png"
        })
        
        if len(self.clipboard_data) > self.max_history:
            self.clipboard_data = self.clipboard_data[:self.max_history]
        
        self._save_clipboard_history()
        self._update_tree_view()
    
    def _add_urls_to_history(self, urls):
        """添加URLs到剪切板历史"""
        paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
        
        if not paths:
            return
        
        if self.clipboard_data and self.clipboard_data[0].get("type") == "urls" and self.clipboard_data[0].get("content") == paths:
            return
        
        self.clipboard_data.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "urls",
            "content": paths
        })
        
        if len(self.clipboard_data) > self.max_history:
            self.clipboard_data = self.clipboard_data[:self.max_history]
        
        self._save_clipboard_history()
        self._update_tree_view()
    
    def _update_tree_view(self):
        """更新树形视图"""
        self.tree.clear()
        
        for item_data in self.clipboard_data:
            tree_item = QTreeWidgetItem()
            tree_item.setText(0, item_data["timestamp"])
            
            content_type = item_data.get("type", "text")
            if content_type == "text":
                preview = item_data["content"][:80] + "..." if len(item_data["content"]) > 80 else item_data["content"]
                type_text = "文本"
            elif content_type == "image":
                preview = "[图片]"
                type_text = "图片"
            elif content_type == "urls":
                if isinstance(item_data["content"], list) and item_data["content"]:
                    if len(item_data["content"]) == 1:
                        preview = os.path.basename(item_data['content'][0])
                    else:
                        preview = f"{len(item_data['content'])} 个文件"
                else:
                    preview = "[文件]"
                type_text = "文件"
            else:
                preview = "[未知]"
                type_text = "未知"
            
            tree_item.setText(1, type_text)
            tree_item.setText(2, preview.replace('\n', ' '))
            tree_item.setData(0, Qt.UserRole, item_data)
            self.tree.addTopLevelItem(tree_item)
    
    def _copy_to_clipboard(self, item: QTreeWidgetItem, column: int):
        """复制选中项到剪切板"""
        item_data = item.data(0, Qt.UserRole)
        
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
        from PyQt5.QtWidgets import QMenu, QAction
        
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)
        
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(lambda: self._copy_to_clipboard(item, 0))
        menu.addAction(copy_action)
        
        pin_action = QAction("置顶", self)
        pin_action.triggered.connect(lambda: self._pin_item(item))
        menu.addAction(pin_action)
        
        menu.addSeparator()
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_item(item))
        menu.addAction(delete_action)
        
        menu.exec_(QCursor.pos())
    
    def _pin_item(self, item: QTreeWidgetItem):
        """置顶选中项"""
        index = self.tree.indexOfTopLevelItem(item)
        if index > 0:
            item_data = self.clipboard_data.pop(index)
            self.clipboard_data.insert(0, item_data)
            self._update_tree_view()
            self._save_clipboard_history()
            self.status_label.setText("已置顶")
    
    def _delete_item(self, item: QTreeWidgetItem):
        """删除选中项"""
        index = self.tree.indexOfTopLevelItem(item)
        if index >= 0:
            self.clipboard_data.pop(index)
            self.tree.takeTopLevelItem(index)
            self._save_clipboard_history()
            self.status_label.setText("已删除")
    
    def _clear_history(self):
        """清空剪切板历史"""
        box = MessageBox("确认清空", "确定要清空所有剪切板历史记录吗？", self)
        if box.exec():
            self.clipboard_data.clear()
            self._save_clipboard_history()
            self._update_tree_view()
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
        
        self.tree.clear()
        
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
                tree_item = QTreeWidgetItem()
                tree_item.setText(0, item_data["timestamp"])
                
                if content_type == "text":
                    preview = item_data["content"][:80] + "..." if len(item_data["content"]) > 80 else item_data["content"]
                    type_text = "文本"
                elif content_type == "image":
                    preview = "[图片]"
                    type_text = "图片"
                elif content_type == "urls":
                    if isinstance(item_data["content"], list) and item_data["content"]:
                        preview = os.path.basename(item_data['content'][0]) if len(item_data['content']) == 1 else f"{len(item_data['content'])} 个文件"
                    else:
                        preview = "[文件]"
                    type_text = "文件"
                else:
                    preview = "[未知]"
                    type_text = "未知"
                
                tree_item.setText(1, type_text)
                tree_item.setText(2, preview.replace('\n', ' '))
                tree_item.setData(0, Qt.UserRole, item_data)
                self.tree.addTopLevelItem(tree_item)
    
    def _add_and_pin_text(self):
        """添加并置顶文本"""
        text = self.edit_input.text().strip()
        if not text:
            return
        
        self._add_text_to_history(text)
        self.edit_input.clear()
        self.status_label.setText("已添加文本")
    
    def _save_clipboard_history(self):
        """保存剪切板历史到文件"""
        try:
            temp_file = str(self.json_file) + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.clipboard_data, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, str(self.json_file))
        except Exception as e:
            self.core.logger.error(f"保存剪切板历史失败: {e}")
    
    def _load_clipboard_history(self):
        """从文件加载剪切板历史"""
        try:
            if self.json_file.exists():
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "type" not in item:
                                item["type"] = "text"
                        self.clipboard_data = data
        except Exception as e:
            self.core.logger.error(f"加载剪切板历史失败: {e}")
            self.clipboard_data = []
    
    def load_data(self) -> None:
        """加载数据"""
        self._load_clipboard_history()
        self._update_tree_view()
    
    def showEvent(self, event):
        """窗口显示时刷新"""
        super().showEvent(event)
        self._load_clipboard_history()
        self._update_tree_view()


class Plugin(PluginInterface):
    """剪切板插件"""
    
    PLUGIN_ID = "clipboard"
    PLUGIN_NAME = "剪切板"
    PLUGIN_ICON = FIF.COPY
    PLUGIN_PRIORITY = 7
    
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
