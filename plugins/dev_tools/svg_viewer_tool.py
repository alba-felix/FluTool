"""SVG 查看器 - 支持粘贴 SVG 代码并实时预览"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QSplitter, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QRect, QRectF, QRegularExpression
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtSvg import QSvgRenderer
from qfluentwidgets import PushButton, PrimaryPushButton, InfoBar, InfoBarPosition, isDarkTheme, qconfig, TextEdit, StrongBodyLabel

from plugins.text_tools.page_interface import TabPageInterface


class SvgHighlighter(QSyntaxHighlighter):
    """SVG/XML 简单语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules = []
        self._setup_rules()

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

    def _setup_rules(self):
        is_dark = isDarkTheme()

        # 标签名（<tag ...> 或 </tag>）
        tag_fmt = QTextCharFormat()
        tag_fmt.setForeground(QColor(86, 156, 214) if is_dark else QColor(0, 0, 255))
        tag_fmt.setFontWeight(QFont.Bold)
        self._rules.append((QRegularExpression(r'</?[\w-]+[\s>]'), tag_fmt))

        # 属性名
        attr_fmt = QTextCharFormat()
        attr_fmt.setForeground(QColor(156, 220, 254) if is_dark else QColor(128, 0, 128))
        self._rules.append((QRegularExpression(r'\b(?:xmlns|version|id|class|style|fill|stroke|width|height|viewBox|x|y|cx|cy|r|rx|ry|d|p|path|transform|opacity|xlink:href|href|src|alt)\b'), attr_fmt))

        # 属性值（双引号）
        val_fmt = QTextCharFormat()
        val_fmt.setForeground(QColor(206, 145, 120) if is_dark else QColor(163, 21, 21))
        self._rules.append((QRegularExpression(r'"[^"]*"'), val_fmt))

        # 属性值（单引号）
        self._rules.append((QRegularExpression(r"'[^']*'"), val_fmt))

        # 注释
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor(106, 153, 85) if is_dark else QColor(0, 128, 0))
        comment_fmt.setFontItalic(True)
        self._rules.append((QRegularExpression(r'<!--[\s\S]*?-->'), comment_fmt))

        # 十六进制颜色值
        color_fmt = QTextCharFormat()
        color_fmt.setForeground(QColor(255, 128, 64))
        self._rules.append((QRegularExpression(r'#[0-9a-fA-F]{3,8}\b'), color_fmt))

        # CDATA
        cdata_fmt = QTextCharFormat()
        cdata_fmt.setForeground(QColor(106, 153, 85) if is_dark else QColor(0, 128, 0))
        self._rules.append((QRegularExpression(r'<!\[CDATA\[.*?\]\]>'), cdata_fmt))


class SvgViewerTool(TabPageInterface):
    """SVG 查看器标签页"""

    page_id = "svg_viewer"
    page_name = "SVG 查看器"
    page_icon = None

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return SvgViewerWidget(parent)


