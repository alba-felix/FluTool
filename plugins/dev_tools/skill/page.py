"""SKILL Manager UI — 完整技能管理界面（优化版）

视图:
- Library: 中央库卡片浏览、搜索、标签过滤、安装/卸载
- Global Workspace: 按 Agent 管理全局技能
- Settings: 仓库路径、同步模式、自定义 Agent
"""

from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QSizePolicy, QFileDialog, QInputDialog, QLineEdit,
    QStackedWidget, QGraphicsDropShadowEffect,
)
from qfluentwidgets import (
    FluentIcon as FIF,
    PushButton, TransparentToolButton, SearchLineEdit,
    StrongBodyLabel, BodyLabel, CaptionLabel, SubtitleLabel, TitleLabel,
    InfoBar, InfoBarPosition, isDarkTheme,
    ComboBox, PrimaryPushButton,
    MessageBoxBase, MessageBox,
    IconWidget,
    setTheme, Theme, qconfig,
)

from ..page_interface import TabPageInterface
from .skill_manager import (
    Skill, Agent, Preset, Workspace, SkillService,
    DEFAULT_SKILLS_ROOT, SYNC_MODE_COPY, SYNC_MODE_SYMLINK,
)


# ══════════════════════════════════════════════════════════
#  Theme helpers
# ══════════════════════════════════════════════════════════

def _card_bg() -> str:
    return "#2d2d2d" if isDarkTheme() else "#ffffff"

def _card_border() -> str:
    return "#3d3d3d" if isDarkTheme() else "#e0e0e0"

def _card_hover_border() -> str:
    return "#0078d4"

def _text_primary() -> str:
    return "#ffffff" if isDarkTheme() else "#1a1a1a"

def _text_secondary() -> str:
    return "#aaaaaa" if isDarkTheme() else "#666666"

def _text_muted() -> str:
    return "#777777" if isDarkTheme() else "#999999"

def _accent() -> str:
    return "#0078d4"

def _section_bg() -> str:
    return "#252525" if isDarkTheme() else "#f8f8f8"

def _separator_color() -> str:
    return "#3d3d3d" if isDarkTheme() else "#e0e0e0"

def _nav_bg() -> str:
    return "#1e1e1e" if isDarkTheme() else "#f0f0f0"

def _nav_hover() -> str:
    return "#333333" if isDarkTheme() else "#e0e0e0"

def _tag_bg() -> str:
    return "#1e3a5f" if isDarkTheme() else "#e8f4fd"

def _tag_text() -> str:
    return "#5ba3d9" if isDarkTheme() else "#0078d4"

def _success_color() -> str:
    return "#2ea043"

def _warning_color() -> str:
    return "#e8a838"

def _danger_color() -> str:
    return "#d73a49"


# ══════════════════════════════════════════════════════════
#  Skill Card
# ══════════════════════════════════════════════════════════

