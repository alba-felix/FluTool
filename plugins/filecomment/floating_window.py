"""浮动备注窗口 - 快捷键唤出，居中显示"""
import os
from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)
from qfluentwidgets import isDarkTheme, qconfig

from .service import CommentService

# ── 样式 ──────────────────────────────────────────────────────────


def _style(dark: bool) -> str:
    bg = "#2d2d2d" if dark else "#ffffff"
    border = "#3d3d3d" if dark else "#e0e0e0"
    fg = "#ffffff" if dark else "#1a1a1a"
    sub = "#b0b0b0" if dark else "#666666"
    comment_bg = "#383838" if dark else "#f5f5f5"
    comment_border = "#4a4a4a" if dark else "#d0d0d0"
    accent = "#4da6ff" if dark else "#0078d4"
    accent_hover = "#70bfff" if dark else "#106ebe"
    return f"""
        QFrame#floatCard {{
            background: {bg};
            border: 1px solid {border};
            border-radius: 12px;
        }}
        QLabel#folderName {{
            color: {fg};
            font-size: 15px;
            font-weight: bold;
        }}
        QLabel#folderPath {{
            color: {sub};
            font-size: 12px;
        }}
        QLabel#updateTime {{
            color: {sub};
            font-size: 11px;
        }}
        QLabel#commentText {{
            color: {fg};
            font-size: 13px;
            background: {comment_bg};
            border: 1px solid {comment_border};
            border-radius: 6px;
            padding: 8px;
        }}
        QPushButton#editBtn {{
            background: {accent};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 14px;
            font-size: 12px;
        }}
        QPushButton#editBtn:hover {{
            background: {accent_hover};
        }}
        QPushButton#closeBtn {{
            background: transparent;
            color: {sub};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 14px;
            font-size: 12px;
        }}
        QPushButton#closeBtn:hover {{
            background: {comment_bg};
        }}
        QCheckBox {{
            color: {sub};
            font-size: 11px;
            spacing: 4px;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
        }}
        QTextEdit#editArea {{
            background: {comment_bg};
            border: 1px solid {accent};
            border-radius: 6px;
            padding: 6px;
            color: {fg};
            font-size: 13px;
        }}
    """


class FloatingWindow(QWidget):
    """全局快捷键唤出的浮动备注窗口"""

    def __init__(self, comment_service: CommentService, parent=None):
        super().__init__(parent)
        self._service = comment_service
        self._path: Optional[str] = None
        self._edit_mode = False

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 220)

        self._card = QFrame(self)
        self._card.setObjectName("floatCard")
        self._card.setGeometry(0, 0, 420, 220)

        self._build_ui()
        self._apply_theme_style()
        qconfig.themeChangedFinished.connect(self._apply_theme_style)

    def _apply_theme_style(self) -> None:
        """跟随主题切换刷新样式"""
        self.setStyleSheet(_style(isDarkTheme()))

    def set_service(self, comment_service: CommentService) -> None:
        """替换数据服务（设置变更后）"""
        self._service = comment_service
        if self._path is not None and self.isVisible():
            self.trigger(self._path)

    def _build_ui(self) -> None:
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(8)

        # ─ 顶部：文件夹名 + 按钮 ─
        top = QHBoxLayout()
        self._name_label = QLabel("文件夹名")
        self._name_label.setObjectName("folderName")
        top.addWidget(self._name_label)
        top.addStretch()

        self._leave_check = QCheckBox("离开关闭")
        self._leave_check.setChecked(True)
        top.addWidget(self._leave_check)

        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setObjectName("editBtn")
        self._edit_btn.setFixedHeight(28)
        self._edit_btn.clicked.connect(self._toggle_edit)
        top.addWidget(self._edit_btn)

        self._close_btn = QPushButton("双击关闭")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedHeight(28)
        self._close_btn.mouseDoubleClickEvent = lambda _: self.hide()
        card_layout.addLayout(top)

        # ─ 路径 + 时间 ─
        self._path_label = QLabel("H:\\...")
        self._path_label.setObjectName("folderPath")
        card_layout.addWidget(self._path_label)

        self._time_label = QLabel("")
        self._time_label.setObjectName("updateTime")
        card_layout.addWidget(self._time_label)

        card_layout.addSpacing(4)

        # ─ 备注正文（只读 / 编辑） ─
        self._comment_label = QLabel("暂无备注")
        self._comment_label.setObjectName("commentText")
        self._comment_label.setWordWrap(True)
        self._comment_label.setMinimumHeight(50)
        card_layout.addWidget(self._comment_label)

        self._comment_edit = QTextEdit()
        self._comment_edit.setObjectName("editArea")
        self._comment_edit.setPlaceholderText("输入备注内容…")
        self._comment_edit.setVisible(False)
        card_layout.addWidget(self._comment_edit)

        card_layout.addStretch()

    # ─── 公开接口 ───

    def trigger(self, folder_path: str) -> None:
        """快捷键触发：刷新内容并居中弹出"""
        self._path = folder_path
        self._edit_mode = False

        name = os.path.basename(folder_path.rstrip("\\/")) or folder_path
        self._name_label.setText(name)
        self._path_label.setText(folder_path)

        entry = self._service.get(folder_path)
        if entry:
            self._time_label.setText(f"更新于 {entry['updated_at']}")
            self._comment_label.setText(entry["text"] or "暂无备注")
        else:
            self._time_label.setText("")
            self._comment_label.setText("暂无备注")

        self._comment_edit.setVisible(False)
        self._comment_label.setVisible(True)
        self._edit_btn.setText("编辑")

        # 居中
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    # ─── 编辑切换 ───

    def _toggle_edit(self) -> None:
        if self._edit_mode:
            self._save_comment()
        else:
            self._enter_edit()

    def _enter_edit(self) -> None:
        self._edit_mode = True
        self._comment_label.setVisible(False)
        self._comment_edit.setVisible(True)
        self._comment_edit.setPlainText(self._comment_label.text())
        self._edit_btn.setText("保存")
        self._comment_edit.setFocus()

    def _save_comment(self) -> None:
        text = self._comment_edit.toPlainText().strip()
        if self._path:
            entry = self._service.put(self._path, text)
            self._time_label.setText(f"更新于 {entry['updated_at']}")
        self._comment_label.setText(text or "暂无备注")
        self._comment_edit.setVisible(False)
        self._comment_label.setVisible(True)
        self._edit_mode = False
        self._edit_btn.setText("编辑")

    # ─── 鼠标离开自动隐藏 ───

    def leaveEvent(self, event) -> None:
        """鼠标离开窗口时自动隐藏"""
        super().leaveEvent(event)
        if self._leave_check.isChecked():
            QTimer.singleShot(200, self._hide_if_mouse_left)

    def _hide_if_mouse_left(self) -> None:
        """延迟检查鼠标是否仍在窗口内"""
        if not self.isVisible():
            return
        from PyQt5.QtGui import QCursor
        cursor_pos = QCursor.pos()
        if not self.geometry().contains(cursor_pos):
            self.hide()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self._leave_check.isChecked():
            QTimer.singleShot(100, self._hide_if_focus_lost)

    def _hide_if_focus_lost(self) -> None:
        if not self.isVisible():
            return
        fw = QApplication.focusWidget()
        if fw is None:
            self.hide()
            return
        w = fw.window()
        while w is not None:
            if w is self:
                return
            w = w.parentWidget()
        self.hide()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.hide()
        elif event.key() == Qt.Key_Return and self._edit_mode:
            if event.modifiers() & Qt.ControlModifier:
                self._save_comment()