class SvgPreviewLabel(QWidget):
    """SVG 预览标签 - 支持缩放和居中显示，通过 paintEvent 直接绘制"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svg_renderer = QSvgRenderer()
        self._zoom_factor = 1.0  # 缩放比例
        self._default_size = QSize(200, 200)  # 默认显示尺寸
        self._has_svg = False
        self._grid_pixmap = None  # 缓存网格背景
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self) -> None:
        """主题切换时清除网格缓存"""
        self._grid_pixmap = None
        self.update()

    def set_svg_data(self, svg_data: str) -> bool:
        """设置 SVG 数据，返回是否成功"""
        if not svg_data or not svg_data.strip():
            self._has_svg = False
            self.update()
            return False

        try:
            success = self._svg_renderer.load(svg_data.encode('utf-8'))
            if success:
                self._zoom_factor = 1.0
                self._default_size = self._svg_renderer.defaultSize()
                self._has_svg = True
                self._grid_pixmap = None  # 清除缓存
                self.update()
            return success
        except Exception:
            return False

    def clear(self) -> None:
        """清空 SVG 数据"""
        self._has_svg = False
        self._grid_pixmap = None
        self.update()

    def zoom_in(self) -> None:
        """放大"""
        self._zoom_factor = min(self._zoom_factor * 1.2, 5.0)
        self.update()

    def zoom_out(self) -> None:
        """缩小"""
        self._zoom_factor = max(self._zoom_factor / 1.2, 0.1)
        self.update()

    def reset_zoom(self) -> None:
        """实际尺寸"""
        self._zoom_factor = 1.0
        self.update()

    def fit_to_window(self) -> None:
        """自适应窗口"""
        if not self._svg_renderer.isValid():
            return

        view_size = self.size()
        svg_size = self._svg_renderer.defaultSize()

        if svg_size.width() <= 0 or svg_size.height() <= 0:
            return

        # 计算合适的缩放比例
        scale_w = view_size.width() / svg_size.width()
        scale_h = view_size.height() / svg_size.height()
        self._zoom_factor = min(scale_w, scale_h, 1.0)
        self.update()

    def paintEvent(self, event) -> None:
        """直接绘制 SVG"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        try:
            # 绘制网格背景
            self._draw_grid_background(painter)
            
            if not self._has_svg or not self._svg_renderer.isValid():
                return
            
            view_size = self.size()
            if view_size.width() < 10 or view_size.height() < 10:
                return

            # 计算目标尺寸
            target_size = self._default_size * self._zoom_factor

            # 限制最大尺寸不超过控件尺寸
            if target_size.width() > view_size.width() or target_size.height() > view_size.height():
                scale_w = view_size.width() / target_size.width()
                scale_h = view_size.height() / target_size.height()
                scale = min(scale_w, scale_h)
                target_size *= scale

            # 确保最小尺寸
            if target_size.width() < 10 or target_size.height() < 10:
                return

            # 计算居中位置
            offset_x = (view_size.width() - target_size.width()) / 2
            offset_y = (view_size.height() - target_size.height()) / 2

            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # 在居中位置渲染 SVG
            target_rect = QRectF(int(offset_x), int(offset_y), int(target_size.width()), int(target_size.height()))
            self._svg_renderer.render(painter, target_rect)
        finally:
            painter.end()

    def _draw_grid_background(self, painter: QPainter) -> None:
        """绘制透明网格背景（使用缓存优化性能）"""
        view_size = self.size()
        if view_size.width() < 1 or view_size.height() < 1:
            return

        grid_size = 10
        
        dark = isDarkTheme()
        light_color = QColor(50, 50, 50) if dark else QColor(255, 255, 255)
        dark_color = QColor(40, 40, 40) if dark else QColor(240, 240, 240)
        
        # 检查是否需要重新生成网格缓存
        if self._grid_pixmap is None or self._grid_pixmap.size() != view_size:
            self._grid_pixmap = self._create_grid_pixmap(view_size, grid_size, light_color, dark_color)
        
        # 绘制缓存的网格背景
        painter.drawPixmap(0, 0, self._grid_pixmap)

    def _create_grid_pixmap(self, size: QSize, grid_size: int, light_color: QColor, dark_color: QColor):
        """创建网格背景缓存"""
        from PyQt5.QtGui import QPixmap
        
        pixmap = QPixmap(size.width(), size.height())
        pixmap.fill(light_color)
        
        painter = QPainter(pixmap)
        try:
            painter.setBrush(dark_color)
            painter.setPen(Qt.NoPen)
            
            # 只绘制深色格子（棋盘格模式）
            for x in range(0, size.width(), grid_size * 2):
                for y in range(0, size.height(), grid_size * 2):
                    painter.drawRect(x, y, grid_size, grid_size)
                    painter.drawRect(x + grid_size, y + grid_size, grid_size, grid_size)
        finally:
            painter.end()
        return pixmap

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # 清除网格缓存，下次绘制时重新生成
        self._grid_pixmap = None
        if self._has_svg:
            self.update()

    def destroy(self, destroyWindow: bool = True, destroySubWindows: bool = True) -> None:
        """清理资源"""
        try:
            qconfig.themeChanged.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
        super().destroy(destroyWindow, destroySubWindows)

    def minimumSizeHint(self) -> QSize:
        return QSize(100, 100)

    def sizeHint(self) -> QSize:
        return QSize(100, 100)


