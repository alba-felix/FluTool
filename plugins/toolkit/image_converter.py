"""图片格式转换页面 - 常见图片格式互转与多尺寸输出"""

import os
from typing import List, Optional, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFileDialog, QListWidgetItem,
)
from qfluentwidgets import (
    FluentIcon as FIF, PushButton, ComboBox, CheckBox, InfoBar, InfoBarPosition,
    BodyLabel, StrongBodyLabel, LineEdit, PrimaryPushButton, ListWidget,
)

from .image_converter_service import (
    HAS_PIL, SUPPORTED_FORMATS, PRESET_SIZES, IMAGE_EXTS,
    parse_custom_size, convert_image,
)
from .page_interface import TabPageInterface

# 预设尺寸每行显示的个数
_SIZES_PER_ROW = 5


class ImageConverterPage(TabPageInterface):
    """图片格式转换页面"""

    page_id = "image_converter"
    page_name = "图片转换"

    @classmethod
    def create(cls, parent=None, core=None) -> QWidget:
        return ImageConverterWidget(parent, core=core)


class ImageConverterWidget(QWidget):
    """图片转换工具界面：格式单选、尺寸多选、拖拽上传"""

    def __init__(self, parent=None, core=None):
        super().__init__(parent)
        self.core = core
        self._file_paths: List[str] = []
        self._selected_format: Optional[str] = None
        self._size_checks: dict = {}
        self.setAcceptDrops(True)
        self._setup_ui()

    # ==================== UI ====================

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel("图片格式转换", self))

        if not HAS_PIL:
            InfoBar.error(
                title="缺少依赖",
                content="请安装 Pillow：pip install Pillow",
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                parent=self,
            )
            return

        # 文件选择区（批量列表 + 拖拽）
        file_btn_row = QHBoxLayout()
        add_btn = PushButton("选择图片", self)
        add_btn.setIcon(FIF.FOLDER)
        add_btn.clicked.connect(self._select_files)
        file_btn_row.addWidget(add_btn)
        remove_btn = PushButton("移除所选", self)
        remove_btn.setIcon(FIF.DELETE)
        remove_btn.clicked.connect(self._remove_selected)
        file_btn_row.addWidget(remove_btn)
        clear_btn = PushButton("清空", self)
        clear_btn.setIcon(FIF.BROOM)
        clear_btn.clicked.connect(self._clear_files)
        file_btn_row.addWidget(clear_btn)
        file_btn_row.addStretch()
        self._file_count_label = BodyLabel("共 0 张", self)
        file_btn_row.addWidget(self._file_count_label)
        layout.addLayout(file_btn_row)

        self._file_list = ListWidget(self)
        self._file_list.setMaximumHeight(160)
        layout.addWidget(self._file_list)

        drop_hint = BodyLabel("支持多选与拖拽添加，逐张转换为目标格式", self)
        drop_hint.setStyleSheet("color: #888;")
        layout.addWidget(drop_hint)

        # 目标格式行（单选下拉）
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(BodyLabel("目标格式:", self))
        self._fmt_combo = ComboBox(self)
        for display_name, fmt in SUPPORTED_FORMATS:
            self._fmt_combo.addItem(display_name, userData=fmt)
        self._fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        self._fmt_combo.setCurrentIndex(0)
        # 插入首项时 Qt 默认已选中索引 0，信号不触发，需显式初始化
        self._selected_format = self._fmt_combo.currentData()
        fmt_row.addWidget(self._fmt_combo, 1)
        layout.addLayout(fmt_row)

        # 输出尺寸区（多选，默认原始尺寸）
        layout.addWidget(StrongBodyLabel("输出尺寸", self))
        size_grid = QGridLayout()
        size_grid.setSpacing(6)
        self._orig_check = CheckBox("原始尺寸", self)
        self._orig_check.setChecked(True)
        size_grid.addWidget(self._orig_check, 0, 0)
        for index, (w, h) in enumerate(PRESET_SIZES):
            check = CheckBox(f"{w}×{h}", self)
            self._size_checks[(w, h)] = check
            cell = index + 1
            size_grid.addWidget(check, cell // _SIZES_PER_ROW, cell % _SIZES_PER_ROW)
        layout.addLayout(size_grid)

        custom_row = QHBoxLayout()
        self._custom_check = CheckBox("自定义:", self)
        self._custom_check.stateChanged.connect(self._on_custom_toggled)
        custom_row.addWidget(self._custom_check)
        self._custom_edit = LineEdit(self)
        self._custom_edit.setPlaceholderText("宽x高，如 512x512 或 512")
        self._custom_edit.setEnabled(False)
        custom_row.addWidget(self._custom_edit, 1)
        layout.addLayout(custom_row)

        size_hint = BodyLabel("默认按原始尺寸输出，可与预设/自定义叠加；ICO 会把选中尺寸嵌入单个文件", self)
        size_hint.setStyleSheet("color: #888;")
        layout.addWidget(size_hint)

        # 输出目录行
        out_row = QHBoxLayout()
        out_row.addWidget(BodyLabel("输出目录:", self))
        self._out_edit = LineEdit(self)
        self._out_edit.setPlaceholderText("默认与源文件相同目录")
        out_row.addWidget(self._out_edit, 1)
        browse_btn = PushButton("浏览", self)
        browse_btn.setIcon(FIF.FOLDER_ADD)
        browse_btn.clicked.connect(self._browse_output)
        out_row.addWidget(browse_btn)
        layout.addLayout(out_row)

        # 操作按钮
        btn_row = QHBoxLayout()
        self._convert_btn = PrimaryPushButton("开始转换", self)
        self._convert_btn.setIcon(FIF.SEND)
        self._convert_btn.clicked.connect(self._convert)
        self._convert_btn.setEnabled(False)
        btn_row.addWidget(self._convert_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    # ==================== 交互 ====================

    def _select_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.webp *.bmp *.ico *.gif *.tiff);;所有文件 (*.*)"
        )
        self._add_files(files)

    def _add_files(self, paths: List[str]) -> None:
        """批量追加文件到列表（按 normcase 去重，保持添加顺序）"""
        known = {os.path.normcase(p) for p in self._file_paths}
        for path in paths:
            key = os.path.normcase(path)
            if key in known:
                continue
            known.add(key)
            self._file_paths.append(path)
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self._file_list.addItem(item)
        if paths:
            self._update_convert_state()

    def _remove_selected(self) -> None:
        """移除列表中选中的文件"""
        rows = sorted(
            (self._file_list.row(item) for item in self._file_list.selectedItems()),
            reverse=True,
        )
        for row in rows:
            self._file_list.takeItem(row)
            del self._file_paths[row]
        self._update_convert_state()

    def _clear_files(self) -> None:
        """清空文件列表"""
        self._file_paths.clear()
        self._file_list.clear()
        self._update_convert_state()

    def dragEnterEvent(self, event) -> None:
        """拖入本地文件时接收事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """放下文件：按扩展名筛选图片后追加到待转换列表"""
        paths = [url.toLocalFile() for url in event.mimeData().urls()
                 if url.isLocalFile()]
        images = [p for p in paths
                  if os.path.splitext(p)[1].lower() in IMAGE_EXTS]
        if images:
            self._add_files(images)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self._out_edit.setText(directory)

    def _on_format_changed(self, index: int) -> None:
        """切换目标格式（单选）"""
        self._selected_format = self._fmt_combo.itemData(index)
        self._update_convert_state()

    def _on_custom_toggled(self, state: int) -> None:
        """自定义尺寸勾选状态切换输入框可用性"""
        self._custom_edit.setEnabled(self._custom_check.isChecked())

    def _collect_sizes(self) -> Optional[List[Tuple[int, int]]]:
        """收集选中尺寸；自定义勾选但格式非法时返回 None"""
        sizes = [size for size in PRESET_SIZES
                 if self._size_checks[size].isChecked()]
        if self._custom_check.isChecked():
            custom = parse_custom_size(self._custom_edit.text())
            if custom is None:
                return None
            sizes.append(custom)
        return sizes

    def _update_convert_state(self) -> None:
        """刷新文件计数与转换按钮可用状态"""
        count = len(self._file_paths)
        self._file_count_label.setText(f"共 {count} 张")
        self._convert_btn.setEnabled(bool(count and self._selected_format))

    # ==================== 转换 ====================

    def _convert(self) -> None:
        if not HAS_PIL:
            return

        sizes = self._collect_sizes()
        if sizes is None:
            InfoBar.warning(
                title="提示",
                content="自定义尺寸格式不正确，应为 宽x高，如 512x512 或 512",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self,
            )
            return

        if not self._file_paths or not self._selected_format:
            InfoBar.warning(
                title="提示",
                content="请先选择图片和目标格式",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            return

        include_original = self._orig_check.isChecked()
        if not sizes and not include_original:
            InfoBar.warning(
                title="提示",
                content="请至少勾选一个输出尺寸（或保留原始尺寸）",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2500,
                parent=self,
            )
            return

        output_dir = self._out_edit.text().strip()
        success_count = 0
        fail_count = 0
        errors = []

        for path in self._file_paths:
            try:
                target_dir = output_dir or os.path.dirname(path)
                results = convert_image(path, target_dir, self._selected_format,
                                        sizes, include_original)
                success_count += len(results)
            except Exception as e:
                fail_count += 1
                errors.append(f"{path}: {e}")
                if self.core:
                    self.core.logger.error(f"图片转换失败 {path}: {e}")

        if success_count > 0:
            InfoBar.success(
                title="转换完成",
                content=f"成功 {success_count} 张，失败 {fail_count} 张",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
        elif fail_count > 0:
            InfoBar.error(
                title="转换失败",
                content=errors[0] if errors else "未知错误",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
