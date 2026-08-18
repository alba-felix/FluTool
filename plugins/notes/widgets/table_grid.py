"""迷你 Excel 表格编辑器 - 布局2"""

from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QDialog, QFileDialog,
    QHBoxLayout, QHeaderView, QInputDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    CaptionLabel, ComboBox, FluentIcon as FIF, InfoBar, InfoBarPosition,
    PushButton, TransparentToolButton, isDarkTheme, qconfig,
)

from ..services.note_service import NoteService
from ..services.table_service import (
    COLUMN_NAMES, MAX_COLUMNS, MAX_ROWS, TableService, coord_to_key,
    key_to_coord,
)

MIN_ROW_HEIGHT = 24
DEFAULT_COL_WIDTH = 100


class TableGrid(QWidget):
    """极简 Excel：固定 A1..Z999 的 26x999 网格，表头可拖拽调宽高"""

    def __init__(self, note_service: NoteService, parent=None):
        super().__init__(parent)
        self._table_service = TableService(note_service)
        self._current_id: Optional[int] = None
        self._current_cells: Dict[str, str] = {}
        self._loading = False

        self._setup_ui()
        self._refresh_table_list()
        qconfig.themeChangedFinished.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        """主题切换后刷新样式"""
        self._apply_grid_style()

    # ───────────────────────── 界面构建 ─────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(8)

        # 顶部工具条
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.table_combo = ComboBox()
        self.table_combo.setMinimumWidth(160)
        self.table_combo.setToolTip("选择表格")
        self.table_combo.currentIndexChanged.connect(self._on_table_selected)
        toolbar.addWidget(self.table_combo)

        self.new_btn = PushButton("新建表格")
        self.new_btn.setIcon(FIF.ADD)
        self.new_btn.setFixedHeight(32)
        self.new_btn.clicked.connect(self._create_table)
        toolbar.addWidget(self.new_btn)

        self.rename_btn = PushButton("重命名")
        self.rename_btn.setIcon(FIF.EDIT)
        self.rename_btn.setFixedHeight(32)
        self.rename_btn.clicked.connect(self._rename_table)
        toolbar.addWidget(self.rename_btn)

        self.delete_btn = PushButton("删除")
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._delete_table)
        toolbar.addWidget(self.delete_btn)

        toolbar.addStretch()

        self.save_btn = PushButton("保存")
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.setFixedHeight(32)
        self.save_btn.clicked.connect(self._save_table)
        toolbar.addWidget(self.save_btn)

        self.md_btn = TransparentToolButton(FIF.DOWNLOAD)
        self.md_btn.setToolTip("导出为 Markdown 表格")
        self.md_btn.clicked.connect(self._export_markdown)
        toolbar.addWidget(self.md_btn)

        self.copy_btn = TransparentToolButton(FIF.COPY)
        self.copy_btn.setToolTip("复制 Markdown 表格")
        self.copy_btn.clicked.connect(self._copy_markdown)
        toolbar.addWidget(self.copy_btn)

        root.addLayout(toolbar)

        # 网格
        self.grid = QTableWidget(0, 0)
        self._build_grid()
        root.addWidget(self.grid, 1)

        self.status_label = CaptionLabel("就绪")
        root.addWidget(self.status_label)

    def _build_grid(self):
        self.grid.setRowCount(MAX_ROWS)
        self.grid.setColumnCount(MAX_COLUMNS)

        for col, letter in enumerate(COLUMN_NAMES):
            self.grid.setHorizontalHeaderItem(col, QTableWidgetItem(letter))
        for row in range(MAX_ROWS):
            self.grid.setVerticalHeaderItem(row, QTableWidgetItem(str(row + 1)))

        header = self.grid.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setDefaultSectionSize(DEFAULT_COL_WIDTH)
        header.setSectionsClickable(False)

        vheader = self.grid.verticalHeader()
        vheader.setSectionResizeMode(QHeaderView.Interactive)
        vheader.setDefaultSectionSize(MIN_ROW_HEIGHT)
        vheader.setSectionsClickable(False)

        self.grid.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked
        )
        self.grid.setSelectionMode(QAbstractItemView.SingleSelection)
        self.grid.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.grid.itemChanged.connect(self._on_item_changed)
        self._apply_grid_style()

    def _apply_grid_style(self):
        """应用主题感知的网格样式（颜色随亮/暗主题反转）"""
        dark = isDarkTheme()
        text = "#e0e0e0" if dark else "#333333"
        bg = "#242424" if dark else "#ffffff"
        header_bg = "#2f2f2f" if dark else "#ececec"
        border = "rgba(255, 255, 255, 0.25)" if dark else "rgba(128, 128, 128, 0.3)"
        gridline = "rgba(255, 255, 255, 0.12)" if dark else "rgba(128, 128, 128, 0.2)"
        header_line = "rgba(255, 255, 255, 0.2)" if dark else "rgba(128, 128, 128, 0.25)"
        header_hover = "rgba(255, 255, 255, 0.15)" if dark else "rgba(128, 128, 128, 0.15)"
        selection = "rgba(0, 120, 212, 0.3)" if dark else "rgba(0, 120, 212, 0.15)"
        editor_bg = "#2b2b2b" if dark else "#ffffff"
        self.grid.setStyleSheet(
            f"""
            QTableWidget {{
                background: {bg};
                border: 1px solid {border};
                gridline-color: {gridline};
                selection-background-color: {selection};
                selection-color: {text};
            }}
            QTableWidget::item {{
                padding: 0px 4px;
                color: {text};
            }}
            QTableWidget QLineEdit {{
                background: {editor_bg};
                color: {text};
                border: 1px solid {border};
                selection-background-color: {selection};
            }}
            """
        )
        header_qss = (
            f"QHeaderView::section {{"
            f" background: {header_bg};"
            f" border: none;"
            f" border-right: 1px solid {header_line};"
            f" border-bottom: 1px solid {header_line};"
            f" padding: 2px 4px;"
            f" color: {text};"
            f" }}"
            f"QHeaderView::section:hover {{ background: {header_hover}; }}"
        )
        self.grid.horizontalHeader().setStyleSheet(header_qss)
        self.grid.verticalHeader().setStyleSheet(header_qss)

    # ───────────────────────────── 数据加载 ─────────────────────────────

    def _refresh_table_list(self):
        """从服务刷新表格下拉列表"""
        tables = self._table_service.list_tables()
        self._loading = True
        try:
            self.table_combo.blockSignals(True)
            self.table_combo.clear()
            for note in tables:
                self.table_combo.addItem(note.title or "表格", note.id)
            if tables:
                self.table_combo.setCurrentIndex(0)
        finally:
            self.table_combo.blockSignals(False)
            self._loading = False

        if tables:
            self._load_current()
        else:
            self.grid.clearContents()
            self._current_id = None
            self._current_cells = {}
            self.status_label.setText("没有表格，点击「新建表格」创建一个")

    def _load_current(self):
        """加载当前选中表格到网格"""
        table_id = self.table_combo.currentData()
        self._current_id = table_id
        note = self._table_service.get_table(table_id)
        if note is None:
            self.status_label.setText("表格不存在")
            return
        self._current_cells = self._table_service.load_cells(note)

        self._loading = True
        try:
            self.grid.blockSignals(True)
            self.grid.clearContents()
            for key, value in self._current_cells.items():
                coord = key_to_coord(key)
                if coord is None:
                    continue
                col, row = coord
                item = QTableWidgetItem(value)
                self.grid.setItem(row, col, item)
        finally:
            self.grid.blockSignals(False)
            self._loading = False

        total = len(self._current_cells)
        self.status_label.setText(f"表格「{note.title}」 · 已填写 {total} 个单元格")

    # ───────────────────────────── 交互动作 ─────────────────────────────

    def _on_item_changed(self, item):
        if self._loading:
            return
        key = coord_to_key(item.column(), item.row())
        value = item.text()
        if value:
            self._current_cells[key] = value
        else:
            self._current_cells.pop(key, None)
        self.status_label.setText(f"已修改 {key}（未保存）")

    def _on_table_selected(self, index):
        if self._loading or index < 0:
            return
        self._load_current()

    def _save_table(self):
        """手动保存当前网格"""
        if self._current_id is None:
            self.status_label.setText("请先创建表格")
            return
        size = len(self._current_cells)
        if self._table_service.save_cells(self._current_id, self._current_cells):
            note = self._table_service.get_table(self._current_id)
            title = note.title if note else "表格"
            self._update_combo_title(title)
            self.status_label.setText(f"已保存「{title}」（{size} 个单元格）")
        else:
            self.status_label.setText("保存失败")

    def _update_combo_title(self, title: str):
        idx = self.table_combo.currentIndex()
        if idx >= 0:
            self.table_combo.setItemText(idx, title or "表格")

    def _create_table(self):
        note_id = self._table_service.create_table()
        if note_id is None:
            self.status_label.setText("新建失败")
            return
        self._refresh_table_list()
        target_idx = -1
        for idx in range(self.table_combo.count()):
            if self.table_combo.itemData(idx) == note_id:
                target_idx = idx
                break
        if target_idx >= 0:
            self.table_combo.blockSignals(True)
            self.table_combo.setCurrentIndex(target_idx)
            self.table_combo.blockSignals(False)
        self._load_current()
        self.status_label.setText("已新建表格，编辑后点击「保存」")

    def _rename_table(self):
        if self._current_id is None:
            return
        new_name, ok = QInputDialog.getText(
            self, "重命名表格", "新名称：",
            text=self.table_combo.currentText(),
        )
        if not ok:
            return
        if self._table_service.rename_table(self._current_id, new_name):
            self._update_combo_title(new_name)
            self.status_label.setText(f"已重命名为「{new_name}」")

    def _delete_table(self):
        if self._current_id is None:
            return
        result = QMessageBox.question(
            self, "删除表格", "确定删除当前表格吗？此操作不可撤销。"
        )
        if result != QMessageBox.Yes:
            return
        deleted_id = self._current_id
        if self._table_service.delete_table(deleted_id):
            self._current_id = None
            self.status_label.setText("已删除")
            self._refresh_table_list()

    # ───────────────────────────── 导出 ─────────────────────────────

    def _notify_no_table(self) -> None:
        """提示先选择表格"""
        InfoBar.warning(
            title="提示",
            content="请先选择表格",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def _export_markdown(self):
        if self._current_id is None:
            self._notify_no_table()
            return
        md = self._table_service.to_markdown(self._current_cells)
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Markdown", "table.md", "Markdown 文件 (*.md)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        self.status_label.setText(f"已导出 {path}")

    def _copy_markdown(self):
        if self._current_id is None:
            self._notify_no_table()
            return
        md = self._table_service.to_markdown(self._current_cells)
        QApplication.clipboard().setText(md)
        self.status_label.setText("已复制 Markdown 表格到剪贴板")