class SvgViewerWidget(QWidget):
    """SVG 查看器主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("svgViewerWidget")
        self._setup_ui()
        self._update_style()
        qconfig.themeChanged.connect(self._update_style)

    def _update_style(self) -> None:
        """更新样式"""
        dark = isDarkTheme()
        if dark:
            self.setStyleSheet("""
                #svgViewerWidget { background-color: transparent; }
                #previewLabel {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                #svgViewerWidget { background-color: transparent; }
                #previewLabel {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }
            """)
        # 重建高亮器以适应新主题
        self._rebuild_highlighter()

    def _rebuild_highlighter(self) -> None:
        """根据当前主题重建高亮器"""
        self._highlighter = SvgHighlighter(self._code_editor.document())

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 顶部按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._format_btn = PushButton("格式化", self)
        self._format_btn.clicked.connect(self._format_svg)

        self._clear_btn = PushButton("清空", self)
        self._clear_btn.clicked.connect(self._clear_all)

        self._copy_btn = PushButton("复制SVG", self)
        self._copy_btn.clicked.connect(self._copy_svg)

        # 分隔符
        btn_layout.addWidget(self._format_btn)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addWidget(self._copy_btn)

        # 缩放按钮组（使用 PushButton 替代 ToolButton）
        btn_layout.addSpacing(10)

        self._zoom_in_btn = PushButton("+", self)
        self._zoom_in_btn.setFixedSize(32, 32)
        self._zoom_in_btn.setToolTip("放大")
        self._zoom_in_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        btn_layout.addWidget(self._zoom_in_btn)

        self._zoom_out_btn = PushButton("-", self)
        self._zoom_out_btn.setFixedSize(32, 32)
        self._zoom_out_btn.setToolTip("缩小")
        self._zoom_out_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        btn_layout.addWidget(self._zoom_out_btn)

        self._actual_size_btn = PushButton("1:1", self)
        self._actual_size_btn.setFixedSize(40, 32)
        self._actual_size_btn.setToolTip("实际尺寸")
        btn_layout.addWidget(self._actual_size_btn)

        self._fit_btn = PushButton("自适应", self)
        self._fit_btn.setFixedSize(50, 32)
        self._fit_btn.setToolTip("自适应窗口")
        btn_layout.addWidget(self._fit_btn)

        btn_layout.addStretch()

        self._save_btn = PrimaryPushButton("保存为文件", self)
        self._save_btn.clicked.connect(self._save_svg)
        btn_layout.addWidget(self._save_btn)

        main_layout.addLayout(btn_layout)

        # 主区域：QSplitter 左右分割
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)

        # 左侧：SVG 代码输入
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        code_title = StrongBodyLabel("SVG 代码", self)
        left_layout.addWidget(code_title)

        self._code_editor = TextEdit(self)
        self._code_editor.setPlaceholderText(
            "在此粘贴 SVG 代码...\n\n示例：\n<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>\n  <circle cx='50' cy='50' r='40' fill='#009faa'/>\n</svg>"
        )
        self._code_editor.textChanged.connect(self._on_code_changed)
        left_layout.addWidget(self._code_editor)

        # 应用 SVG 语法高亮
        self._highlighter = SvgHighlighter(self._code_editor.document())

        # 右侧：SVG 预览
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        preview_title = StrongBodyLabel("预览", self)
        right_layout.addWidget(preview_title)

        self._preview_label = SvgPreviewLabel(self)
        self._preview_label.setObjectName("previewLabel")
        self._preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self._preview_label)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        main_layout.addWidget(splitter)
        self._splitter = splitter

        # 连接缩放按钮信号
        self._zoom_in_btn.clicked.connect(self._preview_label.zoom_in)
        self._zoom_out_btn.clicked.connect(self._preview_label.zoom_out)
        self._actual_size_btn.clicked.connect(self._preview_label.reset_zoom)
        self._fit_btn.clicked.connect(self._preview_label.fit_to_window)

    def _on_code_changed(self) -> None:
        """代码变化时更新预览"""
        svg_code = self._code_editor.toPlainText().strip()
        if not svg_code:
            self._preview_label.clear()
            return

        success = self._preview_label.set_svg_data(svg_code)
        if not success:
            self._preview_label.clear()
            # 可以在预览区显示错误提示

    def _format_svg(self) -> None:
        """格式化 SVG 代码"""
        svg_code = self._code_editor.toPlainText().strip()
        if not svg_code:
            InfoBar.warning(
                title="提示",
                content="没有可格式化的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        try:
            # 简单的 XML 格式化
            import xml.dom.minidom
            dom = xml.dom.minidom.parseString(svg_code)
            formatted = dom.toprettyxml(indent="  ", encoding=None)
            # 移除 XML 声明行
            lines = formatted.split('\n')
            if lines and lines[0].startswith('<?xml'):
                lines = lines[1:]
            formatted = '\n'.join(lines).strip()

            self._code_editor.setPlainText(formatted)
            InfoBar.success(
                title="格式化成功",
                content="SVG 代码已格式化",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="格式化失败",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _clear_all(self) -> None:
        """清空所有"""
        self._code_editor.clear()
        self._preview_label.clear()

    def _copy_svg(self) -> None:
        """复制 SVG 到剪贴板"""
        svg_code = self._code_editor.toPlainText().strip()
        if not svg_code:
            InfoBar.warning(
                title="提示",
                content="没有可复制的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(svg_code)
        InfoBar.success(
            title="复制成功",
            content="SVG 代码已复制到剪贴板",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    def _save_svg(self) -> None:
        """保存 SVG 为文件"""
        svg_code = self._code_editor.toPlainText().strip()
        if not svg_code:
            InfoBar.warning(
                title="提示",
                content="没有可保存的内容",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 SVG 文件",
            "",
            "SVG Files (*.svg);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(svg_code)
                InfoBar.success(
                    title="保存成功",
                    content=f"已保存到: {file_path}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
            except Exception as e:
                InfoBar.error(
                    title="保存失败",
                    content=str(e),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )

    def closeEvent(self, event) -> None:
        """清理资源"""
        try:
            qconfig.themeChanged.disconnect(self._update_style)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        """窗口显示后设置初始等分尺寸"""
        super().showEvent(event)
        if hasattr(self, '_splitter'):
            sw = self._splitter.width()
            if sw > 0:
                half = sw // 2
                self._splitter.setSizes([half, half])