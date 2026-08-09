"""备注列表 - 搜索、预览、编辑、删除、导出"""
import os
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)
from qfluentwidgets import FluentIcon as FIF, MessageBox, SearchLineEdit, isDarkTheme

from .service import CommentService


def _item_style(dark: bool) -> str:
    bg = "#2d2d2d" if dark else "#ffffff"
    border = "#3d3d3d" if dark else "#e0e0e0"
    fg = "#ffffff" if dark else "#1a1a1a"
    sub = "#b0b0b0" if dark else "#666666"
    accent = "#4da6ff" if dark else "#0078d4"
    danger = "#ff6b7a" if dark else "#ff4757"
    return f"""
        QFrame#itemCard {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 8px;
        }}
        QLabel#title {{ color: {fg}; font-size: 14px; font-weight: bold; }}
        QLabel#path  {{ color: {sub}; font-size: 11px; }}
        QLabel#note  {{ color: {fg}; font-size: 12px; }}
        QLabel#time  {{ color: {sub}; font-size: 10px; }}
        QPushButton#goBtn   {{ color: {accent}; background: transparent; border: none; font-size: 12px; }}
        QPushButton#delBtn  {{ color: {danger}; background: transparent; border: none; font-size: 12px; }}
        QPushButton#preBtn  {{ color: {accent}; background: transparent; border: none; font-size: 12px; }}
    """


def _list_style(dark: bool) -> str:
    """列表容器主题样式：背景透明 + 原生按钮主题化"""
    border = "#3d3d3d" if dark else "#d0d0d0"
    fg = "#ffffff" if dark else "#1a1a1a"
    sub = "#b0b0b0" if dark else "#666666"
    btn_bg = "#383838" if dark else "#f0f0f0"
    btn_hover = "#404040" if dark else "#e4e4e4"
    return f"""
        CommentListWidget {{ background: transparent; }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QPushButton {{
            background: {btn_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 6px 14px;
        }}
        QPushButton:hover {{ background: {btn_hover}; }}
        QPushButton[danger="true"] {{
            color: #ff4757;
            background: transparent;
            border: none;
        }}
        QPushButton[danger="true"]:hover {{
            background: rgba(255, 71, 87, 0.1);
        }}
    """


def _list_theme() -> str:
    from qfluentwidgets import isDarkTheme
    return _list_style(isDarkTheme())


class _CommentCard(QFrame):
    preview_clicked = pyqtSignal(dict)
    delete_clicked = pyqtSignal(str)
    navigate_clicked = pyqtSignal(str)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("itemCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        top = QHBoxLayout()
        title = QLabel(data.get("path", "").split("\\")[-1] or "未命名", self)
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()

        pre_btn = QPushButton("预览", self)
        pre_btn.setObjectName("preBtn")
        pre_btn.clicked.connect(lambda: self.preview_clicked.emit(data))
        top.addWidget(pre_btn)

        del_btn = QPushButton("删除", self)
        del_btn.setObjectName("delBtn")
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(data["path"]))
        top.addWidget(del_btn)

        go_btn = QPushButton("→", self)
        go_btn.setObjectName("goBtn")
        go_btn.setFixedSize(24, 24)
        go_btn.clicked.connect(lambda: self.navigate_clicked.emit(data["path"]))
        top.addWidget(go_btn)

        layout.addLayout(top)

        path_lbl = QLabel(data.get("path", ""), self)
        path_lbl.setObjectName("path")
        path_lbl.setWordWrap(True)
        layout.addWidget(path_lbl)

        note = data.get("text", "")
        if note:
            note_lbl = QLabel(note[:200] + ("…" if len(note) > 200 else ""), self)
            note_lbl.setObjectName("note")
            note_lbl.setWordWrap(True)
            layout.addWidget(note_lbl)

        ts = data.get("updated_at", "")
        if ts:
            t = QLabel(ts, self)
            t.setObjectName("time")
            layout.addWidget(t)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(_item_style(isDarkTheme()))


