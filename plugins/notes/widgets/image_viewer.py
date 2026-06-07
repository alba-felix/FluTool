from typing import List
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QFrame,
    QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QColor
from qfluentwidgets import SubtitleLabel, PushButton, CaptionLabel, InfoBar, InfoBarPosition

from ..core.path_util import PathUtil


class ImageViewer(QDialog):
    """图片查看器对话框"""

    def __init__(self, images: List[str], title: str = '图片查看', parent=None):
        super().__init__(parent)
        self._images = images
        self._current_index = 0
        self._title = title
        self._original_pixmap = None
        self._zoom_factor = 1.0
        self._init_ui()
        self._connect_signals()
        self._show_image(0)

    def _init_ui(self):
        """初始化界面"""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1000, 700)
        self.resize(1000, 700)

        # 主容器
        self.widget = QFrame(self, objectName='centerWidget')
        self.widget.setStyleSheet("""
            #centerWidget {
                background-color: rgb(43, 43, 43);
                border-radius: 10px;
                border: 1px solid rgb(58, 58, 58);
            }
        """)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.widget, 1)

        # 内容布局
        vbox = QVBoxLayout(self.widget)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # 内容区域
        content_widget = QFrame(self.widget)
        content_widget.setStyleSheet("background-color: rgb(43, 43, 43); border: none;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(12)

        # 标题
        self.title_label = SubtitleLabel(self._title, content_widget)
        content_layout.addWidget(self.title_label)

        # 图片显示区（用 QScrollArea 包裹，防止大图遮挡按钮）
        self.scroll_area = QScrollArea(content_widget)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget {
                background-color: rgb(43, 43, 43);
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 4px;
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
                height: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4d4d4d;
                border-radius: 4px;
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

        self.scroll_content = QWidget()
        scroll_layout = QHBoxLayout(self.scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setAlignment(Qt.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)
        scroll_layout.addWidget(self.image_label)

        self.scroll_area.setWidget(self.scroll_content)
        content_layout.addWidget(self.scroll_area, 1)

        vbox.addWidget(content_widget, 1)

        # 底部按钮区域 — 导航、操作、关闭全在一行
        button_group = QFrame(self.widget)
        button_group.setObjectName('buttonGroup')
        button_group.setFixedHeight(73)
        button_group.setStyleSheet("""
            #buttonGroup {
                background-color: rgb(32, 32, 32);
                border-top: 1px solid rgb(29, 29, 29);
                border-left: none;
                border-right: none;
                border-bottom: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QPushButton {
                background-color: rgb(51, 51, 51);
                color: white;
                border: 1px solid rgb(48, 48, 48);
                border-radius: 5px;
                padding: 5px 9px 6px 9px;
                font: 14px "Segoe UI", "Microsoft YaHei", "PingFang SC";
                outline: none;
            }
            QPushButton:hover {
                background-color: rgb(50, 50, 50);
            }
            QPushButton:pressed {
                background-color: rgb(39, 39, 39);
                color: rgba(255, 255, 255, 0.63);
            }
            QPushButton:disabled {
                background-color: rgb(59, 59, 59);
                color: rgba(255, 255, 255, 0.63);
                border: 1px solid rgb(80, 80, 80);
            }
        """)

        btn_layout = QHBoxLayout(button_group)
        btn_layout.setContentsMargins(16, 8, 16, 8)
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self.prev_btn = PushButton('上一张', button_group)
        self.prev_btn.setFixedHeight(32)
        btn_layout.addWidget(self.prev_btn)

        self.page_label = CaptionLabel('1 / 1', button_group)
        btn_layout.addWidget(self.page_label)

        self.next_btn = PushButton('下一张', button_group)
        self.next_btn.setFixedHeight(32)
        btn_layout.addWidget(self.next_btn)

        btn_layout.addSpacing(16)

        self.zoom_in_btn = PushButton('放大', button_group)
        self.zoom_in_btn.setFixedHeight(32)
        btn_layout.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = PushButton('缩小', button_group)
        self.zoom_out_btn.setFixedHeight(32)
        btn_layout.addWidget(self.zoom_out_btn)

        self.reset_btn = PushButton('重置', button_group)
        self.reset_btn.setFixedHeight(32)
        btn_layout.addWidget(self.reset_btn)

        self.save_btn = PushButton('保存', button_group)
        self.save_btn.setFixedHeight(32)
        btn_layout.addWidget(self.save_btn)

        btn_layout.addSpacing(16)

        self.close_btn = PushButton('关闭', button_group)
        self.close_btn.setFixedHeight(32)
        self.close_btn.setMinimumWidth(80)
        btn_layout.addWidget(self.close_btn)

        btn_layout.addStretch()
        vbox.addWidget(button_group, 0, Qt.AlignBottom)

        self._update_nav_buttons()

    def _connect_signals(self):
        """连接信号"""
        self.prev_btn.clicked.connect(self._prev_image)
        self.next_btn.clicked.connect(self._next_image)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        self.reset_btn.clicked.connect(self._reset_zoom)
        self.save_btn.clicked.connect(self._save_image)
        self.close_btn.clicked.connect(self.accept)

    def _show_image(self, index: int):
        """显示指定索引的图片"""
        if not self._images or index < 0 or index >= len(self._images):
            return

        self._current_index = index
        image_filename = self._images[index]

        image_path = self._get_image_path(image_filename)

        if not image_path or not image_path.exists():
            self.image_label.setText(f'图片不存在：{image_filename}')
            self.image_label.setStyleSheet('color: #ff6b6b; background: transparent;')
            return

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText(f'无法加载图片：{image_filename}')
            self.image_label.setStyleSheet('color: #ff6b6b; background: transparent;')
            return

        self._original_pixmap = pixmap
        self._zoom_factor = 1.0
        self._display_pixmap()
        self._update_nav_buttons()

    def _get_image_path(self, filename: str) -> Path | None:
        """获取图片路径"""
        path = Path(PathUtil.get_image_path(filename))
        return path if path.exists() else None

    def _display_pixmap(self):
        """显示当前图片"""
        if not self._original_pixmap or self._original_pixmap.isNull():
            return

        # 计算缩放后尺寸
        scaled_pixmap = self._original_pixmap.scaled(
            int(self._original_pixmap.width() * self._zoom_factor),
            int(self._original_pixmap.height() * self._zoom_factor),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # 固定标签和内容容器大小，使滚动区域感知内容大小
        self.image_label.setFixedSize(scaled_pixmap.size())
        self.image_label.setPixmap(scaled_pixmap)

        margins = self.scroll_content.layout().contentsMargins()
        total_width = scaled_pixmap.width() + margins.left() + margins.right()
        total_height = scaled_pixmap.height() + margins.top() + margins.bottom()
        self.scroll_content.setFixedSize(total_width, total_height)

    def _update_nav_buttons(self):
        """更新导航按钮状态"""
        total = len(self._images)
        self.page_label.setText(f'{self._current_index + 1} / {total}')
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < total - 1)

    def _prev_image(self):
        """上一张"""
        if self._current_index > 0:
            self._zoom_factor = 1.0
            self._show_image(self._current_index - 1)

    def _next_image(self):
        """下一张"""
        if self._current_index < len(self._images) - 1:
            self._zoom_factor = 1.0
            self._show_image(self._current_index + 1)

    def _zoom_in(self):
        """放大"""
        self._zoom_factor = min(self._zoom_factor * 1.25, 5.0)
        self._display_pixmap()

    def _zoom_out(self):
        """缩小"""
        self._zoom_factor = max(self._zoom_factor / 1.25, 0.1)
        self._display_pixmap()

    def _reset_zoom(self):
        """重置缩放"""
        self._zoom_factor = 1.0
        self._display_pixmap()

    def _save_image(self):
        """保存图片到本地"""
        if not self._original_pixmap or self._original_pixmap.isNull():
            InfoBar.error(
                title='错误',
                content='没有可保存的图片',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        from datetime import datetime

        image_filename = self._images[self._current_index] if self._current_index < len(self._images) else None
        if image_filename:
            default_name = image_filename.split('/')[-1]
        else:
            default_name = f"untitled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        save_path, _ = QFileDialog.getSaveFileName(
            self, '保存图片',
            default_name,
            '图片文件 (*.png *.jpg *.jpeg *.bmp)'
        )

        if not save_path:
            return

        try:
            success = self._original_pixmap.save(save_path)
            if success:
                InfoBar.success(
                    title='成功',
                    content='图片已保存',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1500,
                    parent=self
                )
            else:
                InfoBar.error(
                    title='错误',
                    content='保存失败',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                title='错误',
                content=f'保存失败：{str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def resizeEvent(self, event):
        """窗口大小改变时重绘图片"""
        super().resizeEvent(event)
        if self._original_pixmap and not self._original_pixmap.isNull():
            self._display_pixmap()
