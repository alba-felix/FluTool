"""一键关闭插件：扫描已安装程序或提取窗口，按 JSON 清单关闭目标应用。"""
from __future__ import annotations

import os
from typing import List

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QListWidgetItem, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    CaptionLabel, ComboBox, FluentIcon as FIF, HeaderCardWidget, InfoBar,
    InfoBarPosition, ListWidget, MessageBox, MessageBoxBase, PrimaryPushButton,
    PushButton, SearchLineEdit, StrongBodyLabel, SubtitleLabel,
    TransparentToolButton, isDarkTheme,
)

from core import PluginInterface
from .scanner import InstalledApp, scan_installed_apps
from .service import (
    CloseResult, ProcessInfo, QuickCloseService, QuickCloseStore,
    display_label, foreground_process, is_default_whitelist_entry,
    is_protected, is_system_process, normalize_entry, sample_processes,
)
from .processes import ProcessGroup, group_processes
from .windows import WindowInfo, list_windows, window_process


class ScanAppDialog(MessageBoxBase):
    """扫描结果选择对话框。"""

    def __init__(self, apps: List[InstalledApp], existing: List[str], parent=None):
        super().__init__(parent)
        self._apps = apps
        self._existing = {normalize_entry(item) for item in existing}

        self.titleLabel = SubtitleLabel("选择要关闭的应用", self)
        self.viewLayout.addWidget(self.titleLabel)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("搜索应用名称或路径")
        self.viewLayout.addWidget(self.searchEdit)

        self.listWidget = ListWidget(self)
        self.listWidget.setMinimumWidth(520)
        self.listWidget.setMinimumHeight(360)
        self.viewLayout.addWidget(self.listWidget)

        self.hintLabel = CaptionLabel("勾选后点击“添加”，同一应用只列出一项", self)
        self.viewLayout.addWidget(self.hintLabel)

        self._populate(apps)
        self.searchEdit.textChanged.connect(self._apply_filter)
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(580)

    def _populate(self, apps: List[InstalledApp]) -> None:
        """填充可勾选的应用列表。"""
        for app in apps:
            suffix = "（已添加）" if normalize_entry(app.exe) in self._existing else ""
            item = QListWidgetItem(f"{app.name}    {app.exe}{suffix}")
            item.setData(Qt.UserRole, app.exe)
            item.setToolTip(app.exe)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.listWidget.addItem(item)

    def _apply_filter(self, text: str) -> None:
        """按关键字过滤列表。"""
        query = text.strip().casefold()
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            item.setHidden(bool(query) and query not in item.text().casefold())

    def selected_apps(self) -> List[str]:
        """返回勾选的 exe 列表。"""
        selected = []
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def validate(self) -> bool:
        """至少选择一个应用才允许添加。"""
        if self.selected_apps():
            self.hintLabel.setText("")
            return True
        self.hintLabel.setText("请至少选择一个应用")
        return False