class CommentListWidget(QWidget):
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._service = CommentService()
        self._build_ui()
        self._load()
        self._refresh_theme()
        from qfluentwidgets import qconfig
        qconfig.themeChangedFinished.connect(self._refresh_theme)

    def _refresh_theme(self) -> None:
        """主题切换后刷新容器与卡片样式"""
        self.setStyleSheet(_list_theme())
        for i in range(self._vbox.count()):
            w = self._vbox.itemAt(i).widget()
            if isinstance(w, _CommentCard):
                w._apply_style()
        if self._empty_label is not None:
            sub = "#b0b0b0" if isDarkTheme() else "#666666"
            self._empty_label.setStyleSheet(f"color: {sub}; padding: 40px;")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        top = QHBoxLayout()
        self._search = SearchLineEdit()
        self._search.setPlaceholderText("搜索备注（文件夹名称或内容）")
        self._search.setFixedWidth(260)
        self._search.searchSignal.connect(self._on_search)
        self._search.clearSignal.connect(self._load)
        top.addWidget(self._search)
        top.addStretch()

        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export)
        top.addWidget(export_btn)

        clear_btn = QPushButton("一键删除全部")
        clear_btn.setProperty("danger", True)
        clear_btn.clicked.connect(self._clear_all)
        top.addWidget(clear_btn)

        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._container = QWidget()
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(8)
        self._vbox.addStretch()
        scroll.setWidget(self._container)
        layout.addWidget(scroll, 1)
        self._empty_label: Optional[QLabel] = None

    def _load(self, items: List[dict] = None) -> None:
        items = items or self._service.all()
        # 清除旧卡片（保留最后的 stretch）
        while self._vbox.count() > 1:
            w = self._vbox.takeAt(0).widget()
            if w:
                w.deleteLater()

        for d in items:
            card = _CommentCard(d)
            card.preview_clicked.connect(self._preview)
            card.delete_clicked.connect(self._delete)
            card.navigate_clicked.connect(self._navigate)
            self._vbox.insertWidget(self._vbox.count() - 1, card)

        if not items:
            lbl = QLabel("暂无备注")
            sub = "#b0b0b0" if isDarkTheme() else "#666666"
            lbl.setStyleSheet(f"color: {sub}; padding: 40px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._vbox.insertWidget(self._vbox.count() - 1, lbl)
            self._empty_label = lbl
        else:
            self._empty_label = None

    def _on_search(self) -> None:
        kw = self._search.text().strip()
        if kw:
            self._load(self._service.search(kw))

    def _preview(self, data: dict) -> None:
        from PyQt5.QtWidgets import QDialog, QTextEdit
        from qfluentwidgets import isDarkTheme, qconfig

        def _preview_style(dark: bool) -> str:
            bg = "#202020" if dark else "#ffffff"
            fg = "#ffffff" if dark else "#1a1a1a"
            input_bg = "#2d2d2d" if dark else "#f5f5f5"
            border = "#3d3d3d" if dark else "#d0d0d0"
            return f"""
                QDialog {{ background: {bg}; }}
                QTextEdit {{
                    background: {input_bg};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """

        dlg = QDialog(self)
        dlg.setWindowTitle(data.get("path", "").split("\\")[-1])
        dlg.resize(400, 300)
        dlg.setStyleSheet(_preview_style(isDarkTheme()))
        qconfig.themeChangedFinished.connect(lambda: dlg.setStyleSheet(_preview_style(isDarkTheme())))
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        te = QTextEdit()
        te.setPlainText(data.get("text", ""))
        te.setReadOnly(True)
        lay.addWidget(te)
        dlg.exec()

    def _delete(self, path: str) -> None:
        confirm = MessageBox("确认删除", f"确定要删除该备注吗？\n{path}", self)
        if confirm.exec():
            self._service.delete(path)
            self._load()

    def _clear_all(self) -> None:
        confirm = MessageBox("确认删除", "确定要删除所有备注吗？此操作不可撤销！", self)
        if confirm.exec():
            self._service.clear()
            self._load()

    def _navigate(self, path: str) -> None:
        if os.path.isdir(path):
            os.startfile(path)

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "导出备注", "comments.txt", "文本文件 (*.txt)")
        if not path:
            return
        items = self._service.all()
        with open(path, "w", encoding="utf-8") as f:
            for d in items:
                f.write(f"【{d.get('path', '')}】\n{d.get('text', '')}\n\n")
        from qfluentwidgets import InfoBar
        InfoBar.success("导出成功", f"已导出 {len(items)} 条备注", parent=self)
