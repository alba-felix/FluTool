"""翻译管理标签页"""

from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QSplitter, QStackedWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    FluentIcon as FIF,
    PushButton, TransparentToolButton, StrongBodyLabel,
    ComboBox, LineEdit, InfoBar, InfoBarPosition,
    TextEdit as FluentTextEdit, SegmentedWidget, ListWidget,
    CardWidget, CheckBox
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

    def set_input_text(self, text: str) -> None:
        """设置输入文本（供历史记录调用）"""
        self._input_edit.setPlainText(text)
        self._input_edit.setFocus()


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
        self._word_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._word_list.customContextMenuRequested.connect(self._on_word_context_menu)
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
        """添加新单词"""
        from qfluentwidgets import MessageBoxBase, LineEdit, TextEdit
        from PyQt5.QtWidgets import QVBoxLayout, QLabel

        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("添加单词")
        dialog.yesButtonText = "添加"
        dialog.cancelButtonText = "取消"

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 单词输入
        word_label = QLabel("单词:")
        layout.addWidget(word_label)
        word_edit = LineEdit()
        word_edit.setPlaceholderText("输入英文单词")
        layout.addWidget(word_edit)

        # 翻译输入
        trans_label = QLabel("翻译:")
        layout.addWidget(trans_label)
        trans_edit = LineEdit()
        trans_edit.setPlaceholderText("输入中文翻译")
        layout.addWidget(trans_edit)

        # 备注输入
        notes_label = QLabel("备注(可选):")
        layout.addWidget(notes_label)
        notes_edit = TextEdit()
        notes_edit.setPlaceholderText("添加备注信息...")
        notes_edit.setMaximumHeight(80)
        layout.addWidget(notes_edit)

        dialog.viewLayout.addLayout(layout)
        dialog.widget.setMinimumWidth(350)

        if dialog.exec():
            word = word_edit.text().strip()
            translation = trans_edit.text().strip()
            notes = notes_edit.toPlainText().strip()

            if not word or not translation:
                InfoBar.warning(title="提示", content="单词和翻译不能为空",
                              orient=Qt.Horizontal, isClosable=True,
                              position=InfoBarPosition.TOP, duration=2000, parent=self)
                return

            try:
                with self._db.get_connection() as conn:
                    conn.execute(
                        "INSERT INTO vocabulary (word, translation, notes, source_lang, target_lang) VALUES (?, ?, ?, 'en', 'zh')",
                        (word, translation, notes)
                    )
                    conn.commit()

                InfoBar.success(title="添加成功", content=f"已添加单词: {word}",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=2000, parent=self)
                self._load_data()
            except Exception as e:
                InfoBar.error(title="添加失败", content=str(e),
                             orient=Qt.Horizontal, isClosable=True,
                             position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_edit_word(self, item) -> None:
        """编辑单词"""
        from qfluentwidgets import MessageBoxBase, LineEdit, TextEdit
        from PyQt5.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, PushButton

        record_id = item.data(Qt.UserRole)

        # 获取当前数据
        try:
            with self._db.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT word, translation, notes FROM vocabulary WHERE id = ?",
                    (record_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return
                current_word, current_translation, current_notes = row
        except Exception as e:
            print(f"[Vocabulary] Error fetching word: {e}")
            return

        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("编辑单词")
        dialog.yesButtonText = "保存"
        dialog.cancelButtonText = "取消"

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 单词输入
        word_label = QLabel("单词:")
        layout.addWidget(word_label)
        word_edit = LineEdit()
        word_edit.setText(current_word)
        layout.addWidget(word_edit)

        # 翻译输入
        trans_label = QLabel("翻译:")
        layout.addWidget(trans_label)
        trans_edit = LineEdit()
        trans_edit.setText(current_translation)
        layout.addWidget(trans_edit)

        # 备注输入
        notes_label = QLabel("备注(可选):")
        layout.addWidget(notes_label)
        notes_edit = TextEdit()
        notes_edit.setText(current_notes or "")
        notes_edit.setMaximumHeight(80)
        layout.addWidget(notes_edit)

        dialog.viewLayout.addLayout(layout)
        dialog.widget.setMinimumWidth(350)

        if dialog.exec():
            word = word_edit.text().strip()
            translation = trans_edit.text().strip()
            notes = notes_edit.toPlainText().strip()

            if not word or not translation:
                InfoBar.warning(title="提示", content="单词和翻译不能为空",
                              orient=Qt.Horizontal, isClosable=True,
                              position=InfoBarPosition.TOP, duration=2000, parent=self)
                return

            try:
                with self._db.get_connection() as conn:
                    conn.execute(
                        "UPDATE vocabulary SET word = ?, translation = ?, notes = ? WHERE id = ?",
                        (word, translation, notes, record_id)
                    )
                    conn.commit()

                InfoBar.success(title="更新成功", content=f"已更新单词: {word}",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=2000, parent=self)
                self._load_data()
            except Exception as e:
                InfoBar.error(title="更新失败", content=str(e),
                             orient=Qt.Horizontal, isClosable=True,
                             position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_delete_word(self, item) -> None:
        """删除单词"""
        from qfluentwidgets import MessageBox

        record_id = item.data(Qt.UserRole)
        word = item.text().split(" - ")[0]

        box = MessageBox("确认删除", f"确定要删除单词 \"{word}\" 吗？", self)
        if box.exec():
            try:
                with self._db.get_connection() as conn:
                    conn.execute("DELETE FROM vocabulary WHERE id = ?", (record_id,))
                    conn.commit()

                InfoBar.success(title="删除成功", content=f"已删除单词: {word}",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=2000, parent=self)
                self._load_data()
            except Exception as e:
                InfoBar.error(title="删除失败", content=str(e),
                             orient=Qt.Horizontal, isClosable=True,
                             position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_word_context_menu(self, pos) -> None:
        """单词列表右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction
        from qfluentwidgets import isDarkTheme

        item = self._word_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        
        # 根据当前主题设置样式
        dark = isDarkTheme()
        if dark:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 4px;
                    color: #ffffff;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 2px;
                    color: #ffffff;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 120, 215, 0.3);
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    padding: 4px;
                    color: #333333;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 2px;
                    color: #333333;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 120, 215, 0.15);
                }
            """)

        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self._on_edit_word(item))
        menu.addAction(edit_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._on_delete_word(item))
        menu.addAction(delete_action)

        menu.exec_(self._word_list.mapToGlobal(pos))


class HistoryPanel(QWidget):
    """历史记录面板"""

    # 信号：点击历史记录时发送数据到翻译面板
    history_selected = pyqtSignal(str, str, str, str)  # source_text, target_text, source_lang, target_lang

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = DatabaseManager()
        self._selected_items: List[QListWidgetItem] = []
        self._setup_ui()
        QTimer.singleShot(100, self._load_data)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 筛选栏
        filter_bar = QHBoxLayout()
        
        title = StrongBodyLabel("翻译历史", self)
        filter_bar.addWidget(title)
        
        # 语言筛选
        self._lang_filter = ComboBox(self)
        self._lang_filter.addItems(["全部语言", "中文→英语", "英语→中文", "自动→中文", "其他"])
        self._lang_filter.setFixedWidth(120)
        self._lang_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self._lang_filter)
        
        # 日期筛选
        self._date_filter = ComboBox(self)
        self._date_filter.addItems(["全部时间", "今天", "最近7天", "最近30天"])
        self._date_filter.setFixedWidth(100)
        self._date_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_bar.addWidget(self._date_filter)

        filter_bar.addStretch()

        self._search_edit = LineEdit(self)
        self._search_edit.setPlaceholderText("搜索历史...")
        self._search_edit.setFixedWidth(150)
        self._search_edit.textChanged.connect(self._on_search)
        filter_bar.addWidget(self._search_edit)

        layout.addLayout(filter_bar)
        
        # 批量操作栏
        batch_bar = QHBoxLayout()
        
        self._select_all_cb = CheckBox("全选", self)
        self._select_all_cb.stateChanged.connect(self._on_select_all)
        batch_bar.addWidget(self._select_all_cb)
        
        self._batch_delete_btn = PushButton("批量删除", self)
        self._batch_delete_btn.setFixedHeight(28)
        self._batch_delete_btn.clicked.connect(self._on_batch_delete)
        batch_bar.addWidget(self._batch_delete_btn)
        
        self._clear_btn = PushButton("清空全部", self)
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.clicked.connect(self._on_clear)
        batch_bar.addWidget(self._clear_btn)
        
        batch_bar.addStretch()
        layout.addLayout(batch_bar)

        self._history_list = ListWidget(self)
        self._history_list.setSelectionMode(ListWidget.MultiSelection)  # 允许多选
        self._history_list.itemClicked.connect(self._on_item_click)
        self._history_list.itemDoubleClicked.connect(self._on_item_double_click)
        self._history_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._history_list.customContextMenuRequested.connect(self._on_history_context_menu)
        layout.addWidget(self._history_list, 1)

    def _load_data(self) -> None:
        """加载历史数据"""
        self._history_list.clear()
        self._selected_items.clear()
        self._select_all_cb.setChecked(False)
        
        try:
            # 构建查询条件
            lang_filter = self._lang_filter.currentText()
            date_filter = self._date_filter.currentText()
            
            query = "SELECT id, source_text, target_text, source_lang, target_lang, created_at FROM translation_history WHERE 1=1"
            params = []
            
            # 语言筛选
            if lang_filter == "中文→英语":
                query += " AND source_lang = '中文' AND target_lang = '英语'"
            elif lang_filter == "英语→中文":
                query += " AND source_lang = '英语' AND target_lang = '中文'"
            elif lang_filter == "自动→中文":
                query += " AND source_lang = '自动检测' AND target_lang = '中文'"
            elif lang_filter == "其他":
                query += " AND source_lang NOT IN ('中文', '英语', '自动检测')"
            
            # 日期筛选
            if date_filter == "今天":
                query += " AND date(created_at) = date('now')"
            elif date_filter == "最近7天":
                query += " AND created_at >= datetime('now', '-7 days')"
            elif date_filter == "最近30天":
                query += " AND created_at >= datetime('now', '-30 days')"
            
            query += " ORDER BY id DESC LIMIT 100"
            
            with self._db.get_connection() as conn:
                cursor = conn.execute(query, params)
                for row in cursor.fetchall():
                    record_id, source_text, target_text, source_lang, target_lang, created_at = row
                    display = f"[{source_lang}→{target_lang}] {source_text} → {target_text}"
                    item = QListWidgetItem(display)
                    item.setData(Qt.UserRole, record_id)
                    item.setData(Qt.UserRole + 1, source_text)
                    item.setData(Qt.UserRole + 2, target_text)
                    item.setData(Qt.UserRole + 3, source_lang)
                    item.setData(Qt.UserRole + 4, target_lang)
                    item.setToolTip(f"原文: {source_text}\n译文: {target_text}\n时间: {created_at}")
                    self._history_list.addItem(item)
        except Exception as e:
            print(f"[History] Error loading data: {e}")

    def _on_filter_changed(self) -> None:
        """筛选条件变化时重新加载"""
        self._load_data()

    def _on_search(self, text: str) -> None:
        """搜索历史记录"""
        for i in range(self._history_list.count()):
            item = self._history_list.item(i)
            item.setHidden(text.lower() not in item.text().lower() if text else False)

    def _on_select_all(self, state: int) -> None:
        """全选/取消全选"""
        if state == Qt.Checked:
            self._history_list.selectAll()
        else:
            self._history_list.clearSelection()

    def _on_batch_delete(self) -> None:
        """批量删除"""
        from qfluentwidgets import MessageBox
        
        selected_items = self._history_list.selectedItems()
        if not selected_items:
            InfoBar.warning(title="提示", content="请先选择要删除的历史记录",
                          orient=Qt.Horizontal, isClosable=True,
                          position=InfoBarPosition.TOP, duration=2000, parent=self)
            return

        box = MessageBox("确认删除", f"确定要删除选中的 {len(selected_items)} 条历史记录吗？", self)
        if box.exec():
            try:
                with self._db.get_connection() as conn:
                    for item in selected_items:
                        record_id = item.data(Qt.UserRole)
                        conn.execute("DELETE FROM translation_history WHERE id = ?", (record_id,))
                    conn.commit()

                InfoBar.success(title="删除成功", content=f"已删除 {len(selected_items)} 条历史记录",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=2000, parent=self)
                self._load_data()
            except Exception as e:
                InfoBar.error(title="删除失败", content=str(e),
                             orient=Qt.Horizontal, isClosable=True,
                             position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_clear(self) -> None:
        """清空全部历史"""
        from qfluentwidgets import MessageBox
        
        box = MessageBox("确认清空", "确定要清空所有历史记录吗？此操作不可恢复。", self)
        if box.exec():
            try:
                with self._db.get_connection() as conn:
                    conn.execute("DELETE FROM translation_history")
                    conn.commit()
                self._load_data()
                InfoBar.success(title="已清空", content="历史记录已清空",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=1500, parent=self)
            except Exception as e:
                print(f"[History] Error clearing: {e}")

    def _on_item_click(self, item) -> None:
        """单击选中/取消选中"""
        pass

    def _on_item_double_click(self, item) -> None:
        """双击填充到翻译面板"""
        source_text = item.data(Qt.UserRole + 1)
        target_text = item.data(Qt.UserRole + 2)
        source_lang = item.data(Qt.UserRole + 3)
        target_lang = item.data(Qt.UserRole + 4)
        
        # 发送信号到翻译面板
        self.history_selected.emit(source_text, target_text, source_lang, target_lang)
        
        # 切换到翻译标签
        parent = self.parent()
        if parent and hasattr(parent, '_tab_bar'):
            parent._tab_bar.setCurrentItem("translate")

    def _on_add_to_vocabulary(self, item) -> None:
        """添加到单词本 - 弹出编辑对话框"""
        from qfluentwidgets import MessageBoxBase, LineEdit, TextEdit
        from PyQt5.QtWidgets import QVBoxLayout, QLabel

        source_text = item.data(Qt.UserRole + 1)
        target_text = item.data(Qt.UserRole + 2)

        dialog = MessageBoxBase(self)
        dialog.setWindowTitle("添加到单词本")
        dialog.yesButtonText = "添加"
        dialog.cancelButtonText = "取消"

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 显示原文（只读）
        source_label = QLabel("原文:")
        layout.addWidget(source_label)
        source_display = TextEdit()
        source_display.setPlainText(source_text)
        source_display.setReadOnly(True)
        source_display.setMaximumHeight(60)
        layout.addWidget(source_display)

        # 单词输入（使用完整原文，可编辑）
        word_label = QLabel("单词 (可编辑):")
        layout.addWidget(word_label)
        word_edit = LineEdit()
        # 使用完整原文作为默认值，用户可以修改
        word_edit.setText(source_text.strip())
        layout.addWidget(word_edit)

        # 翻译输入（使用完整译文）
        trans_label = QLabel("翻译 (可编辑):")
        layout.addWidget(trans_label)
        trans_edit = TextEdit()
        trans_edit.setPlainText(target_text)
        trans_edit.setMaximumHeight(80)
        layout.addWidget(trans_edit)

        # 备注输入
        notes_label = QLabel("备注(可选):")
        layout.addWidget(notes_label)
        notes_edit = LineEdit()
        notes_edit.setPlaceholderText("添加备注信息...")
        layout.addWidget(notes_edit)

        dialog.viewLayout.addLayout(layout)
        dialog.widget.setMinimumWidth(400)
        dialog.widget.setMinimumHeight(350)

        if dialog.exec():
            word = word_edit.text().strip()
            translation = trans_edit.toPlainText().strip()
            notes = notes_edit.text().strip()

            if not word or not translation:
                InfoBar.warning(title="提示", content="单词和翻译不能为空",
                              orient=Qt.Horizontal, isClosable=True,
                              position=InfoBarPosition.TOP, duration=2000, parent=self)
                return

            try:
                with self._db.get_connection() as conn:
                    # 检查是否已存在
                    cursor = conn.execute("SELECT id FROM vocabulary WHERE word = ?", (word,))
                    if cursor.fetchone():
                        InfoBar.info(title="提示", content=f"单词 \"{word}\" 已存在于单词本",
                                    orient=Qt.Horizontal, isClosable=True,
                                    position=InfoBarPosition.TOP, duration=2000, parent=self)
                        return

                    conn.execute(
                        "INSERT INTO vocabulary (word, translation, notes, source_lang, target_lang) VALUES (?, ?, ?, 'en', 'zh')",
                        (word, translation, notes if notes else f"来自历史记录")
                    )
                    conn.commit()

                InfoBar.success(title="添加成功", content=f"已添加单词到单词本: {word}",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=2000, parent=self)
            except Exception as e:
                InfoBar.error(title="添加失败", content=str(e),
                             orient=Qt.Horizontal, isClosable=True,
                             position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_delete_single(self, item) -> None:
        """删除单条历史"""
        from qfluentwidgets import MessageBox
        
        record_id = item.data(Qt.UserRole)
        source_text = item.data(Qt.UserRole + 1)
        
        box = MessageBox("确认删除", f"确定要删除这条历史记录吗？\n{source_text[:30]}...", self)
        if box.exec():
            try:
                with self._db.get_connection() as conn:
                    conn.execute("DELETE FROM translation_history WHERE id = ?", (record_id,))
                    conn.commit()

                InfoBar.success(title="删除成功", content="已删除历史记录",
                               orient=Qt.Horizontal, isClosable=True,
                               position=InfoBarPosition.TOP, duration=1500, parent=self)
                self._load_data()
            except Exception as e:
                InfoBar.error(title="删除失败", content=str(e),
                             orient=Qt.Horizontal, isClosable=True,
                             position=InfoBarPosition.TOP, duration=3000, parent=self)

    def _on_history_context_menu(self, pos) -> None:
        """历史记录右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction
        from qfluentwidgets import isDarkTheme

        item = self._history_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        
        # 根据当前主题设置样式
        dark = isDarkTheme()
        if dark:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 4px;
                    color: #ffffff;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 2px;
                    color: #ffffff;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 120, 215, 0.3);
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    padding: 4px;
                    color: #333333;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 2px;
                    color: #333333;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 120, 215, 0.15);
                }
            """)

        use_action = QAction("使用此翻译", self)
        use_action.triggered.connect(lambda: self._on_item_double_click(item))
        menu.addAction(use_action)

        add_vocab_action = QAction("添加到单词本", self)
        add_vocab_action.triggered.connect(lambda: self._on_add_to_vocabulary(item))
        menu.addAction(add_vocab_action)

        menu.addSeparator()

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._on_delete_single(item))
        menu.addAction(delete_action)

        menu.exec_(self._history_list.mapToGlobal(pos))


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
        
        # 连接历史记录信号到翻译面板
        self._history_panel.history_selected.connect(self._on_history_selected)

        self._stack.addWidget(self._translate_panel)
        self._stack.addWidget(self._vocabulary_panel)
        self._stack.addWidget(self._history_panel)

    def _on_history_selected(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> None:
        """历史记录选中时填充到翻译面板"""
        self._translate_panel.set_input_text(source_text)
        # 设置语言
        if source_lang in ["中文", "英语", "自动检测"]:
            self._translate_panel._source_lang_combo.setCurrentText(source_lang)
        if target_lang in ["中文", "英语"]:
            self._translate_panel._target_lang_combo.setCurrentText(target_lang)

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
