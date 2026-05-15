import os
import re
import json
try:
    import sip
except ImportError:
    from PyQt5 import sip
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from PyQt5.QtCore import Qt, QPoint, QPointF, QTimer, pyqtSignal, QSize, QEvent, QThread, QObject
from PyQt5.QtGui import QColor, QPalette, QPixmap, QPainter, QPen, QCursor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QColorDialog,
    QGridLayout, QScrollArea, QFrame, QTabWidget,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox, QToolTip,
    QMenu, QAction, QApplication, QFileDialog, QTextEdit, QDialog,
    QVBoxLayout as QVBoxLayoutWidget, QLineEdit, QPushButton,
    QButtonGroup
)
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, ScrollArea, PrimaryPushButton, ToolButton,
    CardWidget, SpinBox, isDarkTheme, qconfig, BodyLabel, IndeterminateProgressBar,
    ComboBox, FluentStyleSheet, Dialog, RoundMenu, Action, MessageBoxBase,
    SubtitleLabel, BodyLabel as FluentBodyLabel, CaptionLabel
)
from core import PluginInterface, get_app_data_path
from plugins.folder_tree.service import FolderTreeService


class FolderTreeWorker(QObject):
    """文件夹树生成后台工作线程"""
    finished = pyqtSignal(str, list, int, int)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, root_path: Path, mode: str, rule_index: int, custom_rules: dict, depth: int = -1):
        super().__init__()
        self._root_path = root_path
        self._mode = mode
        self._rule_index = rule_index
        self._custom_rules = custom_rules
        self._depth = depth
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            self.status.emit("正在估算项目数量...")
            total_items = self._count_items(self._root_path, 0)
            folder_count, file_count = 0, 0

            self.status.emit(f"正在生成结构 ({total_items} 个项目)...")
            root_name = self._root_path.name
            tree_body = ""
            flat_nodes: List[Tuple[str, bool, int]] = [("", False, 0)]

            if self._mode == "tree":
                tree_body, flat_nodes, folder_count, file_count = self._build_tree(
                    self._root_path, '', 0, [(root_name, True, 0)], 0, 0
                )
            else:
                tree_body, flat_nodes, folder_count, _ = self._build_folders_only(
                    self._root_path, '', 0, [(root_name, True, 0)], 0, 0
                )

            if self._cancelled:
                return

            tree_content = f"{root_name}/\n{tree_body}"
            self.finished.emit(tree_content, flat_nodes, folder_count, file_count)
        except Exception as e:
            self.error.emit(str(e))

    def _get_skip_names(self) -> set:
        """获取当前规则下需要跳过的名称集合"""
        if self._rule_index == 1:
            return {".venv", ".git", ".idea"}
        if self._rule_index >= 2:
            custom_index = self._rule_index - 2
            rule_names = list(self._custom_rules.keys())
            if custom_index < len(rule_names):
                rule_name = rule_names[custom_index]
                return set(self._custom_rules.get(rule_name, []))
        return set()

    def _count_items(self, path: Path, current_depth: int) -> int:
        """预计算项目数量"""
        if self._cancelled:
            return 0
        count = 0
        items = []
        try:
            skip_names = self._get_skip_names()
            items = [item for item in path.iterdir() if item.name not in skip_names]
            count += len(items)
            if self._depth == -1 or current_depth < self._depth:
                for item in items:
                    try:
                        if item.is_dir():
                            count += self._count_items(item, current_depth + 1)
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError):
            pass
        return count

    def _build_tree(self, path: Path, prefix: str, current_depth: int,
                     flat_nodes_or_folder_count,
                     folder_count: int = None, file_count: int = None):
        """递归获取文件夹树形结构（深度可控）"""
        legacy_return = not isinstance(flat_nodes_or_folder_count, list)
        if legacy_return:
            flat_nodes = []
            folder_count = flat_nodes_or_folder_count
        else:
            flat_nodes = flat_nodes_or_folder_count

        if folder_count is None:
            folder_count = 0
        if file_count is None:
            file_count = 0

        if self._cancelled:
            return ("", folder_count, file_count) if legacy_return else ("", flat_nodes, folder_count, file_count)

        tree = ''
        items = []
        try:
            skip_names = self._get_skip_names()
            items = sorted(
                (item for item in path.iterdir() if item.name not in skip_names),
                key=lambda x: x.name.lower()
            )
        except (PermissionError, OSError):
            pass

        for i, item in enumerate(items):
            if self._cancelled:
                return ("", folder_count, file_count) if legacy_return else ("", flat_nodes, folder_count, file_count)

            try:
                is_last = (i == len(items) - 1)
                is_dir = item.is_dir()
                display_name = f'{item.name}/' if is_dir else item.name

                if is_last:
                    tree += f'{prefix}└── {display_name}\n'
                    next_prefix = f'{prefix}    '
                else:
                    tree += f'{prefix}├── {display_name}\n'
                    next_prefix = f'{prefix}│   '

                if is_dir:
                    folder_count += 1
                    node_depth = current_depth + 1
                    flat_nodes.append((item.name, True, node_depth))
                    if self._depth == -1 or node_depth < self._depth:
                        sub_tree, flat_nodes, folder_count, file_count = self._build_tree(
                            item, next_prefix, node_depth, flat_nodes, folder_count, file_count
                        )
                        tree += sub_tree
                else:
                    file_count += 1
                    flat_nodes.append((item.name, False, current_depth + 1))
            except (PermissionError, OSError):
                pass

        if legacy_return:
            return tree, folder_count, file_count
        return tree, flat_nodes, folder_count, file_count

    def _build_folders_only(self, path: Path, prefix: str, current_depth: int,
                            flat_nodes_or_folder_count,
                            folder_count: int = None, file_count: int = None):
        """递归获取只有文件夹的树形结构（深度可控）"""
        legacy_return = not isinstance(flat_nodes_or_folder_count, list)
        if legacy_return:
            flat_nodes = []
            folder_count = flat_nodes_or_folder_count
        else:
            flat_nodes = flat_nodes_or_folder_count

        if folder_count is None:
            folder_count = 0
        if file_count is None:
            file_count = 0

        if self._cancelled:
            return ("", folder_count, 0) if legacy_return else ("", flat_nodes, folder_count, 0)

        tree = ''
        folders = []
        try:
            skip_names = self._get_skip_names()
            items = sorted(
                (item for item in path.iterdir() if item.name not in skip_names),
                key=lambda x: x.name.lower()
            )
            folders = [item for item in items if item.is_dir()]
        except (PermissionError, OSError):
            pass

        for i, item in enumerate(folders):
            if self._cancelled:
                return ("", folder_count, 0) if legacy_return else ("", flat_nodes, folder_count, 0)

            try:
                is_last = (i == len(folders) - 1)
                display_name = f'{item.name}/'
                folder_count += 1

                if is_last:
                    tree += f'{prefix}└── {display_name}\n'
                    next_prefix = f'{prefix}    '
                else:
                    tree += f'{prefix}├── {display_name}\n'
                    next_prefix = f'{prefix}│   '

                node_depth = current_depth + 1
                flat_nodes.append((item.name, True, node_depth))

                if self._depth == -1 or node_depth < self._depth:
                    sub_tree, flat_nodes, folder_count, _ = self._build_folders_only(
                        item, next_prefix, node_depth, flat_nodes, folder_count, 0
                    )
                    tree += sub_tree
            except (PermissionError, OSError):
                pass

        if legacy_return:
            return tree, folder_count, 0
        return tree, flat_nodes, folder_count, 0