class WindowListDialog(MessageBoxBase):
    """当前窗口列表选择对话框，可按需刷新。"""

    def __init__(self, windows: List[WindowInfo], existing: List[str],
                 exclude_pids=None, parent=None):
        super().__init__(parent)
        self._existing = {normalize_entry(item) for item in existing}
        self._exclude_pids = exclude_pids or set()
        self._windows: List[WindowInfo] = []

        title_layout = QHBoxLayout()
        title_layout.addWidget(SubtitleLabel("选择要关闭的窗口", self))
        title_layout.addStretch(1)
        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setToolTip("重新读取当前窗口")
        self.refresh_btn.clicked.connect(self._reload_windows)
        title_layout.addWidget(self.refresh_btn)
        self.viewLayout.addLayout(title_layout)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("搜索窗口标题、进程名或路径")
        self.viewLayout.addWidget(self.searchEdit)

        self.listWidget = ListWidget(self)
        self.listWidget.setMinimumWidth(560)
        self.listWidget.setMinimumHeight(380)
        self.viewLayout.addWidget(self.listWidget)

        self.hintLabel = CaptionLabel("", self)
        self.viewLayout.addWidget(self.hintLabel)

        self._apply_windows(windows)
        self.searchEdit.textChanged.connect(self._apply_filter)
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(620)

    def _reload_windows(self) -> None:
        """重新枚举窗口并刷新列表。"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            windows = list_windows(self._exclude_pids)
        finally:
            QApplication.restoreOverrideCursor()
        self._apply_windows(windows)

    def _apply_windows(self, windows: List[WindowInfo]) -> None:
        """填充窗口列表，保留当前搜索过滤。"""
        self._windows = windows
        self.listWidget.clear()

        if not windows:
            item = QListWidgetItem("未读取到可管理的窗口")
            item.setFlags(Qt.NoItemFlags)
            self.listWidget.addItem(item)
            self.hintLabel.setText("")
            return

        for window in windows:
            suffix = "（已添加）" if normalize_entry(window.entry) in self._existing else ""
            label = (
                f"{window.title or '（无标题）'}    {window.image}    "
                f"{window.width}x{window.height}    {window.state}{suffix}"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, window.entry)
            item.setToolTip(window.path or window.image)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.listWidget.addItem(item)

        self.hintLabel.setText("勾选后点击“添加”，同一进程只列出一次")
        self._apply_filter(self.searchEdit.text())

    def _apply_filter(self, text: str) -> None:
        """按关键字过滤列表。"""
        query = text.strip().casefold()
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            item.setHidden(bool(query) and query not in item.text().casefold())

    def selected_entries(self) -> List[str]:
        """返回勾选窗口对应的配置项。"""
        selected = []
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def validate(self) -> bool:
        """至少勾选一个窗口才允许添加。"""
        if self.selected_entries():
            self.hintLabel.setText("")
            return True
        self.hintLabel.setText("请至少勾选一个窗口")
        return False


class ProcessListDialog(MessageBoxBase):
    """任务管理器式进程列表，按程序合并显示。"""

    def __init__(self, processes: List[ProcessInfo], existing: List[str],
                 whitelist: List[str], exclude_pids=None, parent=None):
        super().__init__(parent)
        self._existing = {normalize_entry(item) for item in existing}
        self._whitelist = list(whitelist)
        self._exclude_pids = exclude_pids or set()
        self._groups: List[ProcessGroup] = []
        self._skipped = 0

        title_layout = QHBoxLayout()
        title_layout.addWidget(SubtitleLabel("选择要关闭的进程", self))
        title_layout.addStretch(1)

        self.sortCombo = ComboBox(self)
        self.sortCombo.addItems(["按 CPU", "按内存", "按名称"])
        self.sortCombo.setFixedWidth(110)
        self.sortCombo.currentIndexChanged.connect(self._on_sort_changed)
        title_layout.addWidget(self.sortCombo)

        self.refresh_btn = TransparentToolButton(FIF.SYNC, self)
        self.refresh_btn.setToolTip("重新采样进程")
        self.refresh_btn.clicked.connect(self._reload_processes)
        title_layout.addWidget(self.refresh_btn)
        self.viewLayout.addLayout(title_layout)

        self.searchEdit = SearchLineEdit(self)
        self.searchEdit.setPlaceholderText("搜索进程名、PID 或路径")
        self.viewLayout.addWidget(self.searchEdit)

        self.listWidget = ListWidget(self)
        self.listWidget.setMinimumWidth(600)
        self.listWidget.setMinimumHeight(400)
        self.viewLayout.addWidget(self.listWidget)

        self.hintLabel = CaptionLabel("", self)
        self.viewLayout.addWidget(self.hintLabel)

        self._apply_processes(processes)
        self.searchEdit.textChanged.connect(self._apply_filter)
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")
        self.widget.setMinimumWidth(660)

    def _reload_processes(self) -> None:
        """重新采样进程并刷新列表。"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            processes = sample_processes()
        finally:
            QApplication.restoreOverrideCursor()
        self._apply_processes(processes)

    def _apply_processes(self, processes: List[ProcessInfo]) -> None:
        """过滤白名单进程后按程序合并填充。"""
        eligible = []
        self._skipped = 0
        for process in processes:
            if process.pid in self._exclude_pids:
                continue
            if is_protected(process, self._whitelist):
                self._skipped += 1
                continue
            eligible.append(process)

        self._groups = group_processes(eligible)
        self._populate()

    def _on_sort_changed(self) -> None:
        """切换排序方式，保留已勾选项。"""
        self._populate(preserve=True)

    def _sorted_groups(self) -> List[ProcessGroup]:
        """按当前排序方式返回进程分组。"""
        index = self.sortCombo.currentIndex()
        if index == 1:
            return sorted(self._groups, key=lambda group: (
                -group.memory, -group.cpu, group.image.casefold()
            ))
        if index == 2:
            return sorted(self._groups, key=lambda group: (
                group.image.casefold(), group.pids[0]
            ))
        return sorted(self._groups, key=lambda group: (
            -group.cpu, -group.memory, group.image.casefold()
        ))

    def _checked_entries(self) -> set:
        """读取当前勾选的配置项（规范化后用于比对）。"""
        checked = set()
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            if item.checkState() == Qt.Checked:
                checked.add(normalize_entry(item.data(Qt.UserRole)))
        return checked

    def _populate(self, preserve: bool = False) -> None:
        """按当前排序填充列表。"""
        checked = self._checked_entries() if preserve else set()
        self.listWidget.clear()

        if not self._groups:
            item = QListWidgetItem("未读取到可管理的进程")
            item.setFlags(Qt.NoItemFlags)
            self.listWidget.addItem(item)
            self.hintLabel.setText("")
            return

        for group in self._sorted_groups():
            suffix = "（已添加）" if normalize_entry(group.entry) in self._existing else ""
            pids = "、".join(str(pid) for pid in group.pids[:3])
            if group.count > 3:
                pids += f" 等 {group.count} 个"
            text = (
                f"{group.image}    CPU {group.cpu:.1f}%    "
                f"{group.memory_text}    PID {pids}{suffix}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, group.entry)
            item.setToolTip(group.path or group.image)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(
                Qt.Checked if normalize_entry(group.entry) in checked else Qt.Unchecked
            )
            self.listWidget.addItem(item)

        hint = "勾选后点击“添加”，同一程序合并为一行"
        if self._skipped:
            hint += f"；已隐藏 {self._skipped} 个系统/白名单进程"
        self.hintLabel.setText(hint)
        self._apply_filter(self.searchEdit.text())

    def _apply_filter(self, text: str) -> None:
        """按关键字过滤列表。"""
        query = text.strip().casefold()
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            item.setHidden(bool(query) and query not in item.text().casefold())

    def selected_entries(self) -> List[str]:
        """返回勾选进程对应的配置项。"""
        selected = []
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def validate(self) -> bool:
        """至少勾选一个进程才允许添加。"""
        if self.selected_entries():
            self.hintLabel.setText("")
            return True
        self.hintLabel.setText("请至少勾选一个进程")
        return False


class WindowCaptureHint(QWidget):
    """非模态倒计时提示窗，倒计时结束后读取前台窗口所属进程。"""

    captured = pyqtSignal(object)
    cancelled = pyqtSignal()
    COUNTDOWN_SECONDS = 5

    def __init__(self, parent=None):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setObjectName("windowCaptureHint")
        self.setAttribute(Qt.WA_StyledBackground)
        self._remaining = self.COUNTDOWN_SECONDS
        self._finished = False
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """构建提示内容并应用当前主题配色。"""
        dark = isDarkTheme()
        background = "#2b2b2b" if dark else "#ffffff"
        border = "#3d3d3d" if dark else "#e0e0e0"
        self.setStyleSheet(
            "#windowCaptureHint {"
            f"background: {background}; border: 1px solid {border}; border-radius: 8px;"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.addWidget(StrongBodyLabel("切换到要关闭的目标窗口", self))
        self.countdown_label = CaptionLabel("", self)
        text_layout.addWidget(self.countdown_label)
        layout.addLayout(text_layout)

        cancel_btn = TransparentToolButton(FIF.CLOSE, self)
        cancel_btn.setToolTip("取消提取")
        cancel_btn.clicked.connect(self.close)
        layout.addWidget(cancel_btn)
        self._update_label()

    def _update_label(self) -> None:
        self.countdown_label.setText(f"{self._remaining} 秒后自动提取，点击 × 取消")

    def start(self) -> None:
        """显示提示窗并开始倒计时。"""
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.center().x() - self.width() // 2, area.top() + 80)
        self.show()
        self._timer.start()

    def _tick(self) -> None:
        """每秒更新倒计时，到点后读取前台进程。"""
        self._remaining -= 1
        if self._remaining > 0:
            self._update_label()
            return
        self._timer.stop()
        self._finished = True
        self.captured.emit(foreground_process({os.getpid()}))
        self.close()

    def closeEvent(self, event) -> None:
        """提前关闭视为取消。"""
        self._timer.stop()
        if not self._finished:
            self._finished = True
            self.cancelled.emit()
        super().closeEvent(event)


class QuickCloseWidget(QWidget):
    """一键关闭主界面。"""

    def __init__(self, core=None, parent=None):
        super().__init__(parent)
        self.core = core
        self.store = QuickCloseStore()
        self.service = QuickCloseService(self.store, logger=getattr(core, "logger", None))
        self._capture_hint = None
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        """构建界面。"""
        self.setObjectName("quickCloseWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(2)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.addWidget(SubtitleLabel("一键关闭", self))
        title_layout.addWidget(CaptionLabel(
            "扫描已安装程序、提取窗口或从窗口列表添加；白名单进程不会被结束", self
        ))
        header_layout.addLayout(title_layout, 1)

        self.edit_btn = TransparentToolButton(FIF.EDIT, self)
        self.edit_btn.setToolTip("编辑配置文件")
        self.edit_btn.clicked.connect(self._open_config)
        header_layout.addWidget(self.edit_btn)

        self.reload_btn = TransparentToolButton(FIF.SYNC, self)
        self.reload_btn.setToolTip("重新加载配置")
        self.reload_btn.clicked.connect(self._reload)
        header_layout.addWidget(self.reload_btn)
        layout.addLayout(header_layout)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        self.scan_btn = PushButton("扫描已安装程序", self)
        self.scan_btn.setIcon(FIF.SEARCH)
        self.scan_btn.clicked.connect(self._scan)
        action_layout.addWidget(self.scan_btn)

        self.extract_btn = PushButton("提取窗口", self)
        self.extract_btn.setIcon(FIF.CLIPPING_TOOL)
        self.extract_btn.setToolTip("切换到目标窗口，倒计时结束后自动读取其进程")
        self.extract_btn.clicked.connect(self._extract_window)
        action_layout.addWidget(self.extract_btn)

        self.window_btn = PushButton("窗口列表", self)
        self.window_btn.setIcon(FIF.TILES)
        self.window_btn.setToolTip("读取当前所有窗口（含托盘/隐藏），勾选后加入清单")
        self.window_btn.clicked.connect(self._list_windows)
        action_layout.addWidget(self.window_btn)

        self.process_btn = PushButton("进程列表", self)
        self.process_btn.setIcon(FIF.APPLICATION)
        self.process_btn.setToolTip("按任务管理器方式列出全部进程（含无窗口的后台进程）")
        self.process_btn.clicked.connect(self._list_processes)
        action_layout.addWidget(self.process_btn)
        action_layout.addStretch(1)
        layout.addLayout(action_layout)

        self.target_card = HeaderCardWidget("目标应用", self)
        self.count_label = CaptionLabel("0 个", self.target_card)
        self.target_card.headerLayout.addWidget(self.count_label)
        self.target_card.headerLayout.addStretch(1)

        self.close_btn = PrimaryPushButton("关闭目标应用", self.target_card)
        self.close_btn.setIcon(FIF.CLOSE)
        self.close_btn.clicked.connect(self._close_targets)
        self.target_card.headerLayout.addWidget(self.close_btn)

        self.target_card.viewLayout.setContentsMargins(12, 8, 12, 12)
        self.list_widget = ListWidget(self.target_card.view)
        self.list_widget.setMinimumHeight(240)
        self.target_card.viewLayout.addWidget(self.list_widget)
        layout.addWidget(self.target_card, 1)

        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(2)
        self.whitelist_label = CaptionLabel("", self)
        footer_layout.addWidget(self.whitelist_label)
        self.path_label = CaptionLabel("", self)
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        footer_layout.addWidget(self.path_label)
        layout.addLayout(footer_layout)

    def _refresh(self) -> None:
        """重新读取配置并刷新列表。"""
        data = self.store.load()
        targets = data["targets"]
        whitelist = data["whitelist"]

        self.list_widget.clear()
        if targets:
            for target in targets:
                item = QListWidgetItem(target)
                item.setToolTip(target)
                self.list_widget.addItem(item)
        else:
            item = QListWidgetItem("暂无目标应用，点击上方按钮扫描、提取或从窗口列表添加")
            item.setFlags(Qt.NoItemFlags)
            self.list_widget.addItem(item)

        self.count_label.setText(f"{len(targets)} 个")
        self.close_btn.setEnabled(bool(targets))
        self.whitelist_label.setText(
            f"白名单：{len(whitelist)} 个自定义进程（系统关键进程与本应用已内置保护）"
        )
        self.path_label.setText(f"配置：{self.store.path}")

    def _scan(self) -> None:
        """扫描已安装程序并让用户选择。"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            apps = scan_installed_apps()
        except Exception as exc:
            self._log_error(f"扫描已安装程序失败：{exc}")
            apps = []
        finally:
            QApplication.restoreOverrideCursor()

        if not apps:
            InfoBar.warning(
                title="未扫描到应用",
                content="可直接编辑配置文件，手动填写 exe 名称或完整路径",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
            return

        existing = self.store.load()["targets"]
        dialog = ScanAppDialog(apps, existing, self.window())
        if not dialog.exec():
            return

        added = self.store.add_targets(dialog.selected_apps())
        self._refresh()
        InfoBar.success(
            title="添加完成",
            content=f"新增 {added} 个目标应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    def _extract_window(self) -> None:
        """提示用户切换窗口，倒计时结束后读取前台窗口进程。"""
        if self._capture_hint is not None:
            return
        self._capture_hint = WindowCaptureHint()
        self._capture_hint.captured.connect(self._on_window_captured)
        self._capture_hint.cancelled.connect(self._on_capture_cancelled)
        self._capture_hint.start()

    def _list_windows(self) -> None:
        """读取当前窗口列表并让用户勾选加入清单。"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            windows = list_windows({os.getpid()})
        except Exception as exc:
            self._log_error(f"读取窗口列表失败：{exc}")
            windows = []
        finally:
            QApplication.restoreOverrideCursor()

        if not windows:
            InfoBar.warning(
                title="未读取到窗口",
                content="请先打开目标应用，再点击“窗口列表”",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
            return

        data = self.store.load()
        eligible = [
            window for window in windows
            if not is_protected(window_process(window), data["whitelist"])
        ]
        skipped = len(windows) - len(eligible)
        if not eligible:
            InfoBar.warning(
                title="窗口均在白名单中",
                content="当前窗口都属于白名单进程，不会被关闭",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
            return

        dialog = WindowListDialog(eligible, data["targets"], {os.getpid()}, self.window())
        if not dialog.exec():
            return

        added = self.store.add_targets(dialog.selected_entries())
        self._refresh()
        content = f"新增 {added} 个目标应用"
        if skipped:
            content += f"；已跳过 {skipped} 个系统/白名单窗口"
        InfoBar.success(
            title="添加完成" if added else "没有新增目标",
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    def _list_processes(self) -> None:
        """按任务管理器方式列出进程，勾选加入清单。"""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            processes = sample_processes()
        except Exception as exc:
            self._log_error(f"读取进程列表失败：{exc}")
            processes = []
        finally:
            QApplication.restoreOverrideCursor()

        data = self.store.load()
        dialog = ProcessListDialog(
            processes, data["targets"], data["whitelist"], {os.getpid()}, self.window()
        )
        if not dialog.exec():
            return

        added = self.store.add_targets(dialog.selected_entries())
        self._refresh()
        InfoBar.success(
            title="添加完成" if added else "没有新增目标",
            content=f"新增 {added} 个目标应用",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    def _on_window_captured(self, process) -> None:
        """把提取到的进程写入目标清单。"""
        self._capture_hint = None
        if process is None:
            InfoBar.warning(
                title="未检测到前台窗口",
                content="请先切换到目标应用窗口，再点击“提取窗口”",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )
            return

        whitelist = self.store.load()["whitelist"]
        if is_protected(process, whitelist):
            if is_system_process(process) or is_default_whitelist_entry(process.image):
                content = f"{process.image} 属于系统进程，不会被关闭"
            else:
                content = f"{process.image} 在自定义白名单中；如需关闭请从 whitelist 移除"
            InfoBar.warning(
                title="该进程受保护",
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self,
            )
            return

        entry = process.path or process.image
        added = self.store.add_targets([entry])
        self._refresh()
        if not added:
            InfoBar.info(
                title="已在目标清单中",
                content=entry,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return
        InfoBar.success(
            title="已添加目标",
            content=entry,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self,
        )

    def _on_capture_cancelled(self) -> None:
        """取消提取时释放提示窗引用。"""
        self._capture_hint = None

    def _close_targets(self) -> None:
        """按配置关闭目标应用。"""
        targets = self.store.load()["targets"]
        if not targets:
            InfoBar.warning(
                title="没有目标应用",
                content="请先扫描添加，或编辑配置文件",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )
            return

        box = MessageBox(
            "确认关闭",
            f"将关闭 {len(targets)} 个目标应用，未保存的数据可能丢失。",
            self.window(),
        )
        if not box.exec():
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = self.service.close_targets(targets)
        except Exception as exc:
            self._log_error(f"关闭目标应用失败：{exc}")
            result = CloseResult(failed=[str(exc)])
        finally:
            QApplication.restoreOverrideCursor()

        self._show_result(result)

    def _show_result(self, result: CloseResult) -> None:
        """展示关闭结果。"""
        content = result.summary()
        if result.failed:
            content = f"{content}；{', '.join(result.failed[:5])}"
            InfoBar.error(
                title="部分应用未关闭",
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self,
            )
            return
        InfoBar.success(
            title="关闭完成" if result.closed_count else "没有进程被关闭",
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3500,
            parent=self,
        )

    def _open_config(self) -> None:
        """用系统默认程序打开 JSON 配置。"""
        self.store.load()
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.path))):
            InfoBar.warning(
                title="无法打开配置",
                content=f"请手动编辑：{self.store.path}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self,
            )

    def _reload(self) -> None:
        """刷新配置并提示。"""
        self._refresh()
        InfoBar.success(
            title="已重新加载",
            content="配置修改已生效",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self,
        )

    def _log_error(self, message: str) -> None:
        logger = getattr(self.core, "logger", None)
        if logger is not None:
            logger.error(message)


class Plugin(PluginInterface):
    """一键关闭插件。"""

    PLUGIN_ID = "quick_close"
    PLUGIN_NAME = "一键关闭"
    PLUGIN_ICON = FIF.CLOSE
    PLUGIN_PRIORITY = 11.6

    def initialize(self, core) -> None:
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        return QuickCloseWidget(self.core, parent)

    def load_data(self) -> None:
        if self._widget is not None:
            self._widget._refresh()
