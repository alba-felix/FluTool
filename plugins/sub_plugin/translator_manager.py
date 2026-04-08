"""翻译管理标签页"""

from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QSplitter, QStackedWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    FluentIcon as FIF,
    PushButton, TransparentToolButton, StrongBodyLabel,
    ComboBox, LineEdit, InfoBar, InfoBarPosition,
    TextEdit as FluentTextEdit, SegmentedWidget, ListWidget,
    CardWidget
)

from storage import DatabaseManager

from .page_interface import TabPageInterface
from .translation_service import get_translation_service, reset_translation_service


class TranslatePanel(QWidget):
    """翻译面板 - 主翻译界面"""

    # 自动翻译延迟(毫秒)
    AUTO_TRANSLATE_DELAY = 1100

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        # 重置翻译服务以确保使用最新配置
        self._translation_service = reset_translation_service()
        self._auto_translate_timer = QTimer(self)
        self._auto_translate_timer.setSingleShot(True)
        self._auto_translate_timer.timeout.connect(self._on_translate)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        lang_bar = QWidget(self)
        lang_bar.setFixedHeight(40)
        lang_layout = QHBoxLayout(lang_bar)
        lang_layout.setContentsMargins(10, 5, 10, 5)
        lang_layout.setSpacing(8)

        self._source_lang_combo = ComboBox(self)
        self._source_lang_combo.addItems(["自动检测", "中文", "英语"])
        self._source_lang_combo.setFixedWidth(120)
        lang_layout.addWidget(self._source_lang_combo)

        self._swap_btn = TransparentToolButton(FIF.SYNC, self)
        self._swap_btn.setFixedSize(28, 28)
        self._swap_btn.setToolTip("交换语言")
        self._swap_btn.clicked.connect(self._on_swap_lang)
        lang_layout.addWidget(self._swap_btn)

        self._target_lang_combo = ComboBox(self)
        self._target_lang_combo.addItems(["中文", "英语"])
        self._target_lang_combo.setCurrentIndex(0)
        self._target_lang_combo.setFixedWidth(120)
        lang_layout.addWidget(self._target_lang_combo)

        lang_layout.addStretch()

        self._translate_btn = PushButton("翻译", self)
        self._translate_btn.setFixedHeight(32)
        self._translate_btn.setIcon(FIF.SEND)
        self._translate_btn.clicked.connect(self._on_translate)
        lang_layout.addWidget(self._translate_btn)

        layout.addWidget(lang_bar)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setHandleWidth(1)

        left_frame = QFrame(self)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 5, 5, 10)
        left_layout.setSpacing(4)

        input_header = QHBoxLayout()
        input_label = QLabel("原文", self)
        input_label.setStyleSheet("color: #888; font-size: 12px;")
        input_header.addWidget(input_label)
        input_header.addStretch()

        self._paste_btn = TransparentToolButton(FIF.PASTE, self)
        self._paste_btn.setFixedSize(24, 24)
        self._paste_btn.setToolTip("粘贴")
        self._paste_btn.clicked.connect(self._on_paste)
        input_header.addWidget(self._paste_btn)

        self._clear_input_btn = TransparentToolButton(FIF.CANCEL, self)
        self._clear_input_btn.setFixedSize(24, 24)
        self._clear_input_btn.setToolTip("清空")
        self._clear_input_btn.clicked.connect(self._on_clear_input)
        input_header.addWidget(self._clear_input_btn)

        left_layout.addLayout(input_header)

        self._input_edit = FluentTextEdit(self)
        self._input_edit.setPlaceholderText("请输入要翻译的文本...")
        self._input_edit.setFont(QFont("Microsoft YaHei", 11))
        # 文本变化时启动自动翻译定时器
        self._input_edit.textChanged.connect(self._on_input_changed)
        left_layout.addWidget(self._input_edit)

        splitter.addWidget(left_frame)

        right_frame = QFrame(self)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(5, 5, 10, 10)
        right_layout.setSpacing(4)

        output_header = QHBoxLayout()
        output_label = QLabel("译文", self)
        output_label.setStyleSheet("color: #888; font-size: 12px;")
        output_header.addWidget(output_label)
        output_header.addStretch()

        self._copy_btn = TransparentToolButton(FIF.COPY, self)
        self._copy_btn.setFixedSize(24, 24)
        self._copy_btn.setToolTip("复制")
        self._copy_btn.clicked.connect(self._on_copy)
        output_header.addWidget(self._copy_btn)

        right_layout.addLayout(output_header)

        self._output_edit = FluentTextEdit(self)
        self._output_edit.setPlaceholderText("翻译结果将显示在这里...")
        self._output_edit.setFont(QFont("Microsoft YaHei", 11))
        self._output_edit.setReadOnly(True)
        right_layout.addWidget(self._output_edit)

        splitter.addWidget(right_frame)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter, 1)

    def _on_swap_lang(self) -> None:
        source_idx = self._source_lang_combo.currentIndex()
        target_idx = self._target_lang_combo.currentIndex()

        if source_idx == 0:
            InfoBar.warning(title="提示", content="自动检测语言无法作为目标语言",
                          orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        # 源语言索引1=中文,2=英语; 目标语言索引0=中文,1=英语
        self._source_lang_combo.setCurrentIndex(target_idx + 1)
        self._target_lang_combo.setCurrentIndex(source_idx - 1)

    def _on_translate(self) -> None:
        source_text = self._input_edit.toPlainText().strip()
        if not source_text:
            InfoBar.warning(title="提示", content="请输入要翻译的文本",
                          orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        source_lang = self._source_lang_combo.currentText()
        target_lang = self._target_lang_combo.currentText()

        # 使用翻译服务
        translated_text, source = self._translation_service.translate(
            source_text, source_lang, target_lang
        )

        self._output_edit.setPlainText(translated_text)
        self._save_to_history(source_text, translated_text, source_lang, target_lang)

        # 根据翻译来源显示不同提示
        if source == "local":
            InfoBar.success(
                title="本地翻译完成",
                content="已从本地词典获取翻译结果",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
        elif source == "api":
            InfoBar.info(
                title="有道API翻译",
                content="使用有道在线翻译服务",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

    def _save_to_history(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> None:
        try:
            with self._db.get_connection() as conn:
                conn.execute('''INSERT INTO translation_history 
                    (source_text, target_text, source_lang, target_lang) VALUES (?, ?, ?, ?)''',
                    (source_text, target_text, source_lang, target_lang))
                conn.commit()
        except Exception as e:
            print(f"[Translator] Error saving history: {e}")

    def _on_input_changed(self) -> None:
        """输入文本变化时启动自动翻译定时器"""
        text = self._input_edit.toPlainText().strip()
        if not text:
            return

        # 如果光标在输入框中，启动自动翻译定时器
        if self._input_edit.hasFocus():
            self._auto_translate_timer.start(self.AUTO_TRANSLATE_DELAY)

    def _on_paste(self) -> None:
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            self._input_edit.setPlainText(text)

    def _on_clear_input(self) -> None:
        self._input_edit.clear()
        self._auto_translate_timer.stop()

    def _on_copy(self) -> None:
        text = self._output_edit.toPlainText()
        if text:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            InfoBar.success(title="已复制", content="翻译结果已复制到剪贴板",
                           orient=Qt.Horizontal, isClosable=True,
                           position=InfoBarPosition.TOP, duration=1500, parent=self)


class VocabularyPanel(QWidget):
    """单词本面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._setup_ui()
        QTimer.singleShot(100, self._load_data)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = StrongBodyLabel("我的单词本", self)
        header.addWidget(title)
        header.addStretch()

        self._search_edit = LineEdit(self)
        self._search_edit.setPlaceholderText("搜索单词...")
        self._search_edit.setFixedWidth(200)
        self._search_edit.textChanged.connect(self._on_search)
        header.addWidget(self._search_edit)

        self._add_btn = PushButton("添加单词", self)
        self._add_btn.setFixedHeight(32)
        self._add_btn.setIcon(FIF.ADD_TO)
        self._add_btn.clicked.connect(self._on_add_word)
        header.addWidget(self._add_btn)

        layout.addLayout(header)

        self._word_list = ListWidget(self)
        self._word_list.itemDoubleClicked.connect(self._on_edit_word)
        layout.addWidget(self._word_list, 1)

    def _load_data(self) -> None:
        self._word_list.clear()
        try:
            with self._db.get_connection() as conn:
                cursor = conn.execute("SELECT id, word, translation FROM vocabulary ORDER BY id DESC LIMIT 100")
                for row in cursor.fetchall():
                    record_id, word, translation = row
                    item = QListWidgetItem(f"{word} - {translation}")
                    item.setData(Qt.UserRole, record_id)
                    self._word_list.addItem(item)
        except Exception as e:
            print(f"[Vocabulary] Error loading data: {e}")

    def _on_search(self, text: str) -> None:
        for i in range(self._word_list.count()):
            item = self._word_list.item(i)
            item.setHidden(text.lower() not in item.text().lower() if text else False)

    def _on_add_word(self) -> None:
        InfoBar.info(title="功能开发中", content="单词本添加功能即将上线",
                    orient=Qt.Horizontal, isClosable=True,
                    position=InfoBarPosition.TOP, duration=2000, parent=self)

    def _on_edit_word(self, item) -> None:
        pass


class HistoryPanel(QWidget):
    """历史记录面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._setup_ui()
        QTimer.singleShot(100, self._load_data)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = StrongBodyLabel("翻译历史", self)
        header.addWidget(title)
        header.addStretch()

        self._search_edit = LineEdit(self)
        self._search_edit.setPlaceholderText("搜索历史...")
        self._search_edit.setFixedWidth(200)
        self._search_edit.textChanged.connect(self._on_search)
        header.addWidget(self._search_edit)

        self._clear_btn = PushButton("清空", self)
        self._clear_btn.setFixedHeight(32)
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)

        layout.addLayout(header)

        self._history_list = ListWidget(self)
        self._history_list.itemClicked.connect(self._on_item_click)
        layout.addWidget(self._history_list, 1)

    def _load_data(self) -> None:
        self._history_list.clear()
        try:
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT id, source_text, target_text, source_lang, target_lang FROM translation_history ORDER BY id DESC LIMIT 50"
                )
                for row in cursor.fetchall():
                    record_id, source_text, target_text, source_lang, target_lang = row
                    display = f"[{source_lang}→{target_lang}] {source_text[:20]}... → {target_text[:20]}..."
                    item = QListWidgetItem(display)
                    item.setData(Qt.UserRole, record_id)
                    self._history_list.addItem(item)
        except Exception as e:
            print(f"[History] Error loading data: {e}")

    def _on_search(self, text: str) -> None:
        for i in range(self._history_list.count()):
            item = self._history_list.item(i)
            item.setHidden(text.lower() not in item.text().lower() if text else False)

    def _on_clear(self) -> None:
        try:
            with self._db.get_connection() as conn:
                conn.execute("DELETE FROM translation_history")
                conn.commit()
            self._history_list.clear()
            InfoBar.success(title="已清空", content="历史记录已清空",
                           orient=Qt.Horizontal, isClosable=True,
                           position=InfoBarPosition.TOP, duration=1500, parent=self)
        except Exception as e:
            print(f"[History] Error clearing: {e}")

    def _on_item_click(self, item) -> None:
        pass


class TranslatorWidget(QWidget):
    """翻译管理器主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._setup_ui()
        QTimer.singleShot(100, self._init_table)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setObjectName("translatorView")
        self.setStyleSheet("QWidget#translatorView { background-color: transparent; }")

        # 二级标签栏
        self._tab_bar = SegmentedWidget(self)
        self._tab_bar.addItem("translate", "翻译")
        self._tab_bar.addItem("vocabulary", "单词本")
        self._tab_bar.addItem("history", "历史")
        self._tab_bar.currentItemChanged.connect(self._on_tab_changed)
        layout.addWidget(self._tab_bar)

        # 内容区域
        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack, 1)

        # 添加面板
        self._translate_panel = TranslatePanel(self)
        self._vocabulary_panel = VocabularyPanel(self)
        self._history_panel = HistoryPanel(self)

        self._stack.addWidget(self._translate_panel)
        self._stack.addWidget(self._vocabulary_panel)
        self._stack.addWidget(self._history_panel)

    def _init_table(self) -> None:
        """初始化数据库表"""
        try:
            with self._db.get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS translation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_text TEXT NOT NULL,
                        target_text TEXT NOT NULL,
                        source_lang TEXT DEFAULT 'auto',
                        target_lang TEXT DEFAULT 'en',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS vocabulary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word TEXT NOT NULL,
                        translation TEXT NOT NULL,
                        source_lang TEXT DEFAULT 'en',
                        target_lang TEXT DEFAULT 'zh',
                        notes TEXT DEFAULT '',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except Exception as e:
            print(f"[Translator] Error initializing table: {e}")

    def _on_tab_changed(self, routeKey: str) -> None:
        index_map = {"translate": 0, "vocabulary": 1, "history": 2}
        index = index_map.get(routeKey, 0)
        self._stack.setCurrentIndex(index)
        if index == 1:
            self._vocabulary_panel._load_data()
        elif index == 2:
            self._history_panel._load_data()


class TranslatorPage(TabPageInterface):
    """翻译页面"""

    page_id = "translator"
    page_name = "翻译"
    page_icon = FIF.LANGUAGE

    @classmethod
    def create(cls, parent=None) -> QWidget:
        return TranslatorWidget(parent)