class TreeNode:
    """文件夹树节点数据"""
    def __init__(self, name: str, is_dir: bool, depth: int = 0):
        self.name = name
        self.is_dir = is_dir
        self.depth = depth
        self.children: List['TreeNode'] = []
        self.expanded = True
        self.parent: Optional['TreeNode'] = None

    def add_child(self, child: 'TreeNode'):
        child.parent = self
        self.children.append(child)

    @property
    def has_children(self) -> bool:
        return len(self.children) > 0

    @property
    def is_last_sibling(self) -> bool:
        if self.parent is None:
            return True
        return self.parent.children[-1] is self

    def get_connector_flags(self) -> List[bool]:
        """获取每级缩进是否需要画│线
        返回列表长度 = self.depth，flag[d] 表示第 d 级（从根开始）是否需要画│
        """
        if self.parent is None:
            return []
        chain: List[TreeNode] = []
        node = self
        while node.parent is not None:
            chain.append(node.parent)
            node = node.parent
        chain.reverse()
        return [not ancestor.is_last_sibling for ancestor in chain]

    def get_visible_nodes(self) -> List['TreeNode']:
        """获取所有可见节点（含自身），按展开状态过滤"""
        nodes = [self]
        if self.expanded:
            for child in self.children:
                nodes.extend(child.get_visible_nodes())
        return nodes


SCAN_DEPTH_CONFIG_KEY = "folder_tree_scan_depth"

NODE_INDENT = 24
NODE_SPACING = 6


class TreeRowWidget(QWidget):
    """树节点行控件（含连接线绘制）"""
    toggle_requested = pyqtSignal(object)

    INDENT = NODE_INDENT
    LINE_COLOR = QColor(180, 180, 180)

    def __init__(self, node: TreeNode, parent=None):
        super().__init__(parent)
        self._node = node
        self._connector_flags = node.get_connector_flags()
        self._init_ui()

    def _init_ui(self):
        """初始化行布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)

        depth = self._node.depth
        btn_width = 18
        connector_end = depth * self.INDENT
        is_toggleable = self._node.is_dir and self._node.has_children

        if is_toggleable:
            layout.addSpacing(connector_end)
        else:
            layout.addSpacing(connector_end + btn_width + NODE_SPACING)

        self._toggle_btn = ToolButton()
        self._toggle_btn.setFixedSize(btn_width, btn_width)
        if is_toggleable:
            icon = FIF.CHEVRON_RIGHT if not self._node.expanded else FIF.ARROW_DOWN
            self._toggle_btn.setIcon(icon)
            self._toggle_btn.clicked.connect(self._on_toggle)
            layout.addSpacing(NODE_SPACING)
        else:
            self._toggle_btn.setVisible(False)
        layout.addWidget(self._toggle_btn)

        name_text = f'{self._node.name}/' if self._node.is_dir else self._node.name
        self._name_label = BodyLabel(name_text)
        layout.addWidget(self._name_label)

        layout.addStretch()

    def _on_toggle(self):
        """切换展开/折叠"""
        self.toggle_requested.emit(self._node)

    def update_icon(self):
        """更新折叠图标状态"""
        if not (self._node.is_dir and self._node.has_children):
            return
        icon = FIF.CHEVRON_RIGHT if not self._node.expanded else FIF.ARROW_DOWN
        self._toggle_btn.setIcon(icon)

    def paintEvent(self, event):
        """绘制树连接线"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(self.LINE_COLOR, 1.2))

        h = self.height()
        mid_y = h / 2
        depth = self._node.depth
        is_last = self._node.is_last_sibling

        for d in range(depth):
            cx = d * self.INDENT + self.INDENT / 2
            if d == depth - 1:
                if is_last:
                    painter.drawLine(QPointF(cx, 0), QPointF(cx, mid_y))
                    painter.drawLine(QPointF(cx, mid_y), QPointF(cx + self.INDENT / 2, mid_y))
                else:
                    painter.drawLine(QPointF(cx, 0), QPointF(cx, h))
                    painter.drawLine(QPointF(cx, mid_y), QPointF(cx + self.INDENT / 2, mid_y))
            elif d < len(self._connector_flags) and self._connector_flags[d]:
                painter.drawLine(QPointF(cx, 0), QPointF(cx, h))


class FolderTreeView(QScrollArea):
    """可折叠文件夹树视图"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(1)
        self._layout.setAlignment(Qt.AlignTop)

        self.setWidget(self._container)

        self._root_nodes: List[TreeNode] = []
        self._row_widgets: List[TreeRowWidget] = []

    @staticmethod
    def _scrollbar_stylesheet() -> str:
        dark = isDarkTheme()
        bg = "#3d3d3d" if dark else "#e0e0e0"
        handle_bg = "#5a5a5a" if dark else "#bfbfbf"
        handle_hover = "#7a7a7a" if dark else "#9a9a9a"
        handle_pressed = "#9a9a9a" if dark else "#808080"
        width = 10

        return f"""
            QScrollBar:vertical {{
                background: {bg};
                width: {width}px;
                margin: 0px;
                padding: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {handle_bg};
                min-height: 30px;
                margin: 1px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {handle_hover};
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {handle_pressed};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """

    def apply_style(self):
        self.verticalScrollBar().setStyleSheet(self._scrollbar_stylesheet())

    @staticmethod
    def build_tree(flat_nodes: List[Tuple[str, bool, int]]) -> List[TreeNode]:
        """从扁平节点列表构建TreeNode树

        Args:
            flat_nodes: [(name, is_dir, depth), ...] 列表, depth从0开始

        Returns:
            根节点列表（通常只有一个根节点）
        """
        if not flat_nodes:
            return []

        roots: List[TreeNode] = []
        stack: List[Tuple[int, TreeNode]] = []

        for name, is_dir, depth in flat_nodes:
            node = TreeNode(name, is_dir, depth)
            node.expanded = (depth == 0)

            while stack and stack[-1][0] >= depth:
                stack.pop()

            if stack:
                stack[-1][1].add_child(node)
            else:
                roots.append(node)

            if is_dir:
                stack.append((depth, node))

        return roots

    def set_tree(self, flat_nodes: List[Tuple[str, bool, int]]):
        """设置树数据并刷新显示"""
        self._root_nodes = self.build_tree(flat_nodes)
        self._rebuild()

    def _rebuild(self):
        """重建所有可见行"""
        for row in self._row_widgets:
            self._layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self._row_widgets.clear()

        for root in self._root_nodes:
            visible = root.get_visible_nodes()
            for node in visible:
                row = TreeRowWidget(node, self._container)
                row.toggle_requested.connect(self._on_toggle)
                self._layout.addWidget(row)
                self._row_widgets.append(row)

    def _on_toggle(self, node: TreeNode):
        """切换节点展开/折叠"""
        node.expanded = not node.expanded
        self._rebuild()

    def clear(self):
        """清空树"""
        self._root_nodes.clear()
        self._rebuild()


class FolderTreeWidget(QWidget):
    """文件夹树插件界面"""
    PLUGIN_ID = "folder_tree"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = FolderTreeService()
        self.current_folder = None
        self.tree_content = ""
        self.custom_rules = {}

        # 扫描统计
        self._folder_count = 0
        self._file_count = 0

        # 扫描统计
        self._folder_count = 0
        self._file_count = 0

        # 深度扫描相关属性
        self._scan_depth = -1
        self._worker = None
        self._thread = None
        self._cancelled = False

        self.init_ui()
        self.setup_style()
        qconfig.themeChangedFinished.connect(self.on_theme_changed)
        
        # 使用 QTimer 延迟加载规则，确保数据库已初始化
        QTimer.singleShot(100, self._delayed_load_rules)
    
    def _delayed_load_rules(self):
        """延迟加载规则"""
        self.load_custom_rules()
        # 更新下拉框
        self._update_rules_combo()

    def on_theme_changed(self):
        """主题变化时更新样式"""
        QTimer.singleShot(0, self.setup_style)

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建最外层滚动区域
        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setObjectName("folderTreeScrollArea")

        # 创建内容容器
        self._content_widget = QWidget()
        self._content_widget.setObjectName("folderTreeContent")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        # 工具栏
        toolbar = self.create_toolbar()
        self._content_layout.addWidget(toolbar)

        # 可折叠文件夹树视图
        self._tree_view = FolderTreeView()
        self._content_layout.addWidget(self._tree_view, 1)

        # 纯文本预览（简单版）
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setPlaceholderText("请选择文件夹并生成树形结构...")
        self._content_layout.addWidget(self._preview_text, 1)
        self._preview_text.hide()

        # 状态栏
        status_bar = self.create_status_bar()
        self._content_layout.addWidget(status_bar)

        # 将内容容器添加到滚动区域
        self._scroll_area.setWidget(self._content_widget)

        main_layout.addWidget(self._scroll_area)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("folderTreeToolbar")
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(8, 8, 8, 8)
        toolbar_layout.setSpacing(8)

        # 选择文件夹按钮
        self._select_btn = PrimaryPushButton(FIF.FOLDER, "选择文件夹")
        self._select_btn.clicked.connect(self.select_folder)
        toolbar_layout.addWidget(self._select_btn)

        # 生成树形结构按钮
        self._generate_tree_btn = PushButton(FIF.VIEW, "生成树形结构")
        self._generate_tree_btn.clicked.connect(self.generate_tree)
        toolbar_layout.addWidget(self._generate_tree_btn)

        # 只生成文件夹按钮
        self._generate_folders_btn = PushButton(FIF.FOLDER, "只生成文件夹")
        self._generate_folders_btn.clicked.connect(self.generate_folders_only)
        toolbar_layout.addWidget(self._generate_folders_btn)

        # 取消按钮（默认隐藏）
        self._cancel_btn = PushButton(FIF.CLOSE, "取消")
        self._cancel_btn.clicked.connect(self._cancel_scan)
        self._cancel_btn.setVisible(False)
        toolbar_layout.addWidget(self._cancel_btn)
        
        # 扫描深度选择下拉框
        depth_label = CaptionLabel("深度:", self)
        toolbar_layout.addWidget(depth_label)
        
        self._depth_combo = ComboBox()
        self._depth_combo.addItems(["1 级", "2 级", "3 级", "全部"])
        self._depth_combo.setFixedWidth(80)
        toolbar_layout.addWidget(self._depth_combo)
        
        # 加载保存的深度设置
        saved_depth = self._load_scan_depth()
        self._scan_depth = saved_depth
        
        # 设置下拉框当前值
        depth_to_index = {-1: 3, 1: 0, 2: 1, 3: 2}
        default_index = depth_to_index.get(saved_depth, 3)
        self._depth_combo.setCurrentIndex(default_index)
        
        self._depth_combo.currentIndexChanged.connect(self._on_depth_changed)

        # 视图切换按钮
        self._view_toggle_btn = ToolButton()
        self._view_toggle_btn.setIcon(FIF.FOLDER)
        self._view_toggle_btn.setToolTip("切换结果视图")
        self._view_toggle_btn.setFixedSize(32, 32)
        self._view_toggle_btn.clicked.connect(self._toggle_view)
        toolbar_layout.addWidget(self._view_toggle_btn)

        toolbar_layout.addStretch()

        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator)

        # 保存为txt按钮
        self._save_btn = PushButton(FIF.SAVE, "保存")
        self._save_btn.clicked.connect(self.save_to_txt)
        toolbar_layout.addWidget(self._save_btn)

        # 另存为按钮
        self._save_as_btn = PushButton(FIF.SAVE_AS, "另存为")
        self._save_as_btn.clicked.connect(self.save_as)
        toolbar_layout.addWidget(self._save_as_btn)

        # 分隔符
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.VLine)
        toolbar_layout.addWidget(separator2)

        # 规则下拉框
        self._rules_combo = ComboBox()
        self._update_rules_combo()
        self._rules_combo.setCurrentIndex(0)
        self._rules_combo.currentIndexChanged.connect(self.on_rules_combo_changed)
        toolbar_layout.addWidget(self._rules_combo)
        
        # 自定义规则按钮
        self._custom_rule_btn = PushButton(FIF.EDIT, "自定义规则")
        self._custom_rule_btn.clicked.connect(self.open_custom_rule_dialog)
        toolbar_layout.addWidget(self._custom_rule_btn)

        toolbar_layout.addStretch()

        return toolbar_widget

    def create_status_bar(self):
        """创建状态栏"""
        status_widget = QWidget()
        status_widget.setObjectName("folderTreeStatus")
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(8, 4, 8, 4)

        self._status_label = BodyLabel("就绪")
        status_layout.addWidget(self._status_label)

        # 进度条（等待条）
        self._progress_bar = IndeterminateProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setVisible(False)
        status_layout.addWidget(self._progress_bar)

        status_layout.addStretch()

        self._folder_count_label = BodyLabel("文件夹: 0")
        status_layout.addWidget(self._folder_count_label)

        self._file_count_label = BodyLabel("文件: 0")
        status_layout.addWidget(self._file_count_label)

        return status_widget

    def setup_style(self):
        """设置样式（支持主题）"""
        dark = isDarkTheme()
        
        if dark:
            bg_color = "#1e1e1e"
            text_color = "#ffffff"
            border_color = "#3d3d3d"
        else:
            bg_color = "#f5f5f5"
            text_color = "#333333"
            border_color = "#d9d9d9"
        
        # 工具栏
        toolbar = self.findChild(QWidget, "folderTreeToolbar")
        if toolbar:
            toolbar.setStyleSheet(f"""
                QWidget#folderTreeToolbar {{
                    background-color: {bg_color};
                    border-bottom: 1px solid {border_color};
                }}
            """)
        
        # 滚动区域
        self._scroll_area.setStyleSheet(f"""
            ScrollArea#folderTreeScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea#folderTreeScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea#folderTreeScrollArea > QWidget {{
                background-color: {bg_color};
            }}
        """)
        
        # 内容容器
        self._content_widget.setStyleSheet(f"QWidget#folderTreeContent{{background-color: {bg_color};}}")
        
        # 可折叠树视图
        self._tree_view.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 2px;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: {bg_color};
            }}
        """)
        self._tree_view.apply_style()

        # 纯文本预览框
        self._preview_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
            QTextEdit > QScrollBar:vertical {{
                background: {"#3d3d3d" if dark else "#e0e0e0"};
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }}
            QTextEdit > QScrollBar::handle:vertical {{
                background: {"#5a5a5a" if dark else "#bfbfbf"};
                min-height: 30px;
                border-radius: 4px;
            }}
            QTextEdit > QScrollBar::handle:vertical:hover {{
                background: {"#7a7a7a" if dark else "#9a9a9a"};
            }}
            QTextEdit > QScrollBar::add-line:vertical,
            QTextEdit > QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QTextEdit > QScrollBar::add-page:vertical,
            QTextEdit > QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        # 状态栏
        status = self.findChild(QWidget, "folderTreeStatus")
        if status:
            status.setStyleSheet(f"""
                QWidget#folderTreeStatus {{
                    background-color: {bg_color};
                    border-top: 1px solid {border_color};
                }}
            """)
    
    def load_custom_rules(self):
        """加载自定义规则"""
        try:
            rules = self.service.list_rules()
            self.custom_rules = {}
            for rule in rules:
                # exclude_items 从 Repository 返回时已经是 list 类型
                items = rule['exclude_items'] if rule['exclude_items'] else []
                self.custom_rules[rule['rule_name']] = items
        except Exception as e:
            self.custom_rules = {}
    
    def save_custom_rules(self):
        """保存自定义规则（已弃用，现在实时保存到数据库）"""
        return True
    
    def validate_rule_items(self, items_str: str) -> Tuple[bool, List[str]]:
        """验证规则项格式
        返回：(是否有效，解析后的列表)
        """
        if not items_str.strip():
            return False, []
        
        items = [item.strip() for item in items_str.split(',')]
        # 正则验证：允许字母、数字、点、下划线、中划线
        pattern = re.compile(r'^[a-zA-Z0-9_\-\.\u4e00-\u9fa5]+$')
        
        invalid_items = []
        for item in items:
            if not item:
                continue
            if not pattern.match(item):
                invalid_items.append(item)
        
        if invalid_items:
            return False, invalid_items
        
        return True, [item for item in items if item]
    
    def open_custom_rule_dialog(self):
        """打开自定义规则对话框"""
        # 重新加载规则，确保显示最新数据
        self.load_custom_rules()
        
        dark = isDarkTheme()
        bg_color = "#1e1e1e" if dark else "#f5f5f5"
        text_color = "#ffffff" if dark else "#333333"
        border_color = "#3d3d3d" if dark else "#d9d9d9"
        
        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("自定义规则管理")
        dialog.yesButton.setText("关闭")
        dialog.cancelButton.setVisible(False)
        # 设置对话框最小大小
        dialog.widget.setMinimumWidth(500)
        dialog.widget.setMinimumHeight(400)
        
        content_widget = QWidget()
        content_widget.setObjectName("customRuleContent")
        content_widget.setStyleSheet(f"QWidget#customRuleContent{{background-color: {bg_color};}}")
        content_layout = QVBoxLayoutWidget(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = SubtitleLabel("已有规则：")
        content_layout.addWidget(list_label)
        content_layout.addSpacing(8)
        
        self._rule_list = QListWidget()
        self._rule_list.setObjectName("ruleList")
        # 设置样式表
        if isDarkTheme():
            self._rule_list.setStyleSheet("""
                QListWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 4px;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #3d3d3d;
                }
                QListWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
            """)
        else:
            self._rule_list.setStyleSheet("""
                QListWidget {
                    background-color: #ffffff;
                    color: #333333;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    padding: 4px;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #e0e0e0;
                }
                QListWidget::item:selected {
                    background-color: #0078d4;
                    color: white;
                }
            """)
        # 添加规则到列表
        for rule_name, items in self.custom_rules.items():
            display_text = f"{rule_name}: {', '.join(items)}"
            self._rule_list.addItem(display_text)
        self._rule_list.setMinimumHeight(200)
        content_layout.addWidget(self._rule_list)
        content_layout.addSpacing(8)
        
        btn_layout = QHBoxLayout()
        
        self._new_btn = PrimaryPushButton(FIF.ADD, "新建")
        self._new_btn.clicked.connect(lambda: self.show_rule_editor(dialog, None))
        btn_layout.addWidget(self._new_btn)
        
        self._edit_btn = PushButton(FIF.EDIT, "编辑")
        self._edit_btn.clicked.connect(lambda: self.show_rule_editor(dialog, self._rule_list.currentRow()))
        btn_layout.addWidget(self._edit_btn)
        
        self._delete_btn = PushButton(FIF.DELETE, "删除")
        self._delete_btn.clicked.connect(lambda: self.delete_rule(dialog))
        btn_layout.addWidget(self._delete_btn)
        
        btn_layout.addStretch()
        content_layout.addLayout(btn_layout)
        
        dialog.viewLayout.addWidget(content_widget)
        dialog.exec_()
    
    def show_rule_editor(self, parent_dialog, edit_index: int = None):
        """显示规则编辑器"""
        dark = isDarkTheme()
        bg_color = "#1e1e1e" if dark else "#f5f5f5"
        text_color = "#ffffff" if dark else "#333333"
        hint_color = "#888888" if dark else "#666666"
        
        editor = MessageBoxBase(self)
        if edit_index is not None:
            editor.setWindowTitle("编辑规则")
        else:
            editor.setWindowTitle("新建规则")
        
        content_widget = QWidget()
        content_widget.setObjectName("ruleEditorContent")
        content_widget.setStyleSheet(f"QWidget#ruleEditorContent{{background-color: {bg_color};}}")
        content_layout = QVBoxLayoutWidget(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        name_label = SubtitleLabel("规则名称：")
        content_layout.addWidget(name_label)
        content_layout.addSpacing(4)
        
        name_input = LineEdit()
        if edit_index is not None and edit_index >= 0:
            # 从列表项中提取规则名称（格式："规则名: 项目1, 项目2"）
            list_item_text = self._rule_list.item(edit_index).text()
            rule_name = list_item_text.split(":")[0].strip()
            name_input.setText(rule_name)
        name_input.setPlaceholderText("例如：规则 2")
        content_layout.addWidget(name_input)
        content_layout.addSpacing(16)
        
        items_label = SubtitleLabel("排除项（用英文逗号分隔）：")
        content_layout.addWidget(items_label)
        content_layout.addSpacing(4)
        
        items_input = LineEdit()
        if edit_index is not None and edit_index >= 0:
            # 从列表项中提取规则名称
            list_item_text = self._rule_list.item(edit_index).text()
            rule_name = list_item_text.split(":")[0].strip()
            if rule_name in self.custom_rules:
                items_input.setText(', '.join(self.custom_rules[rule_name]))
        items_input.setPlaceholderText("例如：node_modules,.git,__pycache__")
        content_layout.addWidget(items_input)
        content_layout.addSpacing(8)
        
        hint_label = FluentBodyLabel("提示：支持以.开头的文件或文件夹，如.gitignore")
        hint_label.setStyleSheet(f"color: {hint_color}; font-size: 12px;")
        content_layout.addWidget(hint_label)
        
        editor.viewLayout.addWidget(content_widget)
        
        editor.yesButton.setText("保存")
        editor.yesButton.clicked.connect(lambda: self.save_rule(editor, edit_index, name_input.text(), items_input.text(), parent_dialog))
        
        editor.exec_()
    
    def save_rule(self, editor, edit_index: int, name: str, items_str: str, parent_dialog):
        """保存规则"""
        name = name.strip()
        items_str = items_str.strip()
        
        if not name:
            InfoBar.error(
                title="错误",
                content="规则名称不能为空",
                parent=self,
                duration=2000
            )
            return
        
        valid, result = self.validate_rule_items(items_str)
        if not valid:
            InfoBar.error(
                title="错误",
                content=f"以下项目格式不正确：{', '.join(result)}\n只允许字母、数字、点、下划线、中划线和中文",
                parent=self,
                duration=3000
            )
            return
        
        if edit_index is not None and edit_index >= 0:
            # 从列表项中提取旧规则名称
            rule_list = parent_dialog.findChild(QListWidget)
            if rule_list and rule_list.count() > edit_index:
                list_item_text = rule_list.item(edit_index).text()
                old_name = list_item_text.split(":")[0].strip()
            else:
                InfoBar.error(
                    title="错误",
                    content="无法找到要编辑的规则",
                    parent=self,
                    duration=2000
                )
                return
            
            if old_name != name:
                if name in self.custom_rules:
                    InfoBar.error(
                        title="错误",
                        content=f"规则'{name}'已存在",
                        parent=self,
                        duration=2000
                    )
                    return
                # 删除旧规则
                self.service.delete_rule(old_name)
                del self.custom_rules[old_name]
                # 添加新规则
                self.service.add_rule(name, result)
                self.custom_rules[name] = result
            else:
                # 名称未变，直接更新
                self.service.update_rule(name, result)
                self.custom_rules[name] = result
            
            # 更新 UI
            self._update_rules_combo(name)
            if parent_dialog:
                parent_dialog.findChild(QListWidget).clear()
                for rule_name, items in self.custom_rules.items():
                    parent_dialog.findChild(QListWidget).addItem(f"{rule_name}: {', '.join(items)}")
            InfoBar.success(
                title="成功",
                content=f"已保存规则：{name}",
                parent=self,
                duration=2000
            )
            editor.accept()
            return
        
        if name in self.custom_rules:
            InfoBar.error(
                title="错误",
                content=f"规则'{name}'已存在",
                parent=self,
                duration=2000
            )
            return
        
        self.service.add_rule(name, result)
        self.custom_rules[name] = result
        self._update_rules_combo(name)
        
        if parent_dialog:
            parent_dialog.findChild(QListWidget).clear()
            for rule_name, items in self.custom_rules.items():
                parent_dialog.findChild(QListWidget).addItem(f"{rule_name}: {', '.join(items)}")
        
        InfoBar.success(
            title="成功",
            content=f"已保存规则：{name}",
            parent=self,
            duration=2000
        )
        editor.accept()
    
    def delete_rule(self, parent_dialog):
        """删除规则"""
        current_row = self._rule_list.currentRow()
        if current_row < 0:
            InfoBar.warning(
                title="提示",
                content="请先选择要删除的规则",
                parent=self,
                duration=2000
            )
            return
        
        from qfluentwidgets import MessageBox
        w = MessageBox(
            title='确认删除',
            content='确定要删除选中的规则吗？',
            parent=self
        )
        if w.exec_():
            # 从列表项中提取规则名称
            list_item_text = self._rule_list.item(current_row).text()
            rule_name = list_item_text.split(":")[0].strip()
            
            self.service.delete_rule(rule_name)
            del self.custom_rules[rule_name]
            
            self._update_rules_combo()
            self._rule_list.takeItem(current_row)
            
            InfoBar.success(
                title="成功",
                content=f"已删除规则：{rule_name}",
                parent=self,
                duration=2000
            )
    
    def _update_rules_combo(self, select_custom_rule_name: str = None):
        """更新规则下拉框
        Args:
            select_custom_rule_name: 如果指定，选中该自定义规则
        """
        current_index = self._rules_combo.currentIndex()
        current_text = self._rules_combo.currentText()
        
        self._rules_combo.blockSignals(True)  # 暂时阻止信号
        
        self._rules_combo.clear()
        self._rules_combo.addItems(["无规则", "规则1：跳过.venv, .git, .idea"])
        
        # 添加自定义规则
        for rule_name in self.custom_rules.keys():
            self._rules_combo.addItem(f"自定义：{rule_name}")
        
        # 如果指定了规则名，选中它
        if select_custom_rule_name:
            for i in range(self._rules_combo.count()):
                if f"自定义：{select_custom_rule_name}" in self._rules_combo.itemText(i):
                    self._rules_combo.setCurrentIndex(i)
                    self._rules_combo.blockSignals(False)
                    return
        # 否则尽量保持原来的选择
        elif current_index < self._rules_combo.count():
            self._rules_combo.setCurrentIndex(current_index)
        
        self._rules_combo.blockSignals(False)
    
    def on_rules_combo_changed(self, index: int):
        """当下拉框选择变化时重新加载规则配置"""
        # 如果选择的是自定义规则（索引 >= 2），重新加载配置文件
        if index >= 2:
            self.load_custom_rules()
            # 重新更新下拉框，保持当前选择
            current_text = self._rules_combo.itemText(index)
            if current_text.startswith("自定义："):
                rule_name = current_text.replace("自定义：", "")
                self._update_rules_combo(rule_name)

    def select_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择文件夹",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.current_folder = Path(folder)
            self._status_label.setText(f"已选择: {self.current_folder}")
            InfoBar.success(
                title="选择成功",
                content=f"已选择文件夹: {self.current_folder.name}",
                parent=self,
                duration=2000
            )

    def generate_tree(self):
        """生成文件夹树形结构"""
        if not self.current_folder:
            InfoBar.warning(
                title="请先选择文件夹",
                content="请先点击选择文件夹按钮",
                parent=self,
                duration=2000
            )
            return
        
        self._start_scan("tree")

    def generate_folders_only(self):
        """只生成文件夹的树形结构"""
        if not self.current_folder:
            InfoBar.warning(
                title="请先选择文件夹",
                content="请先点击选择文件夹按钮",
                parent=self,
                duration=2000
            )
            return
        
        self._start_scan("folders")

    def _start_scan(self, mode: str):
        """启动后台扫描"""
        # 清理已有扫描任务
        try:
            if hasattr(self, '_thread') and self._thread and self._thread.isRunning():
                self._worker.cancel()
                self._thread.quit()
                self._thread.wait(2000)
        except RuntimeError:
            # 线程对象已被删除，忽略
            pass
            
        # 确保之前的线程和工作者完全清理
        try:
            if hasattr(self, '_thread') and self._thread:
                sip.delete(self._thread)
                self._thread = None
        except RuntimeError:
            pass
            
        try:
            if hasattr(self, '_worker') and self._worker:
                sip.delete(self._worker)
                self._worker = None
        except RuntimeError:
            pass

        self._cancelled = False
        self._show_scan_ui(True)
        
        rule_index = self._rules_combo.currentIndex()
        self._worker = FolderTreeWorker(
            root_path=self.current_folder,
            mode=mode,
            rule_index=rule_index,
            custom_rules=getattr(self, 'custom_rules', {}),
            depth=self._scan_depth
        )
        
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_tree_generated)
        self._worker.error.connect(self._on_worker_error)
        self._worker.status.connect(self._on_worker_status)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        
        self._thread.start()

    def _cancel_scan(self):
        """取消扫描"""
        try:
            if hasattr(self, '_worker') and self._worker:
                self._worker.cancel()
        except RuntimeError:
            pass
        self._cancelled = True
        self._show_scan_ui(False)
        InfoBar.info(
            title="已取消", content="扫描已取消",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )

    def _show_scan_ui(self, scanning: bool):
        """显示或隐藏扫描状态"""
        self._cancel_btn.setVisible(scanning)
        self._progress_bar.setVisible(scanning)
        self._generate_tree_btn.setEnabled(not scanning)
        self._generate_folders_btn.setEnabled(not scanning)
        self._select_btn.setEnabled(not scanning)
        if scanning:
            self._status_label.setText("正在扫描...")
        else:
            self._status_label.setText("就绪")

    def _on_tree_generated(self, tree_content: str, flat_nodes: list, folder_count: int, file_count: int):
        """处理生成的树结构"""
        self._show_scan_ui(False)
        self._cancelled = False
        self.tree_content = tree_content
        self._folder_count = folder_count
        self._file_count = file_count
        self._update_counts_display()

        self._tree_view.set_tree(flat_nodes)
        self._preview_text.setPlainText(tree_content)

        InfoBar.success(
            title="生成完成",
            content=f"共 {folder_count} 个文件夹，{file_count} 个文件",
            parent=self,
            duration=3000
        )

    def _toggle_view(self):
        """切换树视图/文本视图"""
        if self._tree_view.isVisible():
            self._tree_view.hide()
            self._preview_text.show()
            self._view_toggle_btn.setIcon(FIF.DOCUMENT)
        else:
            self._tree_view.show()
            self._preview_text.hide()
            self._view_toggle_btn.setIcon(FIF.FOLDER)

    def _on_worker_error(self, error_msg: str):
        """处理扫描错误"""
        self._show_scan_ui(False)
        self._cancelled = False
        self._status_label.setText("生成失败")
        QMessageBox.critical(self, '错误', f'生成失败：{error_msg}')

    def _on_worker_status(self, status_msg: str):
        """更新状态信息"""
        self._status_label.setText(status_msg)

    def _update_counts_display(self):
        """更新统计显示"""
        self._folder_count_label.setText(f"文件夹：{self._folder_count}")
        self._file_count_label.setText(f"文件：{self._file_count}")
    
    def _on_depth_changed(self, index: int):
        """扫描深度改变"""
        # 根据下拉框索引获取深度值：0->1, 1->2, 2->3, 3->-1
        depth_map = {0: 1, 1: 2, 2: 3, 3: -1}
        depth = depth_map.get(index, -1)
        self._scan_depth = depth
        self._save_scan_depth(depth)
        depth_text = "全部层级" if depth == -1 else f"{depth} 级"
        InfoBar.info(
            title="深度已更改",
            content=f"下次扫描将使用深度：{depth_text}",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self
        )
    
    def _load_scan_depth(self) -> int:
        """加载保存的扫描深度"""
        try:
            cfg_path = get_app_data_path("data/folder_tree_config.json")
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                return cfg.get("scan_depth", -1)
        except Exception:
            pass
        return -1
    
    def _save_scan_depth(self, depth: int):
        """保存扫描深度"""
        try:
            cfg_path = get_app_data_path("data/folder_tree_config.json")
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg = {"scan_depth": depth}
            cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def save_to_txt(self):
        """保存为txt（默认位置）"""
        if not self.tree_content:
            InfoBar.warning(
                title="无内容",
                content="请先生成树形结构",
                parent=self,
                duration=2000
            )
            return
        
        # 默认保存位置
        default_dir = get_app_data_path("data/temp_text")
        default_dir.mkdir(parents=True, exist_ok=True)
        
        default_path = default_dir / f"{self.current_folder.name}_tree.txt"
        
        try:
            with open(default_path, "w", encoding="utf-8") as f:
                f.write(self.tree_content)
            
            InfoBar.success(
                title="保存成功",
                content=f"已保存到: {default_path}",
                parent=self,
                duration=2000
            )
            self._status_label.setText(f"已保存: {default_path.name}")
        except Exception as e:
            InfoBar.error(
                title="保存失败",
                content=str(e),
                parent=self,
                duration=2000
            )

    def save_as(self):
        """另存为"""
        if not self.tree_content:
            InfoBar.warning(
                title="无内容",
                content="请先生成树形结构",
                parent=self,
                duration=2000
            )
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            f"{self.current_folder.name}_tree.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.tree_content)
                
                InfoBar.success(
                    title="保存成功",
                    content=f"已保存到: {file_path}",
                    parent=self,
                    duration=2000
                )
                self._status_label.setText(f"已保存: {Path(file_path).name}")
            except Exception as e:
                InfoBar.error(
                    title="保存失败",
                    content=str(e),
                    parent=self,
                    duration=2000
                )

    def show_rules(self):
        """显示规则设置"""
        InfoBar.info(
            title="规则设置",
            content="规则设置功能开发中...",
            parent=self,
            duration=2000
        )


class Plugin(PluginInterface):
    """文件夹树插件"""
    PLUGIN_ID = "folder_tree"
    PLUGIN_NAME = "文件夹树"
    PLUGIN_ICON = FIF.FOLDER
    PLUGIN_PRIORITY = 16

    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return FolderTreeWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        pass
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        from core import SearchResult
        service = FolderTreeService()
        results = []
        rules = service.search_rules(query)
        for rule in rules[:20]:
            # exclude_items 从 Repository 返回时已经是 list 类型
            exclude_items = rule['exclude_items'] if rule['exclude_items'] else []
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=f"规则: {rule['rule_name']}",
                description=f"排除项: {', '.join(exclude_items[:5])}{'...' if len(exclude_items) > 5 else ''}",
                icon=self.PLUGIN_ICON,
                relevance=1.0,
                action=lambda: None,
                metadata={'rule_id': rule['id'], 'rule_name': rule['rule_name']}
            )
            results.append(result)
        return results
