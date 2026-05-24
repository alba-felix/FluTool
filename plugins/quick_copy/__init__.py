"""快速复制插件"""

from typing import List, Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QGridLayout, QLabel, QHBoxLayout,
    QFrame, QPushButton, QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    StrongBodyLabel, InfoBar, InfoBarPosition, PushButton,
    FluentIcon as FIF, MessageBoxBase, SubtitleLabel, TextEdit,
    LineEdit, BodyLabel, isDarkTheme, qconfig, MessageBox
)
from qfluentwidgets.components.widgets.card_widget import (
    HeaderCardWidget, CardSeparator
)
from core import PluginInterface
from .service import QuickCopyService


class EditCardDialog(MessageBoxBase):
    """编辑卡片对话框"""

    delete_requested = pyqtSignal(int)

    def __init__(self, card_data: Dict[str, Any], parent=None):
        self.card_data = card_data.copy()
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """构建界面"""
        self.titleLabel = SubtitleLabel("编辑快速复制卡片", self)
        self.viewLayout.addWidget(self.titleLabel)

        # 标题输入
        self.viewLayout.addWidget(StrongBodyLabel("标题:", self))
        self.title_input = LineEdit(self)
        self.title_input.setText(self.card_data.get("title", ""))
        self.title_input.setPlaceholderText("输入卡片标题...")
        self.title_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.title_input)

        # 内容项输入（四个单独输入框）
        self.viewLayout.addWidget(StrongBodyLabel("内容项:", self))

        self.item_inputs = []
        items = self.card_data.get("items", ["", "", "", ""])

        for i in range(4):
            item_input = LineEdit(self)
            item_input.setPlaceholderText(f"内容 {i + 1}")
            if i < len(items):
                item_input.setText(items[i])
            item_input.returnPressed.connect(lambda: self.yesButton.click())
            self.item_inputs.append(item_input)
            self.viewLayout.addWidget(item_input)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.deleteButton = PushButton("删除卡片", self.buttonGroup)
        self.deleteButton.setStyleSheet("""
            QPushButton {
                color: #d83b01;
                background-color: transparent;
                border: 1px solid #d83b01;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: white;
                background-color: #d83b01;
            }
        """)
        self.deleteButton.clicked.connect(self._on_delete_clicked)
        self.buttonLayout.insertWidget(0, self.deleteButton, 0, Qt.AlignVCenter)
        self.buttonLayout.insertStretch(1, 1)
        self.widget.setMinimumWidth(400)

    def _on_delete_clicked(self) -> None:
        """发出删除卡片请求"""
        card_id = self.card_data.get("id")
        if card_id is None:
            return
        self.delete_requested.emit(card_id)

    def get_data(self) -> Dict[str, Any]:
        """获取编辑后的数据"""
        items = []
        for item_input in self.item_inputs:
            text = item_input.text().strip()
            if text:
                items.append(text)

        return {
            "id": self.card_data.get("id"),
            "title": self.title_input.text().strip(),
            "items": items
        }

    def validate(self) -> bool:
        """验证表单内容"""
        title = self.title_input.text().strip()
        if not title:
            InfoBar.warning(
                title="无法保存",
                content="标题不能为空",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return False

        has_item = any(item_input.text().strip() for item_input in self.item_inputs)
        if not has_item:
            InfoBar.warning(
                title="无法保存",
                content="至少需要一个内容项",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return False

        return True


class QuickCopyCard(HeaderCardWidget):
    """快速复制卡片"""
    
    edit_clicked = pyqtSignal(int)  # 发送卡片ID

    def __init__(self, card_data: Dict[str, Any], parent=None):
        self.card_data = card_data
        super().__init__(parent)
        self.setTitle(card_data.get("title", "未命名"))
        self.setFixedSize(200, 200)
    
    def _postInit(self):
        """初始化后设置（覆盖父类方法）"""
        # 移除默认的 separator
        if hasattr(self, 'separator') and self.separator:
            self.separator.hide()

        # 自定义标题栏背景色（橙色）
        self.headerView.setStyleSheet("""
            QWidget {
                background-color: #f59e0b;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        self.headerView.setCursor(Qt.PointingHandCursor)

        # 修改标题标签样式
        self.headerLabel.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding-left: 8px;
            }
        """)

        # 创建内容容器（只创建一次）
        content_container = QWidget(self.view)
        content_container.setObjectName("contentContainer")
        content_container.setStyleSheet("background-color: transparent;")

        # 创建垂直布局
        container_layout = QVBoxLayout(content_container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(6)

        # 内容列表区域（保存为成员变量，供刷新时使用）
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(4)

        # 添加到容器布局
        container_layout.addLayout(self.items_layout)
        container_layout.addStretch()

        # 将容器添加到 viewLayout
        self.viewLayout.addWidget(content_container, 1)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)

        # 填充初始内容
        self._refresh_content()

        # 主题切换时刷新图标
        qconfig.themeChangedFinished.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        """主题变化时重建内容行，刷新图标"""
        QTimer.singleShot(0, self._refresh_content)

    def _refresh_content(self):
        """刷新内容显示（清空现有行，重新添加）"""
        # 清空 items_layout 中的所有子控件
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # 获取数据中的内容项，跳过空字符串
        items = self.card_data.get("items", [])
        for item_text in items:
            if item_text.strip():      # 只添加非空内容
                self._add_content_row(item_text, "复制")
    
    def _on_header_clicked(self, event):
        """标题栏点击事件"""
        self.edit_clicked.emit(self.card_data.get("id", 0))
    
    def mousePressEvent(self, event):
        """重写鼠标点击事件"""
        if self.headerView.underMouse():
            self._on_header_clicked(event)
        else:
            super().mousePressEvent(event)
    
    def update_data(self, card_data: Dict[str, Any]):
        """更新卡片数据"""
        self.card_data = card_data
        self.setTitle(card_data.get("title", "未命名"))
        self._refresh_content()

    def _add_content_row(self, text: str, btn_text: str) -> None:
        """添加内容行"""
        row_widget = QWidget()
        row_widget.setStyleSheet("background-color: transparent;")
        
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 3, 5, 3)
        row_layout.setSpacing(8)

        # 内容标签（左侧）
        content_label = BodyLabel(text)
        content_label.setWordWrap(True)
        row_layout.addWidget(content_label, 1)

        # 复制按钮（右侧）
        copy_btn = PushButton("", self)
        copy_btn.setIcon(FIF.COPY)
        copy_btn.setFixedSize(28, 28)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
        """)
        copy_btn.clicked.connect(lambda: self._copy_to_clipboard(text))
        row_layout.addWidget(copy_btn)

        self.items_layout.addWidget(row_widget)

        # 添加分隔线
        separator = CardSeparator(self)
        self.items_layout.addWidget(separator)

    def _copy_to_clipboard(self, text: str) -> None:
        """复制到剪贴板"""
        QApplication.clipboard().setText(text)
        InfoBar.success(
            title="已复制",
            content=f"已复制：{text}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )


class QuickCopyWidget(QWidget):
    """快速复制插件界面"""

    PLUGIN_ID = "quick_copy"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = QuickCopyService()
        self.cards_data: List[Dict[str, Any]] = []
        self.setObjectName("quickCopyWidget")
        self._scroll_layout = None
        self._item_count = 0
        self._cards = []
        self._setup_ui()
    
    def _init_paths(self) -> None:
        """初始化路径"""
        # 此方法当前未使用，保留以备后续扩展
        pass

    def _setup_ui(self) -> None:
        """构建界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 标题栏
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title = StrongBodyLabel("快速复制", self)
        header_layout.addWidget(title)

        header_layout.addStretch()

        add_btn = PushButton("添加快速复制", self)
        add_btn.setIcon(FIF.ADD)
        add_btn.clicked.connect(self._add_item)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # 滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(scroll_area)

        # 滚动内容
        scroll_content = QWidget()
        self._scroll_layout = QGridLayout(scroll_content)
        self._scroll_layout.setSpacing(8)
        self._scroll_layout.setContentsMargins(5, 5, 5, 5)
        self._scroll_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # 临时占位符（将在加载数据时被替换）
        placeholder = QLabel("暂无快速复制项目", scroll_content)
        placeholder.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._scroll_layout.addWidget(placeholder, 0, 0, 1, 5)

        scroll_area.setWidget(scroll_content)

        # 完全透明背景
        self.setStyleSheet("QWidget#quickCopyWidget { background-color: transparent; }")
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        scroll_content.setStyleSheet("QWidget { background-color: transparent; }")

    def _add_item(self) -> None:
        """添加快速复制项"""
        try:
            card_title = f"卡片 {len(self.cards_data) + 1}"
            new_card = self.service.add_card(card_title, len(self.cards_data))
            self.cards_data.append(new_card)
            self._display_cards()
        except Exception as e:
            self.core.logger.error(f"添加快速复制卡片失败: {e}")
            InfoBar.error(
                title="添加失败",
                content="无法添加快速复制卡片",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _load_cards(self) -> None:
        """从数据库加载卡片数据"""
        try:
            self.cards_data = self.service.list_cards()
        except Exception as e:
            self.core.logger.error(f"加载快速复制数据失败: {e}")
            self.cards_data = []
        
        self._display_cards()
    
    def _display_cards(self) -> None:
        """显示卡片列表（每次调用先清空现有控件）"""
        # 1. 彻底移除布局中所有已有控件
        while self._scroll_layout.count():
            item = self._scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # 2. 重置内部状态
        self._cards = []
        self._item_count = 0

        # 3. 无数据时显示占位符
        if not self.cards_data:
            placeholder = QLabel("暂无快速复制项目")
            placeholder.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            self._scroll_layout.addWidget(placeholder, 0, 0, 1, 3)
            return

        # 4. 重新创建所有卡片
        for i, card_data in enumerate(self.cards_data):
            card = QuickCopyCard(card_data, self)
            card.edit_clicked.connect(self._on_card_edit)
            self._scroll_layout.addWidget(card, i // 5, i % 5, 1, 1)
            self._cards.append(card)
            self._item_count = i + 1

    def _on_card_delete(self, card_id: int, dialog: EditCardDialog = None) -> None:
        """处理卡片删除请求"""
        card_data = next((data for data in self.cards_data if data.get("id") == card_id), None)
        if card_data is None:
            return

        box = MessageBox("确认删除", f"确定要删除卡片 '{card_data.get('title', '未命名')}' 吗？", dialog or self)
        if not box.exec():
            return

        try:
            if not self.service.delete_card(card_id):
                raise RuntimeError(f"card not found: {card_id}")

            self.cards_data = [data for data in self.cards_data if data.get("id") != card_id]
            self._display_cards()
            if dialog is not None:
                dialog.reject()
            InfoBar.success(
                title="删除成功",
                content="卡片已删除",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            self.core.logger.error(f"删除快速复制卡片失败: {e}")
            InfoBar.error(
                title="删除失败",
                content="无法删除快速复制卡片",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
    
    def _on_card_edit(self, card_id: int) -> None:
        """处理卡片编辑请求"""
        card_data = None
        card_index = -1
        for i, data in enumerate(self.cards_data):
            if data.get("id") == card_id:
                card_data = data
                card_index = i
                break
        
        if card_data is None or card_index < 0:
            return
        
        dialog = EditCardDialog(card_data, self)
        dialog.delete_requested.connect(lambda cid: self._on_card_delete(cid, dialog))
        if dialog.exec():
            new_data = dialog.get_data()
            new_data["id"] = card_id

            try:
                self.service.update_card(card_id, new_data["title"], new_data["items"])

                self.cards_data[card_index] = new_data

                if card_index < len(self._cards):
                    self._cards[card_index].update_data(new_data)

                InfoBar.success(
                    title="保存成功",
                    content="卡片已更新",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            except Exception as e:
                self.core.logger.error(f"保存快速复制卡片失败: {e}")
                InfoBar.error(
                    title="保存失败",
                    content="无法保存快速复制卡片",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def load_data(self) -> None:
        """加载数据（通常由插件框架调用）"""
        self._load_cards()


class Plugin(PluginInterface):
    """快速复制插件"""
    PLUGIN_ID = "quick_copy"
    PLUGIN_NAME = "快速复制"
    PLUGIN_ICON = FIF.COPY
    PLUGIN_PRIORITY = 0

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.get_name()}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.get_name()}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return QuickCopyWidget(self.core, parent)

    def _do_load_data(self) -> None:
        if self._widget is not None:
            self._widget.load_data()
    
    def supports_search(self) -> bool:
        return True
    
    def search(self, query: str):
        from core import SearchResult
        service = QuickCopyService()
        results = []
        items = service.search(query)
        for item in items[:20]:
            content = item['content']
            if len(content) > 80:
                content = content[:80] + '...'
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=content,
                description=f"卡片: {item['card_title']}",
                icon=self.PLUGIN_ICON,
                relevance=1.0,
                action=lambda c=item['content']: QApplication.clipboard().setText(c),
                metadata={'item_id': item['id'], 'card_id': item['card_id']}
            )
            results.append(result)
        return results
