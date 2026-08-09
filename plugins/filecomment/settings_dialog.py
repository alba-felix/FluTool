"""文件夹备注设置面板 — 支持独立对话框和嵌入侧边栏两种模式"""
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QStackedWidget, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    CheckBox, FluentIcon as FIF, NavigationInterface,
    NavigationItemPosition, PushButton, TitleLabel, setTheme, Theme,
    InfoBar, InfoBarPosition, isDarkTheme,
)

from core import get_app_data_path
from core.utils import set_auto_start


def _dialog_style(dark: bool) -> str:
    """设置对话框主题样式（覆盖原生控件的亮色默认外观）"""
    bg = "#202020" if dark else "#ffffff"
    input_bg = "#2d2d2d" if dark else "#f5f5f5"
    border = "#3d3d3d" if dark else "#d0d0d0"
    fg = "#ffffff" if dark else "#1a1a1a"
    sub = "#b0b0b0" if dark else "#666666"
    group_border = "rgba(128,128,128,0.35)" if dark else "rgba(128,128,128,0.25)"
    return f"""
        SettingsDialog {{ background: {bg}; }}
        QWidget#fcStack, QWidget#fcPage, QWidget#fcGroup {{
            background: transparent;
        }}
        QLineEdit {{
            background: {input_bg};
            color: {fg};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 6px 8px;
            selection-background-color: #0078d4;
        }}
        QLabel {{ background: transparent; color: {fg}; }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollArea > QWidget > QWidget {{ background: transparent; }}
        QScrollBar {{ background: transparent; }}
        QLabel#groupTitle {{ color: {fg}; font-weight: bold; font-size: 13px; border: none; }}
        QLabel#hotkeyLabel {{ color: {fg}; font-size: 13px; padding: 6px 0; }}
        QWidget#fcGroup {{ border: 1px solid {group_border}; border-radius: 8px; padding: 12px; }}
    """


def _dialog_theme() -> str:
    from qfluentwidgets import isDarkTheme
    return _dialog_style(isDarkTheme())


