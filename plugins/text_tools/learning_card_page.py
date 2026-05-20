from typing import List, Dict, Any, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QAbstractItemView,
    QTableWidgetItem, QFileDialog, QTextEdit,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from qfluentwidgets import (
    FluentIcon as FIF, PushButton, ComboBox, LineEdit, InfoBar, InfoBarPosition,
    MessageBoxBase, SubtitleLabel, MessageBox, TableWidget, BodyLabel,
    PrimaryPushButton, ProgressBar, RoundMenu, Action,
)

from .page_interface import TabPageInterface
from .learning_card_service import LearningCardService


COL_TITLE = 0
COL_CONTENT = 1
COL_NOTE = 2
COL_CATEGORY = 3


class CardEditDialog(MessageBoxBase):
    """添加/编辑卡片对话框"""

    def __init__(self, service: LearningCardService, card_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.card_data = card_data
        self._setup_ui()

    def _setup_ui(self):
        self.titleLabel = SubtitleLabel("添加卡片" if self.card_data is None else "编辑卡片", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.viewLayout.addWidget(BodyLabel("标题:", self))
        self.title_input = LineEdit(self)
        self.title_input.setPlaceholderText("输入标题...")
        if self.card_data:
            self.title_input.setText(self.card_data.get("title", ""))
        self.viewLayout.addWidget(self.title_input)

        self.viewLayout.addWidget(BodyLabel("内容:", self))
        self.content_input = QTextEdit(self)
        self.content_input.setPlaceholderText("输入内容...")
        self.content_input.setMaximumHeight(120)
        if self.card_data:
            self.content_input.setPlainText(self.card_data.get("content", ""))
        self.viewLayout.addWidget(self.content_input)

        self.viewLayout.addWidget(BodyLabel("备注:", self))
        self.note_input = LineEdit(self)
        self.note_input.setPlaceholderText("输入备注（可选）...")
        if self.card_data:
            self.note_input.setText(self.card_data.get("note", ""))
        self.viewLayout.addWidget(self.note_input)

        self.viewLayout.addWidget(BodyLabel("所属分类:", self))
        self.category_combo = ComboBox(self)
        categories = self.service.list_categories()
        self.category_combo.addItem("（无分类）", userData=None)
        current_category_id = self.card_data.get("category_id") if self.card_data else None
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
        self.widget.setMinimumWidth(450)

    def get_data(self) -> Dict[str, Any]:
        return {
            "title": self.title_input.text().strip(),
            "content": self.content_input.toPlainText().strip(),
            "note": self.note_input.text().strip(),
            "category_id": self.category_combo.currentData(),
        }

    def validate(self) -> bool:
        if not self.title_input.text().strip():
            InfoBar.warning(
                title="无法保存", content="标题不能为空",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return False
        if not self.content_input.toPlainText().strip():
            InfoBar.warning(
                title="无法保存", content="内容不能为空",
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


class LearningCardWidget(QWidget):
    """知识卡片管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.service = LearningCardService()
        self._show_title = True
        self._show_content = True
        self._displayed_cards: List[Dict[str, Any]] = []
        self._all_cards: List[Dict[str, Any]] = []
        self._current_category_id: Optional[int] = None
        self._search_text = ""
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ===== 顶部工具栏 =====
        top_bar = QWidget(self)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索卡片...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self._on_search)
        top_layout.addWidget(self.search_input)

        self.category_combo = ComboBox(self)
        self.category_combo.setMinimumWidth(100)
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        top_layout.addWidget(self.category_combo)

        self.add_cat_btn = PushButton("添加分类", self)
        self.add_cat_btn.clicked.connect(self._add_category)
        top_layout.addWidget(self.add_cat_btn)

        self.edit_cat_btn = PushButton("编辑分类", self)
        self.edit_cat_btn.clicked.connect(self._edit_category)
        top_layout.addWidget(self.edit_cat_btn)

        self.del_cat_btn = PushButton("删除分类", self)
        self.del_cat_btn.clicked.connect(self._delete_category)
        top_layout.addWidget(self.del_cat_btn)

        top_layout.addSpacing(16)

        self.add_btn = PrimaryPushButton("添加卡片", self)
        self.add_btn.clicked.connect(self._add_card)
        top_layout.addWidget(self.add_btn)

        self.del_btn = PushButton("删除选中", self)
        self.del_btn.clicked.connect(self._delete_card)
        top_layout.addWidget(self.del_btn)

        top_layout.addSpacing(16)

        self.hide_title_btn = PushButton("隐藏标题")
        self.hide_title_btn.setCheckable(True)
        self.hide_title_btn.clicked.connect(self._toggle_title)
        top_layout.addWidget(self.hide_title_btn)

        self.hide_content_btn = PushButton("隐藏内容")
        self.hide_content_btn.setCheckable(True)
        self.hide_content_btn.clicked.connect(self._toggle_content)
        top_layout.addWidget(self.hide_content_btn)

        self.import_btn = PushButton("导入")
        self.import_btn.clicked.connect(self._import_cards)
        top_layout.addWidget(self.import_btn)

        self.export_btn = PushButton("导出")
        self.export_btn.clicked.connect(self._export_cards)
        top_layout.addWidget(self.export_btn)

        top_layout.addStretch()
        layout.addWidget(top_bar)

        # ===== 统计信息栏 =====
        stats_bar = QWidget(self)
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(8)

        self.total_label = BodyLabel("总卡片数: 0", self)
        stats_layout.addWidget(self.total_label)

        self.displayed_label = BodyLabel("显示卡片数: 0", self)
        stats_layout.addWidget(self.displayed_label)

        self.progress_bar = ProgressBar(self)
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMinimumHeight(8)
        stats_layout.addWidget(self.progress_bar)

        self.filter_progress_label = BodyLabel("", self)
        stats_layout.addWidget(self.filter_progress_label)

        stats_layout.addStretch()
        layout.addWidget(stats_bar)

        # ===== 卡片表格 =====
        self.table = TableWidget(self)
        self.table.setBorderRadius(8)
        self.table.setBorderVisible(True)
        self.table.setWordWrap(True)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["标题", "内容", "备注", "分类"])
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.verticalHeader().setMinimumSectionSize(40)

        self.table.horizontalHeader().setSectionResizeMode(COL_TITLE, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(COL_CONTENT, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_NOTE, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(COL_CATEGORY, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(COL_TITLE, 150)
        self.table.setColumnWidth(COL_NOTE, 150)

        table_font = QFont()
        table_font.setPointSize(12)
        self.table.setFont(table_font)

        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)

        self.table.setMinimumHeight(32 + 40 * 10)

        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.table, 1)

    # ============ 数据加载 ============

    def _load_data(self):
        self._all_cards = self.service.list_cards()
        self._displayed_cards = self._all_cards.copy()
        self._load_categories()
        self._display_cards()

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
        cards = self._all_cards
        if self._current_category_id is not None:
            cards = [c for c in cards if c.get("category_id") == self._current_category_id]
        if self._search_text:
            kw = self._search_text.lower()
            cards = [
                c for c in cards
                if kw in c.get("title", "").lower()
                or kw in c.get("content", "").lower()
                or kw in c.get("note", "").lower()
            ]
        self._displayed_cards = cards

    def _display_cards(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row, card in enumerate(self._displayed_cards):
            self.table.insertRow(row)

            title = card.get("title", "")
            content = card.get("content", "")
            note = card.get("note", "")
            cat = card.get("category_name", "") or ""

            title_item = QTableWidgetItem(title if self._show_title else "******")
            content_item = QTableWidgetItem(content if self._show_content else "******")
            note_item = QTableWidgetItem(note)
            cat_item = QTableWidgetItem(cat)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsEditable)

            if not self._show_title:
                title_item.setForeground(QColor("#999999"))
            if not self._show_content:
                content_item.setForeground(QColor("#999999"))

            title_item.setToolTip(title)
            content_item.setToolTip(content)
            note_item.setToolTip(note)
            cat_item.setToolTip(cat)

            title_item.setData(Qt.UserRole, card["id"])

            self.table.setItem(row, COL_TITLE, title_item)
            self.table.setItem(row, COL_CONTENT, content_item)
            self.table.setItem(row, COL_NOTE, note_item)
            self.table.setItem(row, COL_CATEGORY, cat_item)

        self.table.blockSignals(False)
        self._update_stats()

    def _update_stats(self):
        total = len(self._all_cards)
        displayed = len(self._displayed_cards)
        self.total_label.setText(f"总卡片数: {total}")
        self.displayed_label.setText(f"显示卡片数: {displayed}")
        if total > 0:
            self.progress_bar.setValue(int(displayed / total * 100))
        else:
            self.progress_bar.setValue(0)
        self.filter_progress_label.setText(f"过滤进度: {displayed}/{total}")

    # ============ 列显隐 ============

    def _toggle_title(self):
        self._show_title = not self.hide_title_btn.isChecked()
        self._display_cards()

    def _toggle_content(self):
        self._show_content = not self.hide_content_btn.isChecked()
        self._display_cards()

    # ============ 分类筛选 ============

    def _on_category_changed(self, index: int):
        self._current_category_id = self.category_combo.currentData()
        self._apply_filters()
        self._display_cards()

    # ============ 分类管理 ============

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
            self._all_cards = self.service.list_cards()
            self._apply_filters()
            self._display_cards()
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
        box = MessageBox("确认删除", f"确定要删除分类 '{name}' 吗？\n属于该分类的卡片将变为无分类。", self)
        if not box.exec():
            return
        try:
            self.service.delete_category(cat_id)
            self._all_cards = self.service.list_cards()
            self._load_categories()
            self._apply_filters()
            self._display_cards()
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

    # ============ 搜索 ============

    def _on_search(self, text: str):
        self._search_text = text.strip()
        self._apply_filters()
        self._display_cards()

    # ============ 内联编辑 ============

    def _on_item_changed(self, item: QTableWidgetItem):
        if item.column() == COL_CATEGORY:
            return

        self.table.blockSignals(True)
        card_id = self.table.item(item.row(), COL_TITLE).data(Qt.UserRole)
        if card_id is None:
            self.table.blockSignals(False)
            return

        col_map = {
            COL_TITLE: "title",
            COL_CONTENT: "content",
            COL_NOTE: "note",
        }
        field = col_map.get(item.column())
        if field is None:
            self.table.blockSignals(False)
            return

        new_text = item.text().strip()
        if not new_text or new_text == "******":
            self._display_cards()
            self.table.blockSignals(False)
            return

        try:
            self.service.update_card(card_id, **{field: new_text})
            for c in self._all_cards:
                if c["id"] == card_id:
                    c[field] = new_text
                    break
            self._apply_filters()
            self._display_cards()
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
            self._display_cards()
        finally:
            self.table.blockSignals(False)

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
            title_item = self.table.item(row, COL_TITLE)
            if title_item is not None:
                card_id = title_item.data(Qt.UserRole)
                if card_id is not None:
                    ids.append(card_id)
        if not ids:
            return
        box = MessageBox("确认删除", f"确定要删除选中的 {len(ids)} 个卡片吗？", self)
        if not box.exec():
            return
        success = 0
        for card_id in ids:
            if self.service.delete_card(card_id):
                success += 1
        self._all_cards = self.service.list_cards()
        self._apply_filters()
        self._display_cards()
        InfoBar.success(
            title="删除成功", content=f"已删除 {success} 个卡片",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self,
        )

    # ============ 卡片操作 ============

    def _add_card(self):
        dialog = CardEditDialog(self.service, parent=self)
        if not dialog.exec():
            return
        data = dialog.get_data()
        try:
            self.service.add_card(
                title=data["title"],
                content=data["content"],
                note=data["note"],
                category_id=data["category_id"],
            )
            self._all_cards = self.service.list_cards()
            self._apply_filters()
            self._display_cards()
            InfoBar.success(
                title="添加成功", content=f"卡片 '{data['title']}' 已添加",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="添加失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    def _get_selected_card_ids(self) -> List[int]:
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        ids = []
        for row in rows:
            title_item = self.table.item(row, COL_TITLE)
            if title_item is not None:
                card_id = title_item.data(Qt.UserRole)
                if card_id is not None:
                    ids.append(card_id)
        return ids

    def _delete_card(self):
        ids = self._get_selected_card_ids()
        if not ids:
            InfoBar.warning(
                title="提示", content="请先选择要删除的卡片",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
            return
        box = MessageBox("确认删除", f"确定要删除选中的 {len(ids)} 个卡片吗？", self)
        if not box.exec():
            return
        success = 0
        for card_id in ids:
            if self.service.delete_card(card_id):
                success += 1
        self._all_cards = self.service.list_cards()
        self._apply_filters()
        self._display_cards()
        InfoBar.success(
            title="删除成功", content=f"已删除 {success} 个卡片",
            orient=Qt.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self,
        )

    # ============ 导入/导出 ============

    def _import_cards(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入卡片", "", "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if not file_path:
            return
        import json
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cards_data = data if isinstance(data, list) else data.get("cards", [])
            if not cards_data:
                InfoBar.warning(
                    title="导入失败", content="文件中没有找到卡片数据",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=2000, parent=self,
                )
                return

            added = 0
            for c in cards_data:
                title = (c.get("title") or "").strip()
                content = (c.get("content") or "").strip()
                if title and content:
                    note = (c.get("note") or "").strip()
                    cat_name = (c.get("category") or "").strip()
                    cat_id = None
                    if cat_name:
                        cats = self.service.list_categories()
                        existing = [cat for cat in cats if cat["name"] == cat_name]
                        if existing:
                            cat_id = existing[0]["id"]
                        else:
                            cat_id = self.service.add_category(cat_name)
                    self.service.add_card(title, content, note, cat_id)
                    added += 1

            self._all_cards = self.service.list_cards()
            self._load_categories()
            self._apply_filters()
            self._display_cards()
            InfoBar.success(
                title="导入成功", content=f"成功导入 {added} 个卡片",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="导入失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )

    def _export_cards(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出卡片", "learning_cards.json", "JSON 文件 (*.json)"
        )
        if not file_path:
            return
        import json
        try:
            cats = {c["id"]: c["name"] for c in self.service.list_categories()}
            cards = []
            for c in self._all_cards:
                cards.append({
                    "title": c.get("title", ""),
                    "content": c.get("content", ""),
                    "note": c.get("note", ""),
                    "category": cats.get(c.get("category_id")) or "",
                })
            data = {
                "cards": cards,
                "categories": list(cats.values()),
                "total_count": len(cards),
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            InfoBar.success(
                title="导出成功", content=f"已导出 {len(cards)} 个卡片",
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )
        except Exception as e:
            InfoBar.error(
                title="导出失败", content=str(e),
                orient=Qt.Horizontal, isClosable=True,
                position=InfoBarPosition.TOP, duration=2000, parent=self,
            )


class LearningCardPage(TabPageInterface):
    """知识卡片标签页"""

    page_id = "learning_card"
    page_name = "知识卡片"

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return LearningCardWidget(parent)