class SkillCard(QFrame):
    """单个 SKILL 卡片 — 带阴影、圆角、hover 效果"""

    uninstall_clicked = pyqtSignal(str)
    update_clicked = pyqtSignal(str)

    # 来源标签配色（不随主题变化）
    _SOURCE_COLORS = {
        "local": ("#2ea043", "#e6f4ea"),
        "git": ("#0078d4", "#e8f4fd"),
        "zip": ("#8b5cf6", "#f0e8fd"),
        "marketplace": ("#e8a838", "#fdf4e8"),
    }

    def __init__(self, skill: Skill, parent=None):
        super().__init__(parent)
        self.skill = skill
        # 保存子组件引用以便主题刷新
        self._source_tag: Optional[CaptionLabel] = None
        self._desc_label: Optional[BodyLabel] = None
        self._tag_labels: List[CaptionLabel] = []
        self._meta_label: Optional[CaptionLabel] = None
        self._update_label: Optional[CaptionLabel] = None
        self._setup_ui()
        self._apply_theme()
        self._setup_shadow()

    def _setup_ui(self) -> None:
        self.setFixedHeight(130)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 12, 12)
        layout.setSpacing(14)

        # 左侧图标区域
        icon_frame = QFrame(self)
        icon_frame.setFixedSize(52, 52)
        icon_frame.setObjectName("cardIconFrame")
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("📦", icon_frame)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 24px;")
        icon_layout.addWidget(icon_label)
        layout.addWidget(icon_frame)

        # 中间信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 2, 0, 2)

        # 名称行
        name_row = QHBoxLayout()
        name_label = StrongBodyLabel(self.skill.name, self)
        name_row.addWidget(name_label)
        name_row.addStretch()

        # 来源标签
        fg, bg = self._SOURCE_COLORS.get(
            self.skill.source, (_text_secondary(), _section_bg())
        )
        self._source_tag = CaptionLabel(self.skill.source.upper(), self)
        self._source_tag.setStyleSheet(
            f"padding: 2px 8px; border-radius: 10px; font-size: 10px;"
            f"background-color: {bg}; color: {fg};"
        )
        name_row.addWidget(self._source_tag)
        info_layout.addLayout(name_row)

        # 描述
        desc = self.skill.description[:90] + ("..." if len(self.skill.description) > 90 else "")
        self._desc_label = BodyLabel(desc, self)
        self._desc_label.setWordWrap(True)
        self._desc_label.setMaximumHeight(32)
        info_layout.addWidget(self._desc_label)

        # 标签行
        if self.skill.tags:
            tags_row = QHBoxLayout()
            tags_row.setSpacing(4)
            for tag in self.skill.tags[:4]:
                t = CaptionLabel(tag, self)
                self._tag_labels.append(t)
                tags_row.addWidget(t)
            info_layout.addLayout(tags_row)

        # 底部元信息
        meta_row = QHBoxLayout()
        size_text = f"{self.skill.size_kb:.0f}KB" if self.skill.size_kb < 1024 else f"{self.skill.size_kb/1024:.1f}MB"
        self._meta_label = CaptionLabel(f"{self.skill.file_count} 文件 · {size_text}", self)
        meta_row.addWidget(self._meta_label)
        meta_row.addStretch()

        if self.skill.has_update:
            self._update_label = CaptionLabel("⬆ 有更新", self)
            self._update_label.setStyleSheet(f"color: {_warning_color()}; font-weight: bold;")
            meta_row.addWidget(self._update_label)

        info_layout.addLayout(meta_row)
        layout.addLayout(info_layout, 1)

        # 右侧操作按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignVCenter)

        if self.skill.source in ("git", "marketplace"):
            update_btn = TransparentToolButton(FIF.UPDATE, self)
            update_btn.setFixedSize(32, 32)
            update_btn.setToolTip("更新")
            update_btn.clicked.connect(lambda: self.update_clicked.emit(self.skill.id))
            btn_layout.addWidget(update_btn)

        uninstall_btn = TransparentToolButton(FIF.DELETE, self)
        uninstall_btn.setFixedSize(32, 32)
        uninstall_btn.setToolTip("卸载")
        uninstall_btn.clicked.connect(lambda: self.uninstall_clicked.emit(self.skill.id))
        btn_layout.addWidget(uninstall_btn)

        layout.addLayout(btn_layout)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {_card_bg()};
                border: 1px solid {_card_border()};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {_card_hover_border()};
            }}
            QFrame#cardIconFrame {{
                background-color: {_section_bg()};
                border-radius: 10px;
                border: none;
            }}
        """)
        # 刷新子组件主题色
        fg, bg = self._SOURCE_COLORS.get(
            self.skill.source, (_text_secondary(), _section_bg())
        )
        if self._source_tag:
            self._source_tag.setStyleSheet(
                f"padding: 2px 8px; border-radius: 10px; font-size: 10px;"
                f"background-color: {bg}; color: {fg};"
            )
        if self._desc_label:
            self._desc_label.setStyleSheet(f"color: {_text_secondary()};")
        for t in self._tag_labels:
            t.setStyleSheet(
                f"padding: 1px 7px; border-radius: 8px; font-size: 10px;"
                f"background-color: {_tag_bg()}; color: {_tag_text()};"
            )
        if self._meta_label:
            self._meta_label.setStyleSheet(f"color: {_text_muted()};")
        if self._update_label:
            self._update_label.setStyleSheet(f"color: {_warning_color()}; font-weight: bold;")

    def _setup_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 20 if isDarkTheme() else 10))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def refresh_theme(self) -> None:
        """主题切换时刷新所有样式"""
        self._apply_theme()
        self._setup_shadow()


# ══════════════════════════════════════════════════════════
#  Section Card (for Settings)
# ══════════════════════════════════════════════════════════

class SectionCard(QFrame):
    """设置页的分组卡片"""

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._content_layout: Optional[QVBoxLayout] = None
        self._sub_label: Optional[CaptionLabel] = None
        self._sep: Optional[QFrame] = None
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # 标题行
        title_row = QHBoxLayout()
        title_row.addWidget(StrongBodyLabel(self._title, self))
        title_row.addStretch()
        layout.addLayout(title_row)

        if self._subtitle:
            self._sub_label = CaptionLabel(self._subtitle, self)
            layout.addWidget(self._sub_label)

        # 分隔线
        self._sep = QFrame(self)
        self._sep.setFixedHeight(1)
        layout.addWidget(self._sep)

        # 内容区
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(8)
        layout.addLayout(self._content_layout)

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {_card_bg()};
                border: 1px solid {_card_border()};
                border-radius: 10px;
            }}
        """)
        if self._sub_label:
            self._sub_label.setStyleSheet(f"color: {_text_muted()};")
        if self._sep:
            self._sep.setStyleSheet(f"background-color: {_separator_color()}; border: none;")

    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def refresh_theme(self) -> None:
        """主题切换时刷新样式"""
        self._apply_theme()


# ══════════════════════════════════════════════════════════
#  Library View
# ══════════════════════════════════════════════════════════

class LibraryView(QWidget):
    """中央库视图 — 卡片浏览、搜索、标签过滤"""

    def __init__(self, service: SkillService, parent=None):
        super().__init__(parent)
        self._service = service
        self._current_tag: Optional[str] = None
        self._current_source: Optional[str] = None
        self._search_text = ""
        self._filter_frame: Optional[QFrame] = None
        self._stats_label: Optional[CaptionLabel] = None
        self._setup_ui()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # ── 顶部工具栏 ──
        toolbar = QHBoxLayout()

        title = TitleLabel("技能库", self)
        toolbar.addWidget(title)
        toolbar.addStretch()

        self._search = SearchLineEdit(self)
        self._search.setPlaceholderText("搜索技能名称或描述...")
        self._search.setFixedWidth(260)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        toolbar.addWidget(self._search)

        install_btn = PrimaryPushButton("安装技能", self)
        install_btn.setIcon(FIF.DOWNLOAD)
        install_btn.setFixedHeight(34)
        install_btn.clicked.connect(self._show_install_dialog)
        toolbar.addWidget(install_btn)

        refresh_btn = TransparentToolButton(FIF.SYNC, self)
        refresh_btn.setFixedSize(36, 36)
        refresh_btn.setToolTip("刷新")
        refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # ── 过滤栏 ──
        self._filter_frame = QFrame(self)
        self._filter_frame.setObjectName("filterFrame")
        filter_layout = QHBoxLayout(self._filter_frame)
        filter_layout.setContentsMargins(14, 8, 14, 8)
        filter_layout.setSpacing(8)

        filter_layout.addWidget(CaptionLabel("来源:", self))
        self._source_combo = ComboBox(self)
        self._source_combo.setFixedWidth(110)
        self._source_combo.setFixedHeight(30)
        self._source_combo.addItem("全部")
        self._source_combo.addItem("local")
        self._source_combo.addItem("git")
        self._source_combo.addItem("zip")
        self._source_combo.currentTextChanged.connect(self._on_source_filter)
        filter_layout.addWidget(self._source_combo)

        filter_layout.addSpacing(8)
        filter_layout.addWidget(CaptionLabel("标签:", self))
        self._tag_combo = ComboBox(self)
        self._tag_combo.setFixedWidth(130)
        self._tag_combo.setFixedHeight(30)
        self._tag_combo.addItem("全部")
        self._tag_combo.currentTextChanged.connect(self._on_tag_filter)
        filter_layout.addWidget(self._tag_combo)

        filter_layout.addStretch()

        self._stats_label = CaptionLabel("", self)
        filter_layout.addWidget(self._stats_label)

        layout.addWidget(self._filter_frame)

        # ── 卡片滚动区域 ──
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(10)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self._apply_frame_theme()

    def _apply_frame_theme(self) -> None:
        """刷新过滤栏和统计标签的主题色"""
        if self._filter_frame:
            self._filter_frame.setStyleSheet(f"""
                QFrame#filterFrame {{
                    background-color: {_section_bg()};
                    border-radius: 8px;
                    border: 1px solid {_card_border()};
                }}
            """)
        if self._stats_label:
            self._stats_label.setStyleSheet(f"color: {_text_muted()};")

    def refresh_theme(self) -> None:
        """主题切换时刷新所有样式"""
        self._apply_frame_theme()
        # 刷新所有 SkillCard
        for card in self.findChildren(SkillCard):
            card.refresh_theme()
        # 刷新空状态标签
        for lbl in self._content.findChildren(CaptionLabel):
            if "color" in lbl.styleSheet():
                lbl.setStyleSheet(f"color: {_text_muted()};")
        for lbl in self._content.findChildren(BodyLabel):
            if "color" in lbl.styleSheet():
                lbl.setStyleSheet(f"color: {_text_muted()};")

    def _refresh(self) -> None:
        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        skills = self._service.db.list_skills(
            tag_filter=self._current_tag if self._current_tag != "全部" else None,
            source_filter=self._current_source if self._current_source != "全部" else None,
            search_query=self._search_text or None,
        )

        if not skills:
            empty_frame = QFrame(self._content)
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setAlignment(Qt.AlignCenter)

            icon = QLabel("", empty_frame)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("font-size: 48px;")
            empty_layout.addWidget(icon)
            empty_layout.addSpacing(12)

            empty = BodyLabel("技能库为空", empty_frame)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {_text_muted()}; font-size: 14px;")
            empty_layout.addWidget(empty)

            hint = CaptionLabel("点击「安装技能」添加第一个技能", empty_frame)
            hint.setAlignment(Qt.AlignCenter)
            hint.setStyleSheet(f"color: {_text_muted()};")
            empty_layout.addWidget(hint)

            self._content_layout.insertWidget(0, empty_frame)
        else:
            for i in range(0, len(skills), 2):
                row = QWidget(self._content)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(10)

                card1 = SkillCard(skills[i], row)
                card1.uninstall_clicked.connect(self._on_uninstall)
                card1.update_clicked.connect(self._on_update)
                row_layout.addWidget(card1, 1)

                if i + 1 < len(skills):
                    card2 = SkillCard(skills[i + 1], row)
                    card2.uninstall_clicked.connect(self._on_uninstall)
                    card2.update_clicked.connect(self._on_update)
                    row_layout.addWidget(card2, 1)
                else:
                    row_layout.addStretch(1)

                self._content_layout.insertWidget(self._content_layout.count() - 1, row)

        all_skills = self._service.db.list_skills()
        enabled = sum(1 for s in all_skills if s.enabled)
        self._stats_label.setText(f"共 {len(all_skills)} 个技能 · {enabled} 已启用")

        all_tags = self._service.get_all_tags()
        current = self._tag_combo.currentText()
        self._tag_combo.blockSignals(True)
        self._tag_combo.clear()
        self._tag_combo.addItem("全部")
        for t in all_tags:
            self._tag_combo.addItem(t)
        if current in all_tags or current == "全部":
            self._tag_combo.setCurrentText(current)
        self._tag_combo.blockSignals(False)

    def _on_search(self, text: str) -> None:
        self._search_text = text
        self._refresh()

    def _on_source_filter(self, text: str) -> None:
        self._current_source = text
        self._refresh()

    def _on_tag_filter(self, text: str) -> None:
        self._current_tag = text
        self._refresh()

    def _show_install_dialog(self) -> None:
        dialog = InstallDialog(self._service, self)
        if dialog.exec():
            self._refresh()

    def _on_uninstall(self, skill_id: str) -> None:
        skill = self._service.db.get_skill(skill_id)
        if not skill:
            return
        box = MessageBox("确认卸载", f"确定要卸载技能 '{skill.name}' 吗？\n\n本地文件将被删除。", self)
        if box.exec():
            self._service.uninstall_skill(skill_id)
            InfoBar.success("已卸载", f"技能 '{skill.name}' 已卸载", parent=self, duration=2000)
            self._refresh()

    def _on_update(self, skill_id: str) -> None:
        success = self._service.update_skill(skill_id)
        if success:
            InfoBar.success("更新成功", f"技能 '{skill_id}' 已更新", parent=self, duration=2000)
        else:
            InfoBar.warning("更新失败", f"技能 '{skill_id}' 更新失败", parent=self, duration=2000)
        self._refresh()