class SettingsDialog(QWidget):
    """文件夹备注设置面板

    可独立作为对话框使用，也可嵌入侧边栏。
    嵌入模式下隐藏底部按钮，设置即时生效。
    """
    settings_changed = pyqtSignal()

    def __init__(self, core, parent=None, embedded: bool = False):
        super().__init__(parent)
        self.core = core
        self._embedded = embedded

        if not embedded:
            self.setWindowTitle("文件夹备注 - 设置")
            self.resize(780, 520)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._nav = NavigationInterface(self)
        self._nav.setFixedWidth(200)
        root.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._stack.setObjectName("fcStack")
        self._stack.setContentsMargins(32, 24, 32, 24)
        root.addWidget(self._stack, 1)

        # ── 页面 ─
        self._basic_page = self._build_basic_page()
        self._list_page = self._build_list_page()
        self._about_page = self._build_about_page()

        self._stack.addWidget(self._basic_page)
        self._stack.addWidget(self._list_page)
        self._stack.addWidget(self._about_page)

        self._nav.addItem("basic", FIF.SETTING, "基础设置", onClick=lambda: self._switch("basic"))
        self._nav.addItem("list", FIF.MARKET, "备注列表", onClick=lambda: self._switch("list"))
        self._nav.addItem("about", FIF.INFO, "关于", onClick=lambda: self._switch("about"))

        self._nav.setCurrentItem("basic")
        self._show(self._basic_page)

        self.setStyleSheet(_dialog_theme())
        from qfluentwidgets import qconfig
        qconfig.themeChangedFinished.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        """主题切换后刷新对话框样式"""
        self.setStyleSheet(_dialog_theme())

    # ── 基础设置 ─

    def _build_basic_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("fcPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel("基础设置"))

        # 数据路径
        path_box = self._make_group("数据保存路径")
        self._path_edit = QLineEdit()
        self._path_edit.setText(str(get_app_data_path("data/filecomment")))
        btn_row = QHBoxLayout()
        browse_btn = PushButton("浏览", icon=FIF.FOLDER)
        browse_btn.clicked.connect(self._browse_path)
        reset_btn = PushButton("恢复默认")
        reset_btn.clicked.connect(lambda: self._path_edit.setText(str(get_app_data_path("data/filecomment"))))
        btn_row.addWidget(browse_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        path_box.layout().addWidget(self._path_edit)
        path_box.layout().addLayout(btn_row)
        layout.addWidget(path_box)

        # 快捷键
        hk_box = self._make_group("唤出快捷键")
        self._hotkey_label = QLabel(self._fmt_hotkey(self.core.config.filecomment_hotkey.value or "alt+space"))
        self._hotkey_label.setObjectName("hotkeyLabel")
        hk_box.layout().addWidget(self._hotkey_label)
        self._hk_set_btn = PushButton("点击此处按下新快捷键")
        self._hk_set_btn.setCheckable(True)
        self._hk_set_btn.clicked.connect(self._capture_hotkey)
        hk_box.layout().addWidget(self._hk_set_btn)
        layout.addWidget(hk_box)

        # 自启动
        auto_box = self._make_group("启动选项")
        self._auto_start_cb = CheckBox("开机自动启动")
        self._auto_start_cb.setChecked(self.core.config.filecomment_autostart.value)
        self._auto_start_cb.toggled.connect(self._on_auto_start)
        auto_box.layout().addWidget(self._auto_start_cb)

        self._context_menu_cb = CheckBox("添加到资源管理器右键菜单")
        self._context_menu_cb.setChecked(self.core.config.filecomment_context_menu.value)
        self._context_menu_cb.toggled.connect(self._on_context_menu)
        auto_box.layout().addWidget(self._context_menu_cb)

        layout.addWidget(auto_box)

        layout.addStretch()

        # 底部按钮（仅对话框模式显示）
        if not self._embedded:
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            cancel = PushButton("取消")
            cancel.clicked.connect(self.close)
            save = PushButton("保存")
            save.clicked.connect(self._save)
            btn_layout.addWidget(cancel)
            btn_layout.addWidget(save)
            layout.addLayout(btn_layout)

        return page

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("fcPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(TitleLabel("备注列表"))

        from .comment_list_widget import CommentListWidget
        self._comment_list = CommentListWidget(self.core)
        layout.addWidget(self._comment_list, 1)
        return page

    def _build_about_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("fcPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(TitleLabel("关于"))
        info = QLabel(
            "文件夹备注助手 v1.0\n\n"
            "快捷键唤出浮窗，对当前文件夹添加备注。\n"
            "数据保存在本地 JSON 文件中。"
        )
        sub = "#b0b0b0" if isDarkTheme() else "#666666"
        info.setStyleSheet(f"font-size: 13px; color: {sub}; line-height: 1.6;")
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        return page

    # ── 工具 ─

    def _make_group(self, title: str) -> QWidget:
        group = QWidget()
        group.setObjectName("fcGroup")
        l = QVBoxLayout(group)
        l.setSpacing(8)
        lbl = QLabel(title)
        lbl.setObjectName("groupTitle")
        l.addWidget(lbl)
        return group

    def _switch(self, key: str) -> None:
        m = {"basic": self._basic_page, "list": self._list_page, "about": self._about_page}
        if key in m:
            self._show(m[key])

    def _show(self, w: QWidget) -> None:
        self._stack.setCurrentWidget(w)

    def _browse_path(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择数据目录", self._path_edit.text())
        if d:
            self._path_edit.setText(d)
            if self._embedded:
                self._save()

    def _capture_hotkey(self) -> None:
        self._hk_set_btn.setText("请按下快捷键…")
        from .hotkey_manager import HotkeyManager
        self._temp_hkm = HotkeyManager()
        self._temp_hkm.capture_done.connect(self._on_hotkey_captured)
        self._temp_hkm.start_capture()

    def _on_hotkey_captured(self, combo: str) -> None:
        self._hotkey_label.setText(self._fmt_hotkey(combo))
        self._hk_set_btn.setText("点击此处按下新快捷键")
        self._hk_set_btn.setChecked(False)
        self.core.config.set(self.core.config.filecomment_hotkey, combo)
        if self._embedded:
            self._save()

    @staticmethod
    def _fmt_hotkey(combo: str) -> str:
        """快捷键显示格式：alt+space -> Alt + Space"""
        return combo.replace("+", " + ").title()

    def _on_auto_start(self, checked: bool) -> None:
        set_auto_start(checked)
        self.core.config.set(self.core.config.filecomment_autostart, checked)
        if self._embedded:
            self._save()

    def _on_context_menu(self, checked: bool) -> None:
        from core.utils import set_explorer_context_menu
        set_explorer_context_menu(checked)
        self.core.config.set(self.core.config.filecomment_context_menu, checked)
        if self._embedded:
            self._save()

    def _save(self) -> None:
        self.core.config.set(self.core.config.filecomment_data_path, self._path_edit.text())
        self.settings_changed.emit()
        if not self._embedded:
            self.close()
        else:
            InfoBar.success(
                title="已保存",
                content="设置已即时生效",
                parent=self,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=1500,
            )
