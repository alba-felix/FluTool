"""图片格式转换页面 - 常见图片格式互转"""

from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QLabel,
    QApplication
)
from qfluentwidgets import (
    FluentIcon as FIF, PushButton, ComboBox, InfoBar, InfoBarPosition,
    BodyLabel, StrongBodyLabel, LineEdit, RoundMenu, Action,
    PrimaryPushButton, isDarkTheme,
)

from .page_interface import TabPageInterface

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# 支持的格式：显示名 -> PIL 格式
SUPPORTED_FORMATS = [
    ("PNG", "PNG"),
    ("JPG", "JPEG"),
    ("WebP", "WEBP"),
    ("BMP", "BMP"),
    ("ICO", "ICO"),
    ("GIF", "GIF"),
    ("TIFF", "TIFF"),
]

# ICO 多尺寸规则：默认生成常见尺寸
ICO_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


class ImageConverterPage(TabPageInterface):
    """图片格式转换页面"""

    page_id = "image_converter"
    page_name = "图片转换"

    @classmethod
    def create(cls, parent=None, core=None) -> QWidget:
        return ImageConverterWidget(parent, core=core)


class ImageConverterWidget(QWidget):
    """图片转换工具界面"""

    def __init__(self, parent=None, core=None):
        super().__init__(parent)
        self.core = core
        self._file_paths: List[str] = []
        self._selected_formats: set = set()
        self._setup_ui()

    # ==================== UI ====================

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = StrongBodyLabel("图片格式转换", self)
        layout.addWidget(title)

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

        # 文件选择行
        file_row = QHBoxLayout()
        self._file_label = BodyLabel("未选择文件", self)
        file_row.addWidget(self._file_label, 1)
        select_btn = PushButton("选择图片", self)
        select_btn.setIcon(FIF.FOLDER)
        select_btn.clicked.connect(self._select_files)
        file_row.addWidget(select_btn)
        layout.addLayout(file_row)

        # 目标格式行（下拉多选）
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(BodyLabel("目标格式:", self))
        self._fmt_btn = PushButton("点击选择格式", self)
        self._fmt_btn.setIcon(FIF.DOWN)
        self._fmt_btn.clicked.connect(self._show_format_menu)
        fmt_row.addWidget(self._fmt_btn, 1)
        layout.addLayout(fmt_row)

        self._fmt_hint = BodyLabel("", self)
        self._fmt_hint.setStyleSheet("color: #888;")
        layout.addWidget(self._fmt_hint)

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
        if files:
            self._file_paths = files
            if len(files) == 1:
                self._file_label.setText(f"已选择 1 个文件：{files[0]}")
            else:
                self._file_label.setText(f"已选择 {len(files)} 个文件")
            self._update_convert_state()

    def _browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self._out_edit.setText(directory)

    def _show_format_menu(self) -> None:
        """目标格式下拉多选菜单"""
        menu = RoundMenu(parent=self)
        actions = []
        for display_name, _fmt in SUPPORTED_FORMATS:
            act = Action(display_name)
            act.setCheckable(True)
            act.setChecked(_fmt in self._selected_formats)
            act.triggered.connect(
                lambda checked=False, f=_fmt: self._toggle_format(f, checked)
            )
            actions.append(act)
            menu.addAction(act)
        menu.exec(self._fmt_btn.mapToGlobal(self._fmt_btn.rect().bottomLeft()))

    def _toggle_format(self, fmt: str, checked: bool) -> None:
        if checked:
            self._selected_formats.add(fmt)
        else:
            self._selected_formats.discard(fmt)
        self._update_convert_state()

    def _update_convert_state(self) -> None:
        names = [n for n, f in SUPPORTED_FORMATS if f in self._selected_formats]
        if names:
            self._fmt_btn.setText("、".join(names))
            self._fmt_hint.setText(f"已选 {len(names)} 种格式")
        else:
            self._fmt_btn.setText("点击选择格式")
            self._fmt_hint.setText("")
        self._convert_btn.setEnabled(bool(self._file_paths and self._selected_formats))

    # ==================== 转换 ====================

    def _convert(self) -> None:
        if not HAS_PIL:
            return
        if not self._file_paths or not self._selected_formats:
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

        output_dir = self._out_edit.text().strip()
        success_count = 0
        fail_count = 0
        errors = []

        for path in self._file_paths:
            try:
                results = self._convert_one(path, output_dir)
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

    def _convert_one(self, path: str, output_dir: str = "") -> List[str]:
        """转换单个图片到所有选中格式，返回生成的文件列表"""
        import os

        image = Image.open(path)
        if image.mode in ("RGBA", "P", "LA"):
            pass
        else:
            image = image.convert("RGBA")

        base_name = os.path.splitext(os.path.basename(path))[0]
        target_dir = output_dir or os.path.dirname(path)
        os.makedirs(target_dir, exist_ok=True)

        results = []
        for fmt in self._selected_formats:
            ext = fmt.lower()
            if fmt == "JPEG":
                ext = "jpg"
            out_path = os.path.join(target_dir, f"{base_name}.{ext}")
            self._save_format(image, out_path, fmt)
            results.append(out_path)
        image.close()
        return results

    def _save_format(self, image, out_path: str, fmt: str) -> None:
        """按格式保存，处理透明色与 ICO 多尺寸"""
        if fmt == "JPEG":
            rgb = image.convert("RGB")
            rgb.save(out_path, format="JPEG", quality=90)
            return
        if fmt == "ICO":
            icon = image.convert("RGBA")
            icon.save(out_path, format="ICO", sizes=ICO_SIZES)
            return
        image.save(out_path, format=fmt)