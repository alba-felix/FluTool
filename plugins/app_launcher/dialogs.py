"""应用启动插件对话框组件"""
import os
from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import QFileDialog, QHBoxLayout
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    BodyLabel, MessageBoxBase, SubtitleLabel, ComboBox, TextEdit,
)

from . import CATEGORY_PRESET_COLORS, get_category_icon_options


class AppEditDialog(MessageBoxBase):
    """应用编辑对话框"""

    def __init__(self, app_data: Dict[str, Any], categories: List[Dict], parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.categories = categories

        self.titleLabel = SubtitleLabel("编辑应用", self)
        self.viewLayout.addWidget(self.titleLabel)

        # 应用名称
        self.name_label = BodyLabel("应用名称:", self)
        self.viewLayout.addWidget(self.name_label)
        self.name_edit = LineEdit(self)
        self.name_edit.setText(app_data.get('name', ''))
        self.name_edit.setClearButtonEnabled(True)
        self.name_edit.returnPressed.connect(self.yesButton.click)
        self.viewLayout.addWidget(self.name_edit)

        # 目标路径
        self.path_label = BodyLabel("目标路径:", self)
        self.viewLayout.addWidget(self.path_label)
        path_layout = QHBoxLayout()
        self.path_edit = LineEdit(self)
        self.path_edit.setText(app_data.get('target_path', ''))
        self.path_edit.setClearButtonEnabled(True)
        self.path_edit.returnPressed.connect(self.yesButton.click)
        path_layout.addWidget(self.path_edit)

        self.browse_btn = PushButton("浏览", self)
        self.browse_btn.setFixedWidth(60)
        self.browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(self.browse_btn)
        self.viewLayout.addLayout(path_layout)

        # 启动参数
        self.args_label = BodyLabel("启动参数:", self)
        self.viewLayout.addWidget(self.args_label)
        self.args_edit = LineEdit(self)
        self.args_edit.setText(app_data.get('arguments', ''))
        self.args_edit.setClearButtonEnabled(True)
        self.args_edit.setPlaceholderText("可选")
        self.args_edit.returnPressed.connect(self.yesButton.click)
        self.viewLayout.addWidget(self.args_edit)

        # 备注信息
        self.notes_label = BodyLabel("备注:", self)
        self.viewLayout.addWidget(self.notes_label)
        self.notes_edit = TextEdit(self)
        self.notes_edit.setPlaceholderText("可选，可填写用途说明等")
        self.notes_edit.setFixedHeight(80)
        self.notes_edit.setPlainText(app_data.get('notes', ''))
        self.viewLayout.addWidget(self.notes_edit)

        # 所属分类
        self.category_label = BodyLabel("所属分类:", self)
        self.viewLayout.addWidget(self.category_label)
        self.category_combo = ComboBox(self)
        self.category_combo.addItem("全部")
        current_category_id = app_data.get('category_id')
        for idx, cat in enumerate(categories):
            self.category_combo.addItem(cat['name'])
            if cat['id'] == current_category_id:
                self.category_combo.setCurrentIndex(idx + 1)
        self.viewLayout.addWidget(self.category_combo)

        self.widget.setMinimumWidth(450)
        self.name_edit.setFocus()

    def _browse_path(self):
        """浏览文件路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用", self.path_edit.text(),
            "所有支持的文件 (*.exe *.py *.bat *.cmd *.ps1 *.vbs);;"
            "可执行文件 (*.exe);;"
            "Python 脚本 (*.py);;"
            "批处理文件 (*.bat *.cmd);;"
            "PowerShell 脚本 (*.ps1);;"
            "VBScript (*.vbs);;"
            "所有文件 (*.*)"
        )
        if file_path:
            self.path_edit.setText(file_path)
            if not self.name_edit.text():
                self.name_edit.setText(os.path.splitext(os.path.basename(file_path))[0])

    def get_data(self) -> Dict[str, Any]:
        """获取编辑后的数据"""
        category_idx = self.category_combo.currentIndex()
        category_id = None if category_idx == 0 else self.categories[category_idx - 1]['id']

        return {
            'name': self.name_edit.text().strip(),
            'target_path': self.path_edit.text().strip(),
            'arguments': self.args_edit.text().strip(),
            'category_id': category_id,
            'notes': self.notes_edit.toPlainText().strip(),
        }

    def validate(self) -> bool:
        """验证输入"""
        return bool(self.name_edit.text().strip() and self.path_edit.text().strip())


class BatchMoveDialog(MessageBoxBase):
    """批量移动分类对话框"""

    def __init__(self, categories: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("批量移动分类", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.category_label = BodyLabel("目标分类:", self)
        self.viewLayout.addWidget(self.category_label)
        self.category_combo = ComboBox(self)
        self.category_combo.addItem("全部")
        for category in categories:
            self.category_combo.addItem(category.get("name", "未命名分类"))
        self.viewLayout.addWidget(self.category_combo)
        self.widget.setMinimumWidth(360)

    def get_category_id(self, categories: List[Dict[str, Any]]) -> Optional[int]:
        """获取选中的分类 ID"""
        current_index = self.category_combo.currentIndex()
        if current_index <= 0:
            return None
        return categories[current_index - 1].get("id")


class BatchEditDialog(MessageBoxBase):
    """批量修改属性对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("批量修改属性", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.args_label = BodyLabel("统一启动参数:", self)
        self.viewLayout.addWidget(self.args_label)
        self.args_edit = LineEdit(self)
        self.args_edit.setPlaceholderText("留空表示不修改")
        self.viewLayout.addWidget(self.args_edit)

        self.notes_label = BodyLabel("统一备注:", self)
        self.viewLayout.addWidget(self.notes_label)
        self.notes_edit = TextEdit(self)
        self.notes_edit.setPlaceholderText("留空表示不修改")
        self.notes_edit.setFixedHeight(80)
        self.viewLayout.addWidget(self.notes_edit)

        self.favorite_label = BodyLabel("收藏状态:", self)
        self.viewLayout.addWidget(self.favorite_label)
        self.favorite_combo = ComboBox(self)
        self.favorite_combo.addItems(["不修改", "设为收藏", "取消收藏"])
        self.viewLayout.addWidget(self.favorite_combo)

        self.widget.setMinimumWidth(420)

    def get_updates(self) -> Dict[str, Any]:
        """获取批量更新字段"""
        updates = {}
        arguments = self.args_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()
        if arguments:
            updates["arguments"] = arguments
        if notes:
            updates["notes"] = notes

        favorite_index = self.favorite_combo.currentIndex()
        if favorite_index == 1:
            updates["is_favorite"] = 1
        elif favorite_index == 2:
            updates["is_favorite"] = 0
        return updates


class CategoryEditDialog(MessageBoxBase):
    """分类编辑对话框"""

    def __init__(self, title: str, category_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.category_data = category_data or {}

        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.name_label = BodyLabel("分类名称:", self)
        self.viewLayout.addWidget(self.name_label)
        self.name_edit = LineEdit(self)
        self.name_edit.setText(self.category_data.get("name", ""))
        self.name_edit.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.name_edit)

        self.icon_label = BodyLabel("分类图标:", self)
        self.viewLayout.addWidget(self.icon_label)
        self.icon_combo = ComboBox(self)
        icon_options = get_category_icon_options()
        for label, _ in icon_options:
            self.icon_combo.addItem(label)
        current_icon_name = self.category_data.get("icon_name", "")
        current_icon_index = next((index for index, (_, value) in enumerate(icon_options) if value == current_icon_name), 0)
        self.icon_combo.setCurrentIndex(current_icon_index)
        self.viewLayout.addWidget(self.icon_combo)

        self.color_label = BodyLabel("分类颜色:", self)
        self.viewLayout.addWidget(self.color_label)
        self.color_combo = ComboBox(self)
        for label, _ in CATEGORY_PRESET_COLORS:
            self.color_combo.addItem(label)
        current_color = self.category_data.get("color", "")
        current_color_index = next((index for index, (_, value) in enumerate(CATEGORY_PRESET_COLORS) if value == current_color), 0)
        self.color_combo.setCurrentIndex(current_color_index)
        self.viewLayout.addWidget(self.color_combo)

        self.widget.setMinimumWidth(420)
        self.name_edit.setFocus()

    def get_data(self) -> Dict[str, Any]:
        """获取分类数据"""
        icon_name = get_category_icon_options()[self.icon_combo.currentIndex()][1]
        color = CATEGORY_PRESET_COLORS[self.color_combo.currentIndex()][1]
        return {
            "name": self.name_edit.text().strip(),
            "icon_name": icon_name,
            "color": color,
        }
