from typing import List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap
from qfluentwidgets import MessageBoxBase, SubtitleLabel, PushButton, CaptionLabel, InfoBar, InfoBarPosition

from ..core.path_util import PathUtil


class ImageViewer(MessageBoxBase):
    def __init__(self, images: List[str], title: str = '\u56fe\u7247\u67e5\u770b', parent=None):
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
        self.titleLabel = SubtitleLabel(self._title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet('background: transparent;')
        self.viewLayout.addWidget(self.image_label)

        nav_layout = QHBoxLayout()
        nav_layout.addStretch()

        self.prev_btn = PushButton('\u4e0a\u4e00\u5f20')
        self.prev_btn.setFixedHeight(32)
        nav_layout.addWidget(self.prev_btn)

        self.page_label = CaptionLabel('1 / 1')
        nav_layout.addWidget(self.page_label)

        self.next_btn = PushButton('\u4e0b\u4e00\u5f20')
        self.next_btn.setFixedHeight(32)
        nav_layout.addWidget(self.next_btn)

        nav_layout.addStretch()
        self.viewLayout.addLayout(nav_layout)

        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.zoom_in_btn = PushButton('\u653e\u5927')
        self.zoom_in_btn.setFixedHeight(32)
        action_layout.addWidget(self.zoom_in_btn)

        self.zoom_out_btn = PushButton('\u7f29\u5c0f')
        self.zoom_out_btn.setFixedHeight(32)
        action_layout.addWidget(self.zoom_out_btn)

        self.reset_btn = PushButton('\u91cd\u7f6e')
        self.reset_btn.setFixedHeight(32)
        action_layout.addWidget(self.reset_btn)

        self.save_btn = PushButton('\u4fdd\u5b58')
        self.save_btn.setFixedHeight(32)
        action_layout.addWidget(self.save_btn)

        action_layout.addStretch()
        self.viewLayout.addLayout(action_layout)

        self.yesButton.setText('\u5173\u95ed')
        self.cancelButton.hide()

        self._update_nav_buttons()

    def _connect_signals(self):
        self.prev_btn.clicked.connect(self._prev_image)
        self.next_btn.clicked.connect(self._next_image)
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        self.reset_btn.clicked.connect(self._reset_zoom)
        self.save_btn.clicked.connect(self._save_image)

    def _show_image(self, index: int):
        if not self._images or index < 0 or index >= len(self._images):
            return

        self._current_index = index
        image_filename = self._images[index]

        # 尝试多种方式获取图片路径
        image_path = self._get_image_path(image_filename)

        if not image_path or not image_path.exists():
            self.image_label.setText(f'\u56fe\u7247\u4e0d\u5b58\u5728\uff1a{image_filename}')
            self.image_label.setStyleSheet('color: #ff6b6b; background: transparent;')
            return

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.image_label.setText(f'\u65e0\u6cd5\u52a0\u8f7d\u56fe\u7247\uff1a{image_filename}')
            self.image_label.setStyleSheet('color: #ff6b6b; background: transparent;')
            return

        self._original_pixmap = pixmap
        self._zoom_factor = 1.0
        self._display_pixmap()
        self._update_nav_buttons()

    def _get_image_path(self, filename: str):
        """获取图片路径，尝试多种方式"""
        # 1. 如果已经是完整路径，直接使用
        path = PathUtil.get_image_path(filename)
        if path.exists():
            return path

        # 2. 尝试 data/images 目录
        base_path = PathUtil.get_data_path()
        images_dir = base_path / 'images'
        path = images_dir / filename
        if path.exists():
            return path

        # 3. 尝试直接作为文件名（可能是相对路径）
        path = PathUtil.get_base_path() / filename
        if path.exists():
            return path

        # 4. 返回 None
        return None

    def _display_pixmap(self):
        if not self._original_pixmap or self._original_pixmap.isNull():
            return

        label_size = self.image_label.size()
        if label_size.width() == 0 or label_size.height() == 0:
            return

        scaled_pixmap = self._original_pixmap.scaled(
            int(label_size.width() * self._zoom_factor),
            int(label_size.height() * self._zoom_factor),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)

    def _update_nav_buttons(self):
        total = len(self._images)
        self.page_label.setText(f'{self._current_index + 1} / {total}')
        self.prev_btn.setEnabled(self._current_index > 0)
        self.next_btn.setEnabled(self._current_index < total - 1)

    def _prev_image(self):
        if self._current_index > 0:
            self._zoom_factor = 1.0
            self._show_image(self._current_index - 1)

    def _next_image(self):
        if self._current_index < len(self._images) - 1:
            self._zoom_factor = 1.0
            self._show_image(self._current_index + 1)

    def _zoom_in(self):
        self._zoom_factor = min(self._zoom_factor * 1.25, 5.0)
        self._display_pixmap()

    def _zoom_out(self):
        self._zoom_factor = max(self._zoom_factor / 1.25, 0.1)
        self._display_pixmap()

    def _reset_zoom(self):
        self._zoom_factor = 1.0
        self._display_pixmap()

    def _save_image(self):
        """保存图片到本地"""
        if not self._original_pixmap or self._original_pixmap.isNull():
            InfoBar.error(
                title='\u9519\u8bef',
                content='\u6ca1\u6709\u53ef\u4fdd\u5b58\u7684\u56fe\u7247',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        from datetime import datetime
        
        # 获取默认文件名
        image_filename = self._images[self._current_index] if self._current_index < len(self._images) else None
        if image_filename:
            default_name = image_filename.split('/')[-1]  # 只取文件名部分
        else:
            default_name = f"untitled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        save_path, _ = QFileDialog.getSaveFileName(
            self, '\u4fdd\u5b58\u56fe\u7247',
            default_name,
            '\u56fe\u7247\u6587\u4ef6 (*.png *.jpg *.jpeg *.bmp)'
        )

        if not save_path:
            return

        # 保存图片
        try:
            # 保存 pixmap 到文件（确保路径是字符串）
            success = self._original_pixmap.save(save_path)
            if success:
                InfoBar.success(
                    title='\u6210\u529f',
                    content='\u56fe\u7247\u5df2\u4fdd\u5b58',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1500,
                    parent=self
                )
            else:
                InfoBar.error(
                    title='\u9519\u8bef',
                    content='\u4fdd\u5b58\u5931\u8d25',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            InfoBar.error(
                title='\u9519\u8bef',
                content=f'\u4fdd\u5b58\u5931\u8d25\uff1a{str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._original_pixmap and not self._original_pixmap.isNull():
            self._display_pixmap()