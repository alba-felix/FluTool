"""全局搜索对话框"""

from typing import List
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidgetItem, QStackedWidget
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
from qfluentwidgets import (
    LineEdit, ListWidget, PushButton, ToolButton,
    FluentIcon as FIF, MessageBoxBase, SubtitleLabel, IndeterminateProgressRing
)
from core import SearchResult


class GlobalSearchDialog(MessageBoxBase):
    """全局搜索对话框"""

    result_selected = pyqtSignal(object)
    search_completed = pyqtSignal(list)

    def __init__(self, search_manager, parent=None):
        self.search_manager = search_manager
        super().__init__(parent)
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_search)
        self.search_completed.connect(self._display_results)
        self._setup_ui()

    def _setup_ui(self):
        """构建界面"""
        # 隐藏底部按钮栏
        self.buttonGroup.hide()

        # 创建标题栏布局（标题 + 关闭按钮）
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        self.titleLabel = SubtitleLabel("全局搜索", self)
        title_layout.addWidget(self.titleLabel)
        title_layout.addStretch()

        # 右上角关闭按钮
        self.close_btn = ToolButton(FIF.CLOSE, self)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.setToolTip("关闭")
        self.close_btn.clicked.connect(self.close)
        title_layout.addWidget(self.close_btn)

        self.viewLayout.addLayout(title_layout)

        # 搜索输入框 + 进度圆圈
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索所有内容...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setFixedHeight(40)
        search_layout.addWidget(self.search_input, 1)

        # 不确定性进度圆圈
        self.progress_ring = IndeterminateProgressRing(self)
        self.progress_ring.setFixedSize(24, 24)
        self.progress_ring.setVisible(False)
        search_layout.addWidget(self.progress_ring)

        self.viewLayout.addLayout(search_layout)

        # 结果列表
        self.result_list = ListWidget(self)
        self.result_list.setFrameShape(ListWidget.NoFrame)
        self.result_list.itemClicked.connect(self._on_result_clicked)
        self.viewLayout.addWidget(self.result_list)

        self.widget.setMinimumWidth(650)
        self.widget.setMinimumHeight(450)

        self.search_input.setFocus()

    def _on_search(self, text: str):
        """搜索（带防抖）"""
        self.search_manager.cancel()
        self._debounce_timer.stop()

        if not text or not text.strip():
            self.result_list.clear()
            self.progress_ring.setVisible(False)
            return

        self._debounce_timer.start(200)

    def _do_search(self):
        """执行异步搜索"""
        text = self.search_input.text().strip()
        if not text:
            self.progress_ring.setVisible(False)
            return

        self.result_list.clear()
        self.progress_ring.setVisible(True)

        def _on_results(results):
            self.search_completed.emit(results)

        self.search_manager.search_async(text, _on_results)

    def _display_results(self, results: List[SearchResult]):
        """显示搜索结果"""
        self.progress_ring.setVisible(False)
        if not results:
            return

        # 按插件分组
        grouped_results = {}
        for result in results:
            if result.plugin_id not in grouped_results:
                grouped_results[result.plugin_id] = []
            grouped_results[result.plugin_id].append(result)

        for plugin_id, plugin_results in grouped_results.items():
            if not plugin_results:
                continue
            plugin_name = plugin_results[0].plugin_name
            header_item = QListWidgetItem(f"📁 {plugin_name}")
            header_item.setFlags(Qt.ItemIsEnabled)
            header_item.setForeground(Qt.gray)
            self.result_list.addItem(header_item)

            for result in plugin_results:
                item = QListWidgetItem(f"  {result.title}")
                item.setData(Qt.UserRole, result)
                item.setToolTip(result.description)
                self.result_list.addItem(item)

    def _on_result_clicked(self, item: QListWidgetItem):
        """结果项点击"""
        result = item.data(Qt.UserRole)
        if result and isinstance(result, SearchResult):
            self.result_selected.emit(result)
            self.close()

    def show(self):
        """显示对话框"""
        super().exec()
        self.search_input.clear()
        self.search_input.setFocus()
