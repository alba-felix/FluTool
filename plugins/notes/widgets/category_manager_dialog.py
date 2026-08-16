from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QListWidgetItem,
    QPushButton, QWidget
)
from PyQt5.QtCore import Qt
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, LineEdit, PushButton, PrimaryPushButton,
    ListWidget, InfoBar, InfoBarPosition
)

from ..core.runtime import get_notes_runtime
from ..models.note import Category
from ..services.category_service import CategoryService


class CategoryManagerDialog(MessageBoxBase):
    def __init__(self, parent=None, category_service: CategoryService = None):
        super().__init__(parent)
        runtime = get_notes_runtime()
        self._category_service = category_service or runtime.category_service
        self._init_ui()
        self._connect_signals()
        self._load_categories()

    def _init_ui(self):
        self.titleLabel = SubtitleLabel('\u5206\u7c7b\u7ba1\u7406', self)
        self.viewLayout.addWidget(self.titleLabel)

        add_layout = QHBoxLayout()
        self.category_input = LineEdit()
        self.category_input.setPlaceholderText('\u8f93\u5165\u65b0\u5206\u7c7b\u540d\u79f0')
        self.category_input.setClearButtonEnabled(True)
        add_layout.addWidget(self.category_input, 1)

        self.add_btn = PushButton('\u6dfb\u52a0')
        self.add_btn.setFixedHeight(32)
        add_layout.addWidget(self.add_btn)
        self.viewLayout.addLayout(add_layout)

        self.category_list = ListWidget()
        self.category_list.setFixedHeight(300)
        self.viewLayout.addWidget(self.category_list)

        self.yesButton.setText('\u5b8c\u6210')
        self.cancelButton.hide()

        self.widget.setMinimumWidth(400)

    def _connect_signals(self):
        self.add_btn.clicked.connect(self._add_category)
        self.category_input.returnPressed.connect(self._add_category)
        self.category_list.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _load_categories(self):
        self.category_list.clear()
        categories = self._category_service.get_user_categories()
        for category in categories:
            self._add_category_item(category)

    def _add_category_item(self, category: Category):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, category.id)

        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        name_label = QLabel(category.name)
        layout.addWidget(name_label, 1)

        note_count = self._category_service.get_note_count(category.id)
        count_label = QLabel(f'{note_count} \u6761\u7b14\u8bb0')
        count_label.setStyleSheet('color: #888;')
        layout.addWidget(count_label)

        rename_btn = QPushButton('\u91cd\u547d\u540d')
        rename_btn.setFixedSize(60, 26)
        rename_btn.clicked.connect(lambda: self._rename_category(category.id))
        layout.addWidget(rename_btn)

        delete_btn = QPushButton('\u5220\u9664')
        delete_btn.setFixedSize(50, 26)
        delete_btn.clicked.connect(lambda: self._delete_category(category.id))
        layout.addWidget(delete_btn)

        self.category_list.addItem(item)
        self.category_list.setItemWidget(item, widget)

    def _add_category(self):
        name = self.category_input.text().strip()
        if not name:
            InfoBar.warning(
                title='\u63d0\u793a',
                content='\u8bf7\u8f93\u5165\u5206\u7c7b\u540d\u79f0',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        if self._category_service.get_by_name(name):
            InfoBar.warning(
                title='\u63d0\u793a',
                content='\u5206\u7c7b\u5df2\u5b58\u5728',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return

        category_id = self._category_service.add(name)
        if category_id:
            category = self._category_service.get_by_id(category_id)
            self._add_category_item(category)
            self.category_input.clear()
        else:
            InfoBar.error(
                title='\u9519\u8bef',
                content='\u6dfb\u52a0\u5206\u7c7b\u5931\u8d25',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _rename_category(self, category_id: int):
        category = self._category_service.get_by_id(category_id)
        if not category:
            return

        from qfluentwidgets import MessageBox, LineEdit
        dialog = MessageBox('\u91cd\u547d\u540d\u5206\u7c7b', '\u8bf7\u8f93\u5165\u65b0\u7684\u5206\u7c7b\u540d\u79f0:', self)
        dialog.yesButton.setText('\u786e\u5b9a')
        dialog.cancelButton.setText('\u53d6\u6d88')

        input_layout = QHBoxLayout()
        input_edit = LineEdit()
        input_edit.setText(category.name)
        input_layout.addWidget(input_edit)
        dialog.textLayout.addLayout(input_layout)

        if dialog.exec():
            new_name = input_edit.text().strip()
            if new_name and new_name != category.name:
                if self._category_service.rename(category_id, new_name):
                    self._load_categories()
                else:
                    InfoBar.error(
                        title='\u9519\u8bef',
                        content='\u91cd\u547d\u540d\u5931\u8d25\uff0c\u540d\u79f0\u53ef\u80fd\u5df2\u5b58\u5728',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=2000,
                        parent=self
                    )

    def _delete_category(self, category_id: int):
        category = self._category_service.get_by_id(category_id)
        if not category:
            return

        note_count = self._category_service.get_note_count(category_id)
        message = f'\u786e\u5b9a\u5220\u9664\u5206\u7c7b "{category.name}" \u5417\uff1f'
        if note_count > 0:
            message += f'\n\u8be5\u5206\u7c7b\u4e0b\u7684 {note_count} \u6761\u7b14\u8bb0\u5c06\u79fb\u52a8\u5230"\u9ed8\u8ba4"\u5206\u7c7b\u3002'

        from qfluentwidgets import MessageBox
        dialog = MessageBox('\u5220\u9664\u5206\u7c7b', message, self)
        dialog.yesButton.setText('\u5220\u9664')
        dialog.cancelButton.setText('\u53d6\u6d88')

        if dialog.exec():
            if self._category_service.delete(category_id):
                self._load_categories()
            else:
                InfoBar.error(
                    title='\u9519\u8bef',
                    content='\u5220\u9664\u5206\u7c7b\u5931\u8d25',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )

    def _on_item_double_clicked(self, item: QListWidgetItem):
        category_id = item.data(Qt.UserRole)
        self._rename_category(category_id)
