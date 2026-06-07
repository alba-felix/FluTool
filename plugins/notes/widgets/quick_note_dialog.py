from typing import Optional

from PyQt5.QtWidgets import QHBoxLayout
from qfluentwidgets import MessageBoxBase, SubtitleLabel, LineEdit, TextEdit, PrimaryPushButton, PushButton, ComboBox, CaptionLabel

from ..core.runtime import get_notes_runtime
from ..services.category_service import CategoryService


class QuickNoteDialog(MessageBoxBase):
    """快速添加笔记对话框"""
    
    def __init__(
        self,
        parent=None,
        current_category_id: int = None,
        category_service: CategoryService = None,
    ):
        super().__init__(parent)
        runtime = get_notes_runtime()
        self._category_service = category_service or runtime.category_service
        self._current_category_id = current_category_id
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.titleLabel = SubtitleLabel('\u5feb\u901f\u6dfb\u52a0\u7b14\u8bb0', self)
        self.viewLayout.addWidget(self.titleLabel)

        # 标题输入
        self.title_input = LineEdit(self)
        self.title_input.setPlaceholderText('\u6807\u9898\uff08\u53ef\u9009\uff09')
        self.title_input.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.title_input)

        # 内容输入
        self.content_input = TextEdit(self)
        self.content_input.setPlaceholderText('\u5185\u5bb9\uff08\u5fc5\u586b\uff09')
        self.content_input.setFixedHeight(200)
        self.viewLayout.addWidget(self.content_input)

        # 分类选择
        category_layout = QHBoxLayout()
        category_label = CaptionLabel('\u5206\u7c7b:')
        category_layout.addWidget(category_label)
        
        self.category_combo = ComboBox()
        self._refresh_categories()
        category_layout.addWidget(self.category_combo, 1)
        
        self.viewLayout.addLayout(category_layout)

        self.yesButton.setText('\u4fdd\u5b58')
        self.cancelButton.setText('\u53d6\u6d88')

        self.widget.setMinimumWidth(500)
        self.window().setMinimumWidth(500)

    def _connect_signals(self):
        pass
    
    def _refresh_categories(self):
        """刷新分类列表"""
        categories = self._category_service.get_all()
        self.category_combo.clear()
        
        # 如果没有指定分类，使用第一个分类
        default_index = 0
        
        for i, category in enumerate(categories):
            self.category_combo.addItem(category.name)
            idx = self.category_combo.count() - 1
            self.category_combo.setItemData(idx, category.id)
            
            # 如果是当前分类，设置为选中
            if self._current_category_id and category.id == self._current_category_id:
                default_index = i
        
        # 设置默认选中的分类
        if self.category_combo.count() > 0:
            self.category_combo.setCurrentIndex(default_index)

    def validate(self) -> bool:
        content = self.content_input.toPlainText().strip()
        if not content:
            return False
        return True

    def get_title(self) -> str:
        return self.title_input.text().strip()

    def get_content(self) -> str:
        return self.content_input.toPlainText().strip()
    
    def get_category_id(self) -> Optional[int]:
        """获取选中的分类 ID"""
        if self.category_combo.count() <= 0:
            return None
        index = self.category_combo.currentIndex()
        if index < 0:
            return None
        return self.category_combo.itemData(index)