# ══════════════════════════════════════════════════════════
#  Install Dialog
# ══════════════════════════════════════════════════════════

class InstallDialog(MessageBoxBase):
    """安装技能对话框"""

    def __init__(self, service: SkillService, parent=None):
        super().__init__(parent)
        self._service = service
        self.setWindowTitle("安装技能")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = self.viewLayout
        layout.setSpacing(14)

        # 来源选择
        source_label = StrongBodyLabel("选择安装来源", self)
        layout.addWidget(source_label)

        self._source_combo = ComboBox(self)
        self._source_combo.setFixedHeight(34)
        self._source_combo.addItem("📁 本地目录")
        self._source_combo.addItem(" Git 仓库")
        self._source_combo.addItem("📦 ZIP 文件")
        self._source_combo.currentTextChanged.connect(self._on_source_changed)
        layout.addWidget(self._source_combo)

        # 本地目录
        self._local_widget = QWidget(self)
        local_row = QHBoxLayout(self._local_widget)
        local_row.setContentsMargins(0, 0, 0, 0)
        self._local_path = QLineEdit(self)
        self._local_path.setPlaceholderText("选择技能目录...")
        self._local_path.setFixedHeight(34)
        local_row.addWidget(self._local_path)
        browse_btn = PushButton("浏览", self)
        browse_btn.setFixedSize(60, 34)
        browse_btn.clicked.connect(self._browse_local)
        local_row.addWidget(browse_btn)
        layout.addWidget(self._local_widget)

        # Git URL
        self._git_widget = QWidget(self)
        git_row = QHBoxLayout(self._git_widget)
        git_row.setContentsMargins(0, 0, 0, 0)
        self._git_url = QLineEdit(self)
        self._git_url.setPlaceholderText("https://github.com/user/repo.git")
        self._git_url.setFixedHeight(34)
        git_row.addWidget(self._git_url)
        self._git_ref = QLineEdit(self)
        self._git_ref.setPlaceholderText("分支/标签")
        self._git_ref.setFixedWidth(120)
        self._git_ref.setFixedHeight(34)
        git_row.addWidget(self._git_ref)
        layout.addWidget(self._git_widget)

        # ZIP 文件
        self._zip_widget = QWidget(self)
        zip_row = QHBoxLayout(self._zip_widget)
        zip_row.setContentsMargins(0, 0, 0, 0)
        self._zip_path = QLineEdit(self)
        self._zip_path.setPlaceholderText("选择 ZIP 文件...")
        self._zip_path.setFixedHeight(34)
        zip_row.addWidget(self._zip_path)
        zip_browse = PushButton("浏览", self)
        zip_browse.setFixedSize(60, 34)
        zip_browse.clicked.connect(self._browse_zip)
        zip_row.addWidget(zip_browse)
        layout.addWidget(self._zip_widget)

        # 技能 ID
        layout.addWidget(CaptionLabel("技能 ID（可选，默认使用目录名）:", self))
        self._skill_id = QLineEdit(self)
        self._skill_id.setPlaceholderText("留空则自动推断")
        self._skill_id.setFixedHeight(34)
        layout.addWidget(self._skill_id)

        layout.addStretch()
        self._on_source_changed("📁 本地目录")

    def _on_source_changed(self, text: str) -> None:
        self._local_widget.setVisible("本地" in text)
        self._git_widget.setVisible("Git" in text)
        self._zip_widget.setVisible("ZIP" in text)

    def _browse_local(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择技能目录")
        if path:
            self._local_path.setText(path)

    def _browse_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 ZIP 文件", "", "ZIP Files (*.zip)")
        if path:
            self._zip_path.setText(path)

    def validate(self) -> bool:
        source = self._source_combo.currentText()
        skill_id = self._skill_id.text().strip() or None

        try:
            if "本地" in source:
                path = self._local_path.text().strip()
                if not path:
                    InfoBar.warning("提示", "请选择本地目录", parent=self, duration=2000)
                    return False
                self._service.install_from_local(path, skill_id)
            elif "Git" in source:
                url = self._git_url.text().strip()
                if not url:
                    InfoBar.warning("提示", "请输入 Git 仓库 URL", parent=self, duration=2000)
                    return False
                ref = self._git_ref.text().strip()
                self._service.install_from_git(url, ref, skill_id)
            elif "ZIP" in source:
                path = self._zip_path.text().strip()
                if not path:
                    InfoBar.warning("提示", "请选择 ZIP 文件", parent=self, duration=2000)
                    return False
                self._service.install_from_zip(path, skill_id)
            return True
        except Exception as e:
            InfoBar.error("安装失败", str(e), parent=self, duration=3000)
            return False


# ══════════════════════════════════════════════════════════
#  Global Workspace View
# ══════════════════════════════════════════════════════════

class GlobalWorkspaceView(QWidget):
    """全局工作区 — 按 Agent 管理技能"""

    def __init__(self, service: SkillService, parent=None):
        super().__init__(parent)
        self._service = service
        self._agent_card: Optional[QFrame] = None
        self._agent_info: Optional[CaptionLabel] = None
        self._setup_ui()
        self._refresh_agents()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = TitleLabel("全局工作区", self)
        layout.addWidget(title)

        # Agent 选择卡片
        self._agent_card = QFrame(self)
        self._agent_card.setObjectName("agentCard")
        agent_layout = QHBoxLayout(self._agent_card)
        agent_layout.setContentsMargins(16, 12, 16, 12)

        agent_layout.addWidget(CaptionLabel("Agent:", self))
        self._agent_combo = ComboBox(self)
        self._agent_combo.setFixedWidth(200)
        self._agent_combo.setFixedHeight(34)
        self._agent_combo.currentTextChanged.connect(self._on_agent_changed)
        agent_layout.addWidget(self._agent_combo)
        agent_layout.addStretch()

        self._agent_info = CaptionLabel("", self)
        agent_layout.addWidget(self._agent_info)

        layout.addWidget(self._agent_card)

        # 技能列表
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QScrollArea.NoFrame)
        self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(6)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self._apply_frame_theme()

    def _apply_frame_theme(self) -> None:
        """刷新 agent 卡片和信息标签的主题色"""
        if self._agent_card:
            self._agent_card.setStyleSheet(f"""
                QFrame#agentCard {{
                    background-color: {_section_bg()};
                    border-radius: 8px;
                    border: 1px solid {_card_border()};
                }}
            """)
        if self._agent_info:
            self._agent_info.setStyleSheet(f"color: {_text_muted()};")

    def refresh_theme(self) -> None:
        """主题切换时刷新所有样式"""
        self._apply_frame_theme()
        for section in self.findChildren(SectionCard):
            section.refresh_theme()
        # 刷新内容区域的主题感知标签
        for lbl in self._content.findChildren(CaptionLabel):
            ss = lbl.styleSheet()
            if "color" in ss:
                lbl.setStyleSheet(f"color: {_text_muted()};")
        for frame in self._content.findChildren(QFrame):
            if frame.objectName() == "":
                ss = frame.styleSheet()
                if "border-bottom" in ss:
                    frame.setStyleSheet(f"""
                        QFrame {{
                            background: transparent;
                            border-bottom: 1px solid {_separator_color()};
                        }}
                    """)

    def _refresh_agents(self) -> None:
        agents = self._service.db.list_agents()
        self._agent_combo.blockSignals(True)
        self._agent_combo.clear()
        for a in agents:
            self._agent_combo.addItem(a.display_name)
        self._agent_combo.blockSignals(False)
        if agents:
            self._on_agent_changed(agents[0].display_name)

    def _on_agent_changed(self, display_name: str) -> None:
        agents = self._service.db.list_agents()
        agent = next((a for a in agents if a.display_name == display_name), None)
        if not agent:
            return

        self._agent_info.setText(f"目录: {agent.expanded_skills_dir}")

        while self._content_layout.count() > 1:
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        agent_dir = agent.expanded_skills_dir
        installed_skills = []
        if agent_dir.is_dir():
            for child in agent_dir.iterdir():
                if child.is_dir() or child.is_symlink():
                    installed_skills.append(child.name)

        all_skills = self._service.db.list_skills()

        if not installed_skills and not all_skills:
            empty_frame = QFrame(self._content)
            empty_layout = QVBoxLayout(empty_frame)
            empty_layout.setAlignment(Qt.AlignCenter)
            icon = QLabel("", empty_frame)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("font-size: 48px;")
            empty_layout.addWidget(icon)
            empty_layout.addSpacing(12)
            empty = BodyLabel("该 Agent 暂无技能", empty_frame)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {_text_muted()};")
            empty_layout.addWidget(empty)
            self._content_layout.insertWidget(0, empty_frame)
            return

        # 已安装技能
        if installed_skills:
            section = SectionCard(f"已安装 ({len(installed_skills)})", parent=self._content)
            cl = section.content_layout()

            for sname in installed_skills:
                row = QHBoxLayout()
                name_label = BodyLabel(sname, self)
                row.addWidget(name_label)
                row.addStretch()

                in_library = any(s.id == sname for s in all_skills)
                if in_library:
                    status = CaptionLabel("● 库中", self)
                    status.setStyleSheet(f"color: {_success_color()};")
                else:
                    status = CaptionLabel("● 外部", self)
                    status.setStyleSheet(f"color: {_warning_color()};")
                row.addWidget(status)

                remove_btn = TransparentToolButton(FIF.DELETE, self)
                remove_btn.setFixedSize(28, 28)
                remove_btn.setToolTip("移除")
                row.addWidget(remove_btn)

                row_widget = QFrame(self)
                row_widget.setLayout(row)
                row_widget.setFixedHeight(44)
                row_widget.setStyleSheet(f"""
                    QFrame {{
                        background: transparent;
                        border-bottom: 1px solid {_separator_color()};
                    }}
                """)
                cl.addWidget(row_widget)

            self._content_layout.insertWidget(self._content_layout.count() - 1, section)

        # 可同步技能
        available = [s for s in all_skills if s.id not in installed_skills]
        if available:
            section2 = SectionCard(f"可同步 ({len(available)})", parent=self._content)
            cl2 = section2.content_layout()

            for skill in available[:15]:
                row = QHBoxLayout()
                name_label = BodyLabel(skill.name, self)
                row.addWidget(name_label)

                source_tag = CaptionLabel(skill.source.upper(), self)
                source_tag.setStyleSheet(
                    f"padding: 1px 6px; border-radius: 8px; font-size: 10px;"
                    f"background-color: {_tag_bg()}; color: {_tag_text()};"
                )
                row.addWidget(source_tag)
                row.addStretch()

                sync_btn = PushButton("同步", self)
                sync_btn.setFixedSize(56, 28)
                sid = skill.id
                an = agent.name
                sync_btn.clicked.connect(lambda checked, s=sid, a=an: self._on_sync(s, a))
                row.addWidget(sync_btn)

                row_widget = QFrame(self)
                row_widget.setLayout(row)
                row_widget.setFixedHeight(44)
                row_widget.setStyleSheet(f"""
                    QFrame {{
                        background: transparent;
                        border-bottom: 1px solid {_separator_color()};
                    }}
                """)
                cl2.addWidget(row_widget)

            self._content_layout.insertWidget(self._content_layout.count() - 1, section2)

    def _on_sync(self, skill_id: str, agent_name: str) -> None:
        success = self._service.sync_to_agent(skill_id, agent_name)
        if success:
            InfoBar.success("同步成功", f"已同步到 {agent_name}", parent=self, duration=2000)
        else:
            InfoBar.error("同步失败", f"同步到 {agent_name} 失败", parent=self, duration=2000)
        self._refresh_agents()


