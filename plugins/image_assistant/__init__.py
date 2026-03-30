"""
图片助手插件
提供图片管理功能，支持粘贴、预览、缩放、导出等
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import Qt, QBuffer, QByteArray, QIODevice, QUrl, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon, QCursor
from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
    QStatusBar, QApplication
)
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, setCustomStyleSheet, isDarkTheme, qconfig,
    TransparentToolButton, CaptionLabel, SubtitleLabel, BodyLabel, ScrollArea
)
from core import PluginInterface, get_app_data_path
from ui import CustomFluentIcon


class ImagePreviewWidget(QWidget):
    """图片预览组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale_factor = 1.0
        self._original_pixmap = None
        self._setup_ui()
    
    def _setup_ui(self):
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 使用 QScrollArea（标准 Qt 组件，避免 qfluentwidgets 可能的干扰）
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(False)  # 关键：不要自动调整内容大小
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        # 滚动内容容器
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        
        # 内容布局 - 使用 QHBoxLayout 并居中
        content_layout = QHBoxLayout(self.scroll_content)
        content_layout.setContentsMargins(20, 20, 20, 20)  # 留边距，视觉更好
        content_layout.setAlignment(Qt.AlignCenter)
        
        # 预览标签
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setScaledContents(False)
        content_layout.addWidget(self.preview_label)
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)
        
        # 信息栏
        info_layout = QHBoxLayout()
        info_layout.setSpacing(20)
        
        self.size_label = BodyLabel("尺寸: -", self)
        info_layout.addWidget(self.size_label)
        
        self.file_size_label = BodyLabel("大小: -", self)
        info_layout.addWidget(self.file_size_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        self._apply_style()
    
    def _apply_style(self):
        """应用样式（根据主题）"""
        if isDarkTheme():
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background-color: #252525;
                }
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical {
                    background-color: #4d4d4d;
                    border-radius: 5px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #5d5d5d;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
                QScrollBar:horizontal {
                    background-color: #2d2d2d;
                    height: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #4d4d4d;
                    border-radius: 5px;
                    min-width: 30px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #5d5d5d;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    background: none;
                    width: 0px;
                }
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                    background: none;
                }
            """)
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #252525;
                    border: 2px dashed #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: transparent;
                    border: none;
                }
                QScrollArea > QWidget > QWidget {
                    background-color: #ffffff;
                }
                QScrollBar:vertical {
                    background-color: #f0f0f0;
                    width: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:vertical {
                    background-color: #c0c0c0;
                    border-radius: 5px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #a0a0a0;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    background: none;
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
                QScrollBar:horizontal {
                    background-color: #f0f0f0;
                    height: 12px;
                    border-radius: 6px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #c0c0c0;
                    border-radius: 5px;
                    min-width: 30px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #a0a0a0;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    background: none;
                    width: 0px;
                }
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                    background: none;
                }
            """)
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    border: 2px dashed #d0d0d0;
                    border-radius: 8px;
                }
            """)
    
    def set_image(self, pixmap: QPixmap):
        """设置图片"""
        self._original_pixmap = pixmap
        self._scale_factor = 1.0
        self._update_info(pixmap)
        self.fit_to_window()
    
    def _update_preview(self):
        """更新预览"""
        if not self._original_pixmap:
            return
        
        # 计算缩放后的尺寸
        scaled_size = self._original_pixmap.size() * self._scale_factor
        scaled_pixmap = self._original_pixmap.scaled(
            scaled_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 设置预览图片
        self.preview_label.setPixmap(scaled_pixmap)
        
        # 关键：固定标签和内容容器的大小，使滚动区域感知内容大小
        self.preview_label.setFixedSize(scaled_pixmap.size())
        # 内容容器大小 = 标签大小 + 边距
        content_margins = self.scroll_content.layout().contentsMargins()
        total_width = scaled_pixmap.width() + content_margins.left() + content_margins.right()
        total_height = scaled_pixmap.height() + content_margins.top() + content_margins.bottom()
        self.scroll_content.setFixedSize(total_width, total_height)
    
    def _update_info(self, pixmap: QPixmap):
        """更新信息"""
        size = pixmap.size()
        self.size_label.setText(f"尺寸: {size.width()} x {size.height()}")
        
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        file_size = buffer.size()
        self.file_size_label.setText(f"大小: {self._format_size(file_size)}")
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} GB"
    
    def zoom_in(self):
        """放大"""
        self._scale_factor = min(self._scale_factor * 1.2, 5.0)
        self._update_preview()
    
    def zoom_out(self):
        """缩小"""
        self._scale_factor = max(self._scale_factor / 1.2, 0.1)
        self._update_preview()
    
    def fit_to_window(self):
        """自适应窗口"""
        if not self._original_pixmap:
            return
        
        # 获取滚动区域视口大小
        viewport_size = self.scroll_area.viewport().size()
        # 减去内容边距
        margins = self.scroll_content.layout().contentsMargins()
        available_width = viewport_size.width() - margins.left() - margins.right()
        available_height = viewport_size.height() - margins.top() - margins.bottom()
        
        img_size = self._original_pixmap.size()
        scale_x = available_width / img_size.width()
        scale_y = available_height / img_size.height()
        self._scale_factor = min(scale_x, scale_y, 1.0)
        self._update_preview()
    
    def reset_scale(self):
        """重置缩放"""
        self._scale_factor = 1.0
        self._update_preview()
    
    def get_pixmap(self) -> Optional[QPixmap]:
        """获取当前显示的图片"""
        return self.preview_label.pixmap()


class ImageAssistantWidget(QWidget):
    """图片助手主组件"""
    
    PLUGIN_ID = "image_assistant"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.images: List[Dict[str, Any]] = []
        self._current_image_index = -1
        
        self._init_paths()
        self._setup_ui()
        self._load_images()
        self._setup_clipboard_monitor()
    
    def _init_paths(self):
        """初始化路径"""
        self.data_dir = get_app_data_path("data/img")
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _setup_ui(self):
        """构建界面"""
        self.setObjectName("imageAssistantWidget")
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)
        
        self.paste_btn = PushButton("粘贴", self)
        self.paste_btn.setIcon(FIF.PASTE)
        self.paste_btn.clicked.connect(self._paste_from_clipboard)
        toolbar_layout.addWidget(self.paste_btn)
        
        self.add_btn = PushButton("添加", self)
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self._add_image)
        toolbar_layout.addWidget(self.add_btn)
        
        self.delete_btn = PushButton("删除", self)
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.clicked.connect(self._delete_image)
        toolbar_layout.addWidget(self.delete_btn)
        
        self.copy_btn = PushButton("复制", self)
        self.copy_btn.setIcon(FIF.COPY)
        self.copy_btn.clicked.connect(self._copy_image)
        toolbar_layout.addWidget(self.copy_btn)
        
        self.save_btn = PushButton("另存为", self)
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.clicked.connect(self._save_image)
        toolbar_layout.addWidget(self.save_btn)
        
        toolbar_layout.addStretch()
        
        self.zoom_in_btn = TransparentToolButton(FIF.ZOOM_IN, self)
        self.zoom_in_btn.setToolTip("放大")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        toolbar_layout.addWidget(self.zoom_in_btn)
        
        self.zoom_out_btn = TransparentToolButton(FIF.ZOOM_OUT, self)
        self.zoom_out_btn.setToolTip("缩小")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        toolbar_layout.addWidget(self.zoom_out_btn)
        
        self.fit_btn = TransparentToolButton(FIF.FULL_SCREEN, self)
        self.fit_btn.setToolTip("自适应")
        self.fit_btn.clicked.connect(self._fit_to_window)
        toolbar_layout.addWidget(self.fit_btn)
        
        self.reset_btn = TransparentToolButton(FIF.SYNC, self)
        self.reset_btn.setToolTip("原始大小")
        self.reset_btn.clicked.connect(self._reset_scale)
        toolbar_layout.addWidget(self.reset_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        left_layout.addWidget(SubtitleLabel("图片列表", left_widget))
        
        self.image_list = QListWidget(left_widget)
        self.image_list.setIconSize(QSize(80, 80))
        self.image_list.setSpacing(8)
        self.image_list.itemClicked.connect(self._on_image_selected)
        self.image_list.itemDoubleClicked.connect(self._on_image_double_clicked)
        left_layout.addWidget(self.image_list)
        
        self._apply_list_style()
        qconfig.themeChangedFinished.connect(self._apply_list_style)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        right_layout.addWidget(SubtitleLabel("图片预览", right_widget))
        
        self.preview_widget = ImagePreviewWidget(right_widget)
        right_layout.addWidget(self.preview_widget)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([180, 620])  # 初始大小
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        self.status_bar = QStatusBar(self)
        self.status_bar.setMaximumHeight(30)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                border-top: 1px solid #3d3d3d;
            }
        """)
        main_layout.addWidget(self.status_bar)
        
        self._apply_style()
        qconfig.themeChangedFinished.connect(self._apply_style)
    
    def _apply_style(self):
        """应用样式"""
        if isDarkTheme():
            self.setStyleSheet("""
                QWidget#imageAssistantWidget {
                    background-color: #1e1e1e;
                }
            """)
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #2d2d2d;
                    border-top: 1px solid #3d3d3d;
                    color: #ffffff;
                }
            """)
            self.preview_widget.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #252525;
                    border: 2px dashed #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget#imageAssistantWidget {
                    background-color: #f5f5f5;
                }
            """)
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #ffffff;
                    border-top: 1px solid #e0e0e0;
                    color: #000000;
                }
            """)
            self.preview_widget.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #ffffff;
                    border: 2px dashed #d0d0d0;
                    border-radius: 8px;
                }
            """)
    
    def _apply_list_style(self):
        """应用列表样式"""
        if isDarkTheme():
            self.image_list.setStyleSheet("""
                QListWidget {
                    background-color: #2d2d2d;
                    border: none;
                }
                QListWidget::item {
                    padding: 8px;
                    border-radius: 4px;
                    margin: 2px;
                }
                QListWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QListWidget::item:hover {
                    background-color: #3d3d3d;
                }
            """)
        else:
            self.image_list.setStyleSheet("""
                QListWidget {
                    background-color: #ffffff;
                    border: none;
                }
                QListWidget::item {
                    padding: 8px;
                    border-radius: 4px;
                    margin: 2px;
                }
                QListWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
                QListWidget::item:hover {
                    background-color: #f0f0f0;
                }
            """)
    
    def _setup_clipboard_monitor(self):
        """设置剪切板监控"""
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self._on_clipboard_changed)
    
    def _on_clipboard_changed(self):
        """剪切板内容变化"""
        mime_data = self.clipboard.mimeData()
        if mime_data.hasImage():
            pixmap = self.clipboard.pixmap()
            if pixmap and not pixmap.isNull():
                self._add_image_from_pixmap(pixmap, "从剪切板粘贴")
    
    def _paste_from_clipboard(self):
        """从剪切板粘贴"""
        mime_data = self.clipboard.mimeData()
        if mime_data.hasImage():
            pixmap = self.clipboard.pixmap()
            if pixmap and not pixmap.isNull():
                self._add_image_from_pixmap(pixmap, "从剪切板粘贴")
        else:
            InfoBar.warning(
                title="提示",
                content="剪切板中没有图片",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _add_image(self):
        """添加图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;所有文件 (*.*)"
        )
        
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self._add_image_from_pixmap(pixmap, os.path.basename(file_path))
            else:
                InfoBar.error(
                    title="错误",
                    content="无法加载图片",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _add_image_from_pixmap(self, pixmap: QPixmap, source_name: str = ""):
        """从 QPixmap 添加图片"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"img_{timestamp}.png"
        save_path = self.data_dir / filename
        
        if pixmap.save(str(save_path), "PNG"):
            image_info = {
                "path": str(save_path),
                "filename": filename,
                "source": source_name,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.images.append(image_info)
            self._save_image_list()
            self._refresh_image_list()
            
            InfoBar.success(
                title="添加成功",
                content=f"已添加图片 {filename}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            InfoBar.error(
                title="错误",
                content="保存图片失败",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _delete_image(self):
        """删除图片"""
        if self._current_image_index < 0 or self._current_image_index >= len(self.images):
            return
        
        image_info = self.images[self._current_image_index]
        
        try:
            os.remove(image_info["path"])
            self.images.pop(self._current_image_index)
            self._save_image_list()
            self._refresh_image_list()
            self.preview_widget.set_image(QPixmap())
            self._current_image_index = -1
            
            InfoBar.success(
                title="删除成功",
                content=f"已删除图片 {image_info['filename']}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="删除失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _copy_image(self):
        """复制图片"""
        pixmap = self.preview_widget.get_pixmap()
        if pixmap:
            self.clipboard.setPixmap(pixmap)
            InfoBar.success(
                title="复制成功",
                content="已复制图片到剪切板",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _save_image(self):
        """另存为"""
        pixmap = self.preview_widget.get_pixmap()
        if not pixmap:
            return
        
        if self._current_image_index >= 0 and self._current_image_index < len(self.images):
            default_name = self.images[self._current_image_index]["filename"]
        else:
            default_name = "image.png"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            default_name,
            "PNG 文件 (*.png);;JPEG 文件 (*.jpg);;所有文件 (*.*)"
        )
        
        if file_path:
            if pixmap.save(file_path):
                InfoBar.success(
                    title="保存成功",
                    content=f"已保存到 {os.path.basename(file_path)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            else:
                InfoBar.error(
                    title="保存失败",
                    content="无法保存图片",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
    
    def _zoom_in(self):
        """放大"""
        self.preview_widget.zoom_in()
    
    def _zoom_out(self):
        """缩小"""
        self.preview_widget.zoom_out()
    
    def _fit_to_window(self):
        """自适应"""
        self.preview_widget.fit_to_window()
    
    def _reset_scale(self):
        """原始大小"""
        self.preview_widget.reset_scale()
    
    def _on_image_selected(self, item: QListWidgetItem):
        """选择图片"""
        index = self.image_list.row(item)
        self._current_image_index = index
        
        if index >= 0 and index < len(self.images):
            image_info = self.images[index]
            pixmap = QPixmap(image_info["path"])
            if not pixmap.isNull():
                self.preview_widget.set_image(pixmap)
                self.status_bar.showMessage(f"来源: {image_info['source']} | 添加时间: {image_info['added_at']}")
    
    def _on_image_double_clicked(self, item: QListWidgetItem):
        """双击图片"""
        self._on_image_selected(item)
    
    def _refresh_image_list(self):
        """刷新图片列表"""
        self.image_list.clear()
        
        for image_info in self.images:
            item = QListWidgetItem()
            item.setText(image_info["filename"])
            item.setIcon(QIcon(image_info["path"]))
            item.setData(Qt.UserRole, image_info)
            self.image_list.addItem(item)
        
        if self._current_image_index >= 0 and self._current_image_index < self.image_list.count():
            self.image_list.setCurrentRow(self._current_image_index)
    
    def _save_image_list(self):
        """保存图片列表"""
        list_file = self.data_dir / "image_list.json"
        try:
            with open(list_file, 'w', encoding='utf-8') as f:
                json.dump(self.images, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.core.logger.error(f"保存图片列表失败: {e}")
    
    def _load_images(self):
        """加载图片列表"""
        list_file = self.data_dir / "image_list.json"
        
        try:
            if list_file.exists():
                with open(list_file, 'r', encoding='utf-8') as f:
                    self.images = json.load(f)
                
                for image_info in self.images:
                    if not os.path.exists(image_info["path"]):
                        self.images.remove(image_info)
                
                self._save_image_list()
        except Exception as e:
            self.core.logger.error(f"加载图片列表失败: {e}")
            self.images = []
        
        self._refresh_image_list()
    
    def load_data(self) -> None:
        """加载数据"""
        self._load_images()


class Plugin(PluginInterface):
    """图片助手插件"""
    
    PLUGIN_ID = "image_assistant"
    PLUGIN_NAME = "图片助手"
    PLUGIN_ICON = CustomFluentIcon.PICTURE
    PLUGIN_PRIORITY = 9
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return ImageAssistantWidget(self.core, parent)
    
    def load_data(self) -> None:
        """加载数据"""
        if self._widget:
            self._widget.load_data()
