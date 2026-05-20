from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QFileDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from qfluentwidgets import (
    FluentIcon as FIF, PushButton, ComboBox, LineEdit, InfoBar, InfoBarPosition,
    MessageBoxBase, SubtitleLabel, MessageBox, TableWidget, BodyLabel,
    PrimaryPushButton, ProgressBar, RoundMenu, Action,
)

from .page_interface import TabPageInterface
from .vocabulary_service import VocabularyService


COL_ENGLISH = 0
COL_CHINESE = 1
COL_PRONUNCIATION = 2
COL_CATEGORY = 3


class WordEditDialog(MessageBoxBase):
    """添加/编辑单词对话框"""

    def __init__(self, service: VocabularyService, word_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.word_data = word_data
        self._setup_ui()

    def _setup_ui(self):
        self.titleLabel = SubtitleLabel("添加单词" if self.word_data is None else "编辑单词", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(BodyLabel("英文:", self))
        self.english_input = LineEdit(self)
        self.english_input.setPlaceholderText("输入对应英文...")
        if self.word_data:
            self.english_input.setText(self.word_data.get("english", ""))
        self.english_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.english_input)

        self.viewLayout.addWidget(BodyLabel("中文:", self))
        self.chinese_input = LineEdit(self)
        self.chinese_input.setPlaceholderText("输入中文意思...")
        if self.word_data:
            self.chinese_input.setText(self.word_data.get("chinese", ""))
        self.chinese_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.chinese_input)

        self.viewLayout.addWidget(BodyLabel("发音:", self))
        self.pronunciation_input = LineEdit(self)
        self.pronunciation_input.setPlaceholderText("输入发音/音标（可选）...")
        if self.word_data:
            self.pronunciation_input.setText(self.word_data.get("pronunciation", ""))
        self.pronunciation_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.pronunciation_input)

        self.viewLayout.addWidget(BodyLabel("所属分类:", self))
        self.category_combo = ComboBox(self)
        categories = self.service.list_categories()
        self.category_combo.addItem("（无分类）", userData=None)
        current_category_id = self.word_data.get("category_id") if self.word_data else None
        for cat in categories:
            self.category_combo.addItem(cat["name"], userData=cat["id"])
        if current_category_id is not None:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == current_category_id:
                    self.category_combo.setCurrentIndex(i)
                    break
        self.viewLayout.addWidget(self.category_combo)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(400)

    def get_data(self) -> Dict[str, Any]:
        return {
            "english": self.english_input.text().strip(),
            "chinese": self.chinese_input.text().strip(),
            "pronunciation": self.pronunciation_input.text().strip(),
            "category_id": self.category_combo.currentData(),
        }

    def validate(self) -> bool:
        if not self.english_input.text().strip():
            InfoBar.warning(
                title="无法保存", content="英文不能为空",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return False
        if not self.chinese_input.text().strip():
            InfoBar.warning(
                title="无法保存", content="中文不能为空",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return False
        return True


class CategoryDialog(MessageBoxBase):
    """添加/编辑分类对话框"""

    def __init__(self, current_name: str = "", parent=None):
        super().__init__(parent)
        self.current_name = current_name
        self._setup_ui()

    def _setup_ui(self):
        title = "编辑分类" if self.current_name else "添加分类"
        self.titleLabel = SubtitleLabel(title, self)
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(BodyLabel("分类名称:", self))
        self.name_input = LineEdit(self)
        self.name_input.setPlaceholderText("输入分类名称...")
        if self.current_name:
            self.name_input.setText(self.current_name)
        self.name_input.returnPressed.connect(lambda: self.yesButton.click())
        self.viewLayout.addWidget(self.name_input)

        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(300)

    def get_name(self) -> str:
        return self.name_input.text().strip()

    def validate(self) -> bool:
        if not self.name_input.text().strip():
            InfoBar.warning(
                title="无法保存", content="分类名称不能为空",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return False
        return True


class VocabularyWidget(QWidget):
    """单词背诵管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = VocabularyService()
        self._show_english = True
        self._show_chinese = True
        self._show_pronunciation = True
        self._displayed_words: List[Dict[str, Any]] = []
        self._all_words: List[Dict[str, Any]] = []
        self._current_category_id: Optional[int] = None
        self._search_text = ""
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ===== 顶部工具栏：搜索 + 分类 + 隐藏按钮 + 导入导出 =====
        top_bar = QWidget(self)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索单词...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(240)
        self.search_input.textChanged.connect(self._on_search)
        top_layout.addWidget(self.search_input)

        self.category_combo = ComboBox(self)
        self.category_combo.setMinimumWidth(120)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        top_layout.addWidget(self.category_combo)

        self.hide_cn_btn = PushButton("隐藏中文")
        self.hide_cn_btn.setCheckable(True)
        self.hide_cn_btn.clicked.connect(self._toggle_chinese)
        top_layout.addWidget(self.hide_cn_btn)

        self.hide_en_btn = PushButton("隐藏英文")
        self.hide_en_btn.setCheckable(True)
        self.hide_en_btn.clicked.connect(self._toggle_english)
        top_layout.addWidget(self.hide_en_btn)

        self.hide_pron_btn = PushButton("隐藏发音")
        self.hide_pron_btn.setCheckable(True)
        self.hide_pron_btn.clicked.connect(self._toggle_pronunciation)
        top_layout.addWidget(self.hide_pron_btn)

        self.import_btn = PushButton("导入单词")
        self.import_btn.clicked.connect(self._import_words)
        top_layout.addWidget(self.import_btn)

        self.export_btn = PushButton("导出单词")
        self.export_btn.clicked.connect(self._export_words)
        top_layout.addWidget(self.export_btn)

        top_layout.addStretch()
        layout.addWidget(top_bar)

        # ===== 统计信息栏 =====
        stats_bar = QWidget(self)
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(8)

        self.total_label = BodyLabel("总单词数: 0", self)
        stats_layout.addWidget(self.total_label)

        self.displayed_label = BodyLabel("显示单词数: 0", self)
        stats_layout.addWidget(self.displayed_label)

        self.progress_bar = ProgressBar(self)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMinimumHeight(8)
        stats_layout.addWidget(self.progress_bar)

        self.filter_progress_label = BodyLabel("", self)
        stats_layout.addWidget(self.filter_progress_label)

        stats_layout.addStretch()
        layout.addWidget(stats_bar)

        # ===== 单词表格（5列：行号 + 英文 + 中文 + 发音 + 分类） =====
        self.table = TableWidget(self)
        self.table.setBorderRadius(8)
        self.table.setBorderVisible(True)
        self.table.setWordWrap(False)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["英文", "中文", "发音", "分类"])

        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.verticalHeader().setMinimumSectionSize(40)
        self.table.horizontalHeader().setSectionResizeMode(COL_ENGLISH, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_CHINESE, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_PRONUNCIATION, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_CATEGORY, QHeaderView.ResizeToContents)

        table_font = QFont()
        table_font.setPointSize(14)
        self.table.setFont(table_font)

        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)

        # 设置表格行高和高度为显示10行
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setMinimumHeight(32 + 40 * 10)

        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, 1)

        # ===== 底部操作栏 =====
        bottom_bar = QWidget(self)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        self.add_btn = PrimaryPushButton("添加单词", self)
        self.add_btn.clicked.connect(self._add_word)
        bottom_layout.addWidget(self.add_btn)

        self.del_btn = PushButton("删除选中单词", self)
        self.del_btn.clicked.connect(self._delete_word)
        bottom_layout.addWidget(self.del_btn)

        self.save_btn = PushButton("保存修改", self)
        self.save_btn.clicked.connect(self._save_changes)
        bottom_layout.addWidget(self.save_btn)

        bottom_layout.addStretch()
        layout.addWidget(bottom_bar)

    # ============ 数据加载 ============

    def _load_data(self):
        self._all_words = self.service.list_words()
        self._displayed_words = self._all_words.copy()
        self._load_categories()
        self._display_words()

    def _load_categories(self):
        self.category_combo.blockSignals(True)
        current_id = self.category_combo.currentData()
        self.category_combo.clear()
        self.category_combo.addItem("全部分类", userData=None)
        categories = self.service.list_categories()
        for cat in categories:
            self.category_combo.addItem(cat["name"], userData=cat["id"])
        if current_id is not None:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == current_id:
                    self.category_combo.setCurrentIndex(i)
                    break
        self.category_combo.blockSignals(False)

    def _apply_filters(self):
        words = self._all_words
        if self._current_category_id is not None:
            words = [w for w in words if w.get("category_id") == self._current_category_id]
        if self._search_text:
            kw = self._search_text.lower()
            words = [
                w for w in words
                if kw in w.get("english", "").lower()
                or kw in w.get("chinese", "").lower()
                or kw in w.get("pronunciation", "").lower()
            ]
        self._displayed_words = words

    def _display_words(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row, word in enumerate(self._displayed_words):
            self.table.insertRow(row)

            en = word.get("english", "")
            cn = word.get("chinese", "")
            pron = word.get("pronunciation", "")
            cat = word.get("category_name", "") or ""

            en_item = QTableWidgetItem(en if self._show_english else "******")
            cn_item = QTableWidgetItem(cn if self._show_chinese else "******")
            pron_item = QTableWidgetItem(pron if self._show_pronunciation else "******")
            cat_item = QTableWidgetItem(cat)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)

            if not self._show_english:
                en_item.setForeground(QColor("#999999"))
            if not self._show_chinese:
                cn_item.setForeground(QColor("#999999"))
            if not self._show_pronunciation:
                pron_item.setForeground(QColor("#999999"))

            en_item.setToolTip(en)
            cn_item.setToolTip(cn)
            pron_item.setToolTip(pron)
            cat_item.setToolTip(cat)

            en_item.setData(Qt.UserRole, word["id"])

            self.table.setItem(row, COL_ENGLISH, en_item)
            self.table.setItem(row, COL_CHINESE, cn_item)
            self.table.setItem(row, COL_PRONUNCIATION, pron_item)
            self.table.setItem(row, COL_CATEGORY, cat_item)

        self.table.blockSignals(False)
        self._update_stats()

    def _update_stats(self):
        total = len(self._all_words)
        displayed = len(self._displayed_words)
        self.total_label.setText(f"总单词数: {total}")
        self.displayed_label.setText(f"显示单词数: {displayed}")
        if total > 0:
            self.progress_bar.setValue(int(displayed / total * 100))
        else:
            self.progress_bar.setValue(0)
        self.filter_progress_label.setText(f"过滤进度: {displayed}/{total}")

    # ============ 列显隐 ============

    def _toggle_english(self):
        self._show_english = not self.hide_en_btn.isChecked()
        self._display_words()

    def _toggle_chinese(self):
        self._show_chinese = not self.hide_cn_btn.isChecked()
        self._display_words()

    def _toggle_pronunciation(self):
        self._show_pronunciation = not self.hide_pron_btn.isChecked()
        self._display_words()

    # ============ 分类筛选 ============

    def _on_category_changed(self, index: int):
        self._current_category_id = self.category_combo.currentData()
        self._apply_filters()
        self._display_words()

    # ============ 搜索 ============

    def _on_search(self, text: str):
        self._search_text = text.strip()
        self._apply_filters()
        self._display_words()

    # ============ 右键菜单 ============

    def _show_context_menu(self, position):
        menu = RoundMenu(parent=self)
        delete_action = Action(FIF.DELETE, "删除选中行")
        delete_action.triggered.connect(self._delete_selected_rows)
        menu.addAction(delete_action)
        menu.exec(self.table.viewport().mapToGlobal(position), ani=True)

    def _delete_selected_rows(self):
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        if not rows:
            return
        ids = []
        for row in rows:
            en_item = self.table.item(row, COL_ENGLISH)
            if en_item is not None:
                word_id = en_item.data(Qt.UserRole)
                if word_id is not None:
                    ids.append(word_id)
        if not ids:
            return
        box = MessageBox("确认删除", f"确定要删除选中的 {len(ids)} 个单词吗？", self)
        if not box.exec():
            return
        success = 0
        for word_id in ids:
            if self.service.delete_word(word_id):
                success += 1
        self._all_words = self.service.list_words()
        self._apply_filters()
        self._display_words()
        InfoBar.success(
            title="删除成功", content=f"已删除 {success} 个单词",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self,
        )

    # ============ 内联编辑 ============

    def _on_item_changed(self, item: QTableWidgetItem):
        if item.column() == COL_CATEGORY:
            return

        self.table.blockSignals(True)
        word_id = self.table.item(item.row(), COL_ENGLISH).data(Qt.UserRole)
        if word_id is None:
            self.table.blockSignals(False)
            return

        col_map = {
            COL_ENGLISH: "english",
            COL_CHINESE: "chinese",
            COL_PRONUNCIATION: "pronunciation",
        }
        field = col_map.get(item.column())
        if field is None:
            self.table.blockSignals(False)
            return

        new_text = item.text().strip()
        if not new_text or new_text == "******":
            self._display_words()
            self.table.blockSignals(False)
            return

        try:
            self.service.update_word(word_id, **{field: new_text})
            for w in self._all_words:
                if w["id"] == word_id:
                    w[field] = new_text
                    break
            self._apply_filters()
            self._display_words()
            InfoBar.success(
                title="修改成功", content="已更新",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=1500, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="修改失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            self._display_words()
        finally:
            self.table.blockSignals(False)

    # ============ 分类操作（右键菜单或对话框） ============

    def _add_category(self):
        dialog = CategoryDialog(parent=self)
        if not dialog.exec():
            return
        name = dialog.get_name()
        try:
            self.service.add_category(name)
            self._load_categories()
            InfoBar.success(
                title="添加成功", content=f"分类 '{name}' 已添加",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="添加失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    def _edit_category(self):
        cat_id = self.category_combo.currentData()
        if cat_id is None:
            InfoBar.warning(
                title="提示", content="请先选择一个分类",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return
        current_name = self.category_combo.currentText()
        dialog = CategoryDialog(current_name, self)
        if not dialog.exec():
            return
        name = dialog.get_name()
        try:
            self.service.update_category(cat_id, name)
            self._load_categories()
            InfoBar.success(
                title="修改成功", content=f"分类已重命名为 '{name}'",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="修改失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    def _delete_category(self):
        cat_id = self.category_combo.currentData()
        if cat_id is None:
            InfoBar.warning(
                title="提示", content="请先选择一个分类",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return
        name = self.category_combo.currentText()
        box = MessageBox("确认删除", f"确定要删除分类 '{name}' 吗？\n属于该分类的单词将变为无分类。", self)
        if not box.exec():
            return
        try:
            self.service.delete_category(cat_id)
            self._all_words = self.service.list_words()
            self._load_categories()
            self._apply_filters()
            self._display_words()
            InfoBar.success(
                title="删除成功", content=f"分类 '{name}' 已删除",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="删除失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    # ============ 单词操作 ============

    def _add_word(self):
        dialog = WordEditDialog(self.service, parent=self)
        if not dialog.exec():
            return
        data = dialog.get_data()
        try:
            self.service.add_word(
                chinese=data["chinese"],
                english=data["english"],
                pronunciation=data["pronunciation"],
                category_id=data["category_id"],
            )
            self._all_words = self.service.list_words()
            self._apply_filters()
            self._display_words()
            InfoBar.success(
                title="添加成功", content=f"单词 '{data['english']}' 已添加",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="添加失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    def _get_selected_word_ids(self) -> List[int]:
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        ids = []
        for row in rows:
            en_item = self.table.item(row, COL_ENGLISH)
            if en_item is not None:
                word_id = en_item.data(Qt.UserRole)
                if word_id is not None:
                    ids.append(word_id)
        return ids

    def _delete_word(self):
        ids = self._get_selected_word_ids()
        if not ids:
            InfoBar.warning(
                title="提示", content="请先选择要删除的单词",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return
        box = MessageBox("确认删除", f"确定要删除选中的 {len(ids)} 个单词吗？", self)
        if not box.exec():
            return
        success = 0
        for word_id in ids:
            if self.service.delete_word(word_id):
                success += 1
        self._all_words = self.service.list_words()
        self._apply_filters()
        self._display_words()
        InfoBar.success(
            title="删除成功", content=f"已删除 {success} 个单词",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self,
        )

    def _save_changes(self):
        """保存修改（数据已实时保存到数据库，此处仅做提示）"""
        InfoBar.success(
            title="保存成功", content="所有修改已保存",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self,
        )

    # ============ 导入/导出 ============

    def _import_words(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入单词", "", "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return
        import json
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            words_data = data if isinstance(data, list) else data.get("words", [])
            if not words_data:
                InfoBar.warning(
                    title="导入失败", content="文件中没有找到单词数据",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=2000, parent=self,
                )
                return

            added = 0
            for w in words_data:
                en = (w.get("english") or "").strip()
                cn = (w.get("chinese") or "").strip()
                if en and cn:
                    pron = (w.get("pronunciation") or "").strip()
                    cat_name = (w.get("category") or "").strip()
                    cat_id = None
                    if cat_name:
                        cats = self.service.list_categories()
                        existing = [c for c in cats if c["name"] == cat_name]
                        if existing:
                            cat_id = existing[0]["id"]
                        else:
                            cat_id = self.service.add_category(cat_name)
                    self.service.add_word(cn, en, pron, cat_id)
                    added += 1

            self._all_words = self.service.list_words()
            self._load_categories()
            self._apply_filters()
            self._display_words()
            InfoBar.success(
                title="导入成功", content=f"成功导入 {added} 个单词",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="导入失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    def _export_words(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出单词", "vocabulary.json", "JSON 文件 (*.json)"
        )
        if not file_path:
            return
        import json
        try:
            cats = {c["id"]: c["name"] for c in self.service.list_categories()}
            words = []
            for w in self._all_words:
                words.append({
                    "english": w.get("english", ""),
                    "chinese": w.get("chinese", ""),
                    "pronunciation": w.get("pronunciation", ""),
                    "category": cats.get(w.get("category_id")) or "",
                })
            data = {
                "words": words,
                "categories": list(cats.values()),
                "total_count": len(words),
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            InfoBar.success(
                title="导出成功", content=f"已导出 {len(words)} 个单词",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="导出失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )


class VocabularyPage(TabPageInterface):
    """单词背诵标签页"""

    page_id = "vocabulary"
    page_name = "单词背诵"

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return VocabularyWidget(parent)