# ══════════════════════════════════════════════════════════
#  Settings View
# ══════════════════════════════════════════════════════════

class SettingsView(QWidget):
    """设置视图"""

    def __init__(self, service: SkillService, parent=None):
        super().__init__(parent)
        self._service = service
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = TitleLabel("设置", self)
        layout.addWidget(title)

        # 仓库路径
        repo_section = SectionCard("仓库路径", "技能中央库的存储位置", self)
        repo_row = QHBoxLayout()
        self._repo_path = QLineEdit(self)
        self._repo_path.setText(str(self._service._skills_root))
        self._repo_path.setFixedHeight(34)
        self._repo_path.setReadOnly(True)
        repo_row.addWidget(self._repo_path)
        browse_repo = PushButton("浏览", self)
        browse_repo.setFixedSize(60, 34)
        browse_repo.clicked.connect(self._browse_repo)
        repo_row.addWidget(browse_repo)
        repo_section.content_layout().addLayout(repo_row)
        layout.addWidget(repo_section)

        # 同步模式
        sync_section = SectionCard("同步模式", "将技能同步到 Agent 目录的方式", self)
        self._sync_combo = ComboBox(self)
        self._sync_combo.setFixedWidth(220)
        self._sync_combo.setFixedHeight(34)
        self._sync_combo.addItem("复制 (Copy) — 完整复制文件")
        self._sync_combo.addItem("符号链接 (Symlink) — 创建链接")
        self._sync_combo.setCurrentIndex(0)
        sync_section.content_layout().addWidget(self._sync_combo)
        layout.addWidget(sync_section)

        # Agent 列表
        agent_section = SectionCard("Agent 列表", "已配置的 AI 工具", self)
        agents = self._service.db.list_agents()
        for agent in agents:
            agent_row = QHBoxLayout()
            agent_row.addWidget(BodyLabel(agent.display_name, self))
            agent_row.addStretch()
            dir_label = CaptionLabel(agent.skills_dir, self)
            dir_label.setStyleSheet(f"color: {_text_muted()}; max-width: 200px;")
            agent_row.addWidget(dir_label)
            mode_label = CaptionLabel(f"同步: {agent.sync_mode}", self)
            mode_label.setStyleSheet(f"color: {_text_muted()};")
            agent_row.addWidget(mode_label)
            agent_section.content_layout().addLayout(agent_row)
        layout.addWidget(agent_section)

        # 活动日志
        log_section = SectionCard("最近活动", "安装/卸载/同步操作记录", self)
        activities = self._service.db.get_recent_activity(20)
        if not activities:
            no_log = CaptionLabel("暂无活动记录", self)
            no_log.setStyleSheet(f"color: {_text_muted()};")
            log_section.content_layout().addWidget(no_log)
        else:
            for act in activities:
                log_row = QHBoxLayout()
                time_label = CaptionLabel(act["timestamp"][:19], self)
                time_label.setStyleSheet(f"color: {_text_muted()};")
                log_row.addWidget(time_label)
                action_label = BodyLabel(act["action"], self)
                log_row.addWidget(action_label)
                if act["detail"]:
                    detail = CaptionLabel(act["detail"][:80], self)
                    detail.setStyleSheet(f"color: {_text_muted()};")
                    log_row.addWidget(detail)
                log_row.addStretch()
                log_section.content_layout().addLayout(log_row)
        layout.addWidget(log_section)

        layout.addStretch()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _browse_repo(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择仓库路径")
        if path:
            self._repo_path.setText(path)

    def refresh_theme(self) -> None:
        """主题切换时刷新所有样式"""
        for section in self.findChildren(SectionCard):
            section.refresh_theme()
        # 刷新所有带颜色的 CaptionLabel
        muted = _text_muted()
        for lbl in self.findChildren(CaptionLabel):
            ss = lbl.styleSheet()
            if "color" in ss:
                lbl.setStyleSheet(f"color: {muted};")


# ══════════════════════════════════════════════════════════
#  Main Widget
# ═════════════════════════════════════════════════════════

class SkillManagerWidget(QWidget):
    """SKILL Manager 主界面 — 左侧导航 + 右侧内容"""

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self._active_nav_key = "library"

        from core.utils import get_app_data_path
        data_root = Path(get_app_data_path("data"))
        self._service = SkillService(data_root)

        self._setup_ui()

        # 监听主题变化
        qconfig.themeChangedFinished.connect(
            lambda: QTimer.singleShot(0, self._on_theme_changed)
        )

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 左侧导航 ──
        nav = QWidget(self)
        nav.setFixedWidth(180)
        nav.setObjectName("navPanel")
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(6)

        nav_title = StrongBodyLabel("SKILL Manager", nav)
        nav_layout.addWidget(nav_title)
        nav_layout.addSpacing(16)

        self._nav_buttons: Dict[str, PushButton] = {}
        nav_items = [
            ("library", FIF.LIBRARY, "技能库"),
            ("global", FIF.GLOBE, "全局工作区"),
            ("settings", FIF.SETTING, "设置"),
        ]
        for key, icon, label in nav_items:
            btn = PushButton(label, nav)
            btn.setFixedHeight(38)
            btn.setMinimumWidth(140)
            btn.clicked.connect(lambda checked, k=key: self._switch_view(k))
            nav_layout.addWidget(btn)
            self._nav_buttons[key] = btn

        nav_layout.addStretch()
        main_layout.addWidget(nav)

        # 分隔线
        separator = QFrame(self)
        separator.setFixedWidth(1)
        separator.setObjectName("navSeparator")
        main_layout.addWidget(separator)

        # ── 右侧内容区 ──
        self._stack = QStackedWidget(self)
        main_layout.addWidget(self._stack, 1)

        self._library_view = LibraryView(self._service, self)
        self._global_view = GlobalWorkspaceView(self._service, self)
        self._settings_view = SettingsView(self._service, self)

        self._stack.addWidget(self._library_view)
        self._stack.addWidget(self._global_view)
        self._stack.addWidget(self._settings_view)

        self._switch_view("library")
        self._apply_nav_theme()

    def _switch_view(self, key: str) -> None:
        self._active_nav_key = key
        view_map = {"library": 0, "global": 1, "settings": 2}
        self._stack.setCurrentIndex(view_map.get(key, 0))
        self._apply_nav_theme(key)

    def _apply_nav_theme(self, active_key: str = "library") -> None:
        dark = isDarkTheme()
        nav_bg = _nav_bg()
        sep_color = _separator_color()

        self.findChild(QWidget, "navPanel").setStyleSheet(f"""
            QWidget#navPanel {{
                background-color: {nav_bg};
            }}
        """)
        self.findChild(QFrame, "navSeparator").setStyleSheet(f"""
            QFrame#navSeparator {{
                background-color: {sep_color};
            }}
        """)

        for k, btn in self._nav_buttons.items():
            if k == active_key:
                btn.setStyleSheet(f"""
                    PushButton {{
                        background-color: {_accent()};
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-weight: bold;
                        padding: 6px 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    PushButton {{
                        background-color: transparent;
                        color: {_text_primary()};
                        border: none;
                        border-radius: 6px;
                        padding: 6px 14px;
                    }}
                    PushButton:hover {{
                        background-color: {_nav_hover()};
                    }}
                """)

    def _on_theme_changed(self) -> None:
        """主题切换回调 — 刷新导航和所有子视图"""
        self._apply_nav_theme(self._active_nav_key)
        self._library_view.refresh_theme()
        self._global_view.refresh_theme()
        self._settings_view.refresh_theme()

    def closeEvent(self, event) -> None:
        self._service.close()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════
#  TabPageInterface
# ══════════════════════════════════════════════════════════

class SkillToolPage(TabPageInterface):
    page_id = "skill_manager"
    page_name = "SKILL 管理"
    page_icon = FIF.ROBOT

    @classmethod
    def create(cls, parent=None, core=None) -> QWidget:
        if core is not None:
            return SkillManagerWidget(core, parent)
        placeholder = QWidget(parent)
        layout = QVBoxLayout(placeholder)
        label = BodyLabel("加载中...", placeholder)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return placeholder
