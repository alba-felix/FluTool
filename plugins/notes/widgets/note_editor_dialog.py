from typing import Optional, List, Dict
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QComboBox, QTextEdit, QPushButton, QFileDialog, QSizePolicy, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QKeySequence
from qfluentwidgets import (
    MessageBoxBase, SubtitleLabel, LineEdit, TextEdit, ComboBox,
    PushButton, PrimaryPushButton, CaptionLabel, CardWidget, PillPushButton,
    ExpandLayout, SettingCardGroup, ExpandGroupSettingCard, InfoBar, InfoBarPosition,
)

from ..core.runtime import get_notes_runtime
from ..models.note import Note, CodeBlock
from ..services.category_service import CategoryService
from ..services.note_service import NoteService


class InputMethodFixMixin:
    """修复无边框窗口输入法位置问题的混入类"""
    
    def event(self, event):
        if event.type() == event.InputMethodUpdate:
            self.setAttribute(Qt.WA_InputMethodEnabled, True)
        return super().event(event)


class TextEditWithContextMenu(TextEdit):
    """带有中文右键菜单的文本编辑器"""
    
    def _can_undo(self) -> bool:
        return self.document().isUndoAvailable()
    
    def _can_redo(self) -> bool:
        return self.document().isRedoAvailable()
    
    def _has_selection(self) -> bool:
        return self.textCursor().hasSelection()
    
    def contextMenuEvent(self, event):
        menu = QMenu(self)

        undo_action = menu.addAction('撤销')
        undo_action.triggered.connect(self.undo)
        undo_action.setEnabled(self._can_undo())

        redo_action = menu.addAction('重做')
        redo_action.triggered.connect(self.redo)
        redo_action.setEnabled(self._can_redo())

        menu.addSeparator()

        cut_action = menu.addAction('剪切')
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(self._has_selection())

        copy_action = menu.addAction('复制')
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self._has_selection())

        paste_action = menu.addAction('粘贴')
        paste_action.triggered.connect(self.paste)
        paste_action.setEnabled(not self.isReadOnly())

        delete_action = menu.addAction('删除')
        delete_action.triggered.connect(self.textCursor().removeSelectedText)
        delete_action.setEnabled(self._has_selection())

        menu.addSeparator()

        select_all_action = menu.addAction('全选')
        select_all_action.triggered.connect(self.selectAll)

        menu.exec(event.globalPos())


class TagWidget(QWidget):
    tag_removed = pyqtSignal(str)

    def __init__(self, tag: str, parent=None):
        super().__init__(parent)
        self.tag = tag
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.tag_btn = PillPushButton(self.tag, self)
        self.tag_btn.setCheckable(False)
        layout.addWidget(self.tag_btn)

        self.remove_btn = QPushButton('\u00d7', self)
        self.remove_btn.setFixedSize(20, 20)
        self.remove_btn.setStyleSheet('''
            QPushButton {
                border: none;
                background: transparent;
                font-size: 14px;
                color: #888;
            }
            QPushButton:hover {
                color: #d00;
            }
        ''')
        self.remove_btn.clicked.connect(lambda: self.tag_removed.emit(self.tag))
        layout.addWidget(self.remove_btn)


class CodeBlockWidget(CardWidget):
    remove_clicked = pyqtSignal(object)

    def __init__(self, code_block: CodeBlock = None, parent=None):
        super().__init__(parent)
        self.code_block = code_block or CodeBlock(language='python', content='')
        self._highlighter = None
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self.language_combo = ComboBox()
        languages = ['python', 'java', 'javascript', 'typescript', 'c', 'cpp', 'go', 'rust', 'sql', 'html', 'css', 'json', 'xml', 'plaintext']
        self.language_combo.addItems(languages)
        self.language_combo.setCurrentText(self.code_block.language)
        header_layout.addWidget(QLabel('\u8bed\u8a00:'))
        header_layout.addWidget(self.language_combo)

        header_layout.addStretch()

        self.remove_btn = QPushButton('\u5220\u9664\u4ee3\u7801\u5757')
        self.remove_btn.setFixedHeight(28)
        self.remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self))
        header_layout.addWidget(self.remove_btn)

        layout.addLayout(header_layout)

        self.code_edit = TextEditWithContextMenu()
        self.code_edit.setPlainText(self.code_block.content)
        self.code_edit.setFont(QFont('Consolas', 10))
        self.code_edit.setPlaceholderText('\u5728\u6b64\u8f93\u5165\u4ee3\u7801...')
        self.code_edit.setAttribute(Qt.WA_InputMethodEnabled, True)
        layout.addWidget(self.code_edit)

        self._setup_highlighter()

    def _setup_highlighter(self):
        from ..highlighter.factory import HighlighterFactory
        language = self.language_combo.currentText()
        self._highlighter = HighlighterFactory.create(language, self.code_edit.document())

    def get_code_block(self) -> CodeBlock:
        return CodeBlock(
            language=self.language_combo.currentText(),
            content=self.code_edit.toPlainText()
        )


class NoteEditorDialog(MessageBoxBase):
    def __init__(
        self,
        note: Note = None,
        parent=None,
        current_category_id: int = None,
        note_service: NoteService = None,
        category_service: CategoryService = None,
    ):
        super().__init__(parent)
        runtime = get_notes_runtime()
        self._note = note
        self._current_category_id = current_category_id
        self._note_service = note_service or runtime.note_service
        self._category_service = category_service or runtime.category_service
        self._tags: List[str] = []
        self._code_block_widgets: List[CodeBlockWidget] = []
        self._images: List[str] = []
        self._init_ui()
        self._connect_signals()
        if note:
            self._load_note_data()

    def _init_ui(self):
        self.titleLabel = SubtitleLabel('\u7f16\u8f91\u7b14\u8bb0' if self._note else '\u65b0\u5efa\u7b14\u8bb0', self)
        self.viewLayout.addWidget(self.titleLabel)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(128, 128, 128, 0.4);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(128, 128, 128, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(0, 0, 8, 0)

        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel('\u6807\u9898:'))
        self.title_input = LineEdit()
        self.title_input.setPlaceholderText('\u8f93\u5165\u6807\u9898\uff08\u53ef\u9009\uff09')
        self.title_input.setClearButtonEnabled(True)
        title_layout.addWidget(self.title_input)
        scroll_layout.addLayout(title_layout)

        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel('\u5206\u7c7b:'))
        self.category_combo = ComboBox()
        self._refresh_categories()
        category_layout.addWidget(self.category_combo)

        self.manage_category_btn = PushButton('\u7ba1\u7406\u5206\u7c7b')
        self.manage_category_btn.setFixedHeight(32)
        category_layout.addWidget(self.manage_category_btn)
        category_layout.addStretch()
        scroll_layout.addLayout(category_layout)

        tags_label = QLabel('\u6807\u7b7e:')
        scroll_layout.addWidget(tags_label)

        tags_input_layout = QHBoxLayout()
        self.tag_input = LineEdit()
        self.tag_input.setPlaceholderText('\u8f93\u5165\u6807\u7b7e\u540e\u6309\u56de\u8f66\u6dfb\u52a0')
        self.tag_input.setClearButtonEnabled(True)
        tags_input_layout.addWidget(self.tag_input)
        scroll_layout.addLayout(tags_input_layout)

        self.tags_container = QWidget()
        self.tags_container.setStyleSheet("background: transparent;")
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(8)
        self.tags_layout.addStretch()
        scroll_layout.addWidget(self.tags_container)

        scroll_layout.addWidget(QLabel('\u5185\u5bb9:'))
        self.content_input = TextEditWithContextMenu()
        self.content_input.setPlaceholderText('\u8f93\u5165\u7b14\u8bb0\u5185\u5bb9\uff08\u5fc5\u586b\uff09')
        self.content_input.setFixedHeight(200)
        self.content_input.setAttribute(Qt.WA_InputMethodEnabled, True)
        scroll_layout.addWidget(self.content_input)

        code_header = QHBoxLayout()
        code_header.addWidget(QLabel('\u4ee3\u7801\u5757:'))
        code_header.addStretch()
        self.add_code_btn = PushButton('\u6dfb\u52a0\u4ee3\u7801\u5757')
        self.add_code_btn.setFixedHeight(32)
        code_header.addWidget(self.add_code_btn)
        scroll_layout.addLayout(code_header)

        self.code_blocks_container = QWidget()
        self.code_blocks_container.setStyleSheet("background: transparent;")
        self.code_blocks_layout = QVBoxLayout(self.code_blocks_container)
        self.code_blocks_layout.setContentsMargins(0, 0, 0, 0)
        self.code_blocks_layout.setSpacing(8)
        scroll_layout.addWidget(self.code_blocks_container)

        scroll_layout.addWidget(QLabel('\u5907\u6ce8:'))
        self.remarks_input = TextEditWithContextMenu()
        self.remarks_input.setPlaceholderText('\u8f93\u5165\u5907\u6ce8\uff08\u53ef\u9009\uff09')
        self.remarks_input.setFixedHeight(80)
        scroll_layout.addWidget(self.remarks_input)

        image_header = QHBoxLayout()
        image_header.addWidget(QLabel('\u56fe\u7247:'))
        image_header.addStretch()
        self.paste_image_btn = PushButton('\u7c98\u8d34\u56fe\u7247')
        self.paste_image_btn.setFixedHeight(32)
        image_header.addWidget(self.paste_image_btn)
        self.add_image_btn = PushButton('\u6dfb\u52a0\u56fe\u7247')
        self.add_image_btn.setFixedHeight(32)
        image_header.addWidget(self.add_image_btn)
        scroll_layout.addLayout(image_header)

        self.images_container = QWidget()
        self.images_container.setStyleSheet("background: transparent;")
        self.images_layout = QHBoxLayout(self.images_container)
        self.images_layout.setContentsMargins(0, 0, 0, 0)
        self.images_layout.setSpacing(8)
        self.images_layout.addStretch()
        scroll_layout.addWidget(self.images_container)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        self.viewLayout.addWidget(scroll)

        self.yesButton.setText('\u4fdd\u5b58')
        self.cancelButton.setText('\u53d6\u6d88')

        self.widget.setMinimumSize(800, 700)
        self.window().setMinimumSize(800, 700)

    def _connect_signals(self):
        self.tag_input.returnPressed.connect(self._add_tag)
        self.add_code_btn.clicked.connect(self._add_code_block)
        self.add_image_btn.clicked.connect(self._add_image)
        self.paste_image_btn.clicked.connect(self._paste_image)
        self.manage_category_btn.clicked.connect(self._on_manage_category)

    def _refresh_categories(self):
        categories = self._category_service.get_all() or []
        self.category_combo.clear()
        
        # 如果没有分类，什么都不选
        if not categories:
            return
        
        default_index = 0
        
        for i, category in enumerate(categories):
            self.category_combo.addItem(category.name or '未命名')
            idx = self.category_combo.count() - 1
            self.category_combo.setItemData(idx, category.id)
            
            # 如果是当前分类，设置为选中
            if self._current_category_id and category.id == self._current_category_id:
                default_index = i
        
        # 设置默认选中的分类
        if self.category_combo.count() > 0:
            self.category_combo.setCurrentIndex(default_index)

    def _on_manage_category(self):
        from .category_manager_dialog import CategoryManagerDialog
        dialog = CategoryManagerDialog(self, category_service=self._category_service)
        dialog.exec()
        self._refresh_categories()

    def _add_tag(self):
        tag = self.tag_input.text().strip()
        if not tag or tag in self._tags:
            self.tag_input.clear()
            return
        self._tags.append(tag)
        self._add_tag_widget(tag)
        self.tag_input.clear()

    def _add_tag_widget(self, tag: str):
        tag_widget = TagWidget(tag)
        tag_widget.tag_removed.connect(self._remove_tag)
        self.tags_layout.insertWidget(self.tags_layout.count() - 1, tag_widget)

    def _remove_tag(self, tag: str):
        if tag not in self._tags:
            return
        self._tags.remove(tag)
        for i in range(self.tags_layout.count()):
            item = self.tags_layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if isinstance(widget, TagWidget) and widget.tag == tag:
                widget.deleteLater()
                break

    def _add_code_block(self):
        code_widget = CodeBlockWidget()
        code_widget.remove_clicked.connect(self._remove_code_block)
        self._code_block_widgets.append(code_widget)
        self.code_blocks_layout.addWidget(code_widget)

    def _remove_code_block(self, widget: CodeBlockWidget):
        if widget in self._code_block_widgets:
            self._code_block_widgets.remove(widget)
        widget.deleteLater()

    def _add_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '\u9009\u62e9\u56fe\u7247', '',
            '\u56fe\u7247\u6587\u4ef6 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)'
        )
        if not file_path:
            return
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # 获取当前图片数量作为序号
            image_index = len(self._images)
            
            # 获取分类名称
            category_name = self.category_combo.currentText()
            
            # 生成文件名基础部分
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            prefix = category_name if category_name else 'untitled'
            prefix = ''.join(c for c in prefix if c.isalnum() or c in '_-')[:20]
            filename_base = f"{prefix}_{timestamp}"
            
            filename = self._note_service.save_image(image_data, category_name, filename_base, image_index)
            if filename:
                self._images.append(filename)
                self._add_image_thumbnail(filename)
        except Exception as e:
            print(f'\u6dfb\u52a0\u56fe\u7247\u5931\u8d25\uff1a{e}')

    def _paste_image(self):
        """从剪贴板粘贴图片"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        pixmap = clipboard.pixmap()
        
        if pixmap.isNull():
            InfoBar.warning(
                title='\u63d0\u793a',
                content='\u526a\u8d34\u677f\u4e2d\u6ca1\u6709\u56fe\u7247',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=1500,
                parent=self
            )
            return
        
        try:
            from datetime import datetime
            
            # 获取当前图片数量作为序号
            image_index = len(self._images)
            
            # 生成文件名基础部分（不含序号）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            category_name = self.category_combo.currentText()
            
            # 使用分类名称作为前缀
            prefix = category_name if category_name else 'untitled'
            prefix = ''.join(c for c in prefix if c.isalnum() or c in '_-')[:20]
            filename_base = f"{prefix}_{timestamp}"
            
            print(f'[DEBUG] \u7c98\u8d34\u56fe\u7247 - \u5206\u7c7b\uff1a{category_name}, \u6587\u4ef6\u540d\u57fa\u7840\uff1a{filename_base}, \u5e8f\u53f7\uff1a{image_index}')
            print(f'[DEBUG] Pixmap \u5c3a\u5bf8\uff1a{pixmap.width()}x{pixmap.height()}')
            
            # 保存图片（传递序号）
            saved_filename = self._note_service.save_image(pixmap, category_name, filename_base, image_index)
            
            if saved_filename:
                print(f'[DEBUG] \u56fe\u7247\u4fdd\u5b58\u6210\u529f\uff1a{saved_filename}')
                self._images.append(saved_filename)
                self._add_image_thumbnail(saved_filename)
                InfoBar.success(
                    title='\u6210\u529f',
                    content='\u56fe\u7247\u5df2\u7c98\u8d34',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=1500,
                    parent=self
                )
            else:
                print(f'[DEBUG] \u56fe\u7247\u4fdd\u5b58\u5931\u8d25\uff0c\u8fd4\u56de\u7a7a\u6587\u4ef6\u540d')
                InfoBar.error(
                    title='\u9519\u8bef',
                    content='\u4fdd\u5b58\u56fe\u7247\u5931\u8d25',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
        except Exception as e:
            import traceback
            error_msg = f'\u7c98\u8d34\u56fe\u7247\u5931\u8d25\uff1a{str(e)}\n{traceback.format_exc()}'
            print(error_msg)
            InfoBar.error(
                title='\u9519\u8bef',
                content=f'\u7c98\u8d34\u56fe\u7247\u5931\u8d25\uff1a{str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def _add_image_thumbnail(self, filename: str):
        if not filename:
            return
        image_path = self._note_service.get_image_path(filename)
        if image_path is None or not image_path.exists():
            return

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            return

        thumb_label = QLabel()
        thumb_label.setFixedSize(80, 80)
        thumb_label.setScaledContents(True)
        thumb_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        thumb_label.setStyleSheet('border: 1px solid #ccc; border-radius: 4px;')

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(thumb_label)

        remove_btn = QPushButton('\u00d7')
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet('''
            QPushButton {
                border: none;
                background: rgba(0,0,0,0.5);
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255,0,0,0.7);
            }
        ''')
        remove_btn.clicked.connect(lambda: self._remove_image(filename, container))

        self.images_layout.insertWidget(self.images_layout.count() - 1, container)

    def _remove_image(self, filename: str, container: QWidget):
        if filename in self._images:
            self._images.remove(filename)
        container.deleteLater()

    def _load_note_data(self):
        note = self._note
        if not note:
            return

        self.title_input.setText(note.title or '')

        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == note.category_id:
                self.category_combo.setCurrentIndex(i)
                break

        self._tags = (note.tags or []).copy()
        for tag in self._tags:
            self._add_tag_widget(tag)

        self.content_input.setPlainText(note.content or '')

        for code_block in note.code_blocks or []:
            code_widget = CodeBlockWidget(code_block)
            code_widget.remove_clicked.connect(self._remove_code_block)
            self._code_block_widgets.append(code_widget)
            self.code_blocks_layout.addWidget(code_widget)

        self.remarks_input.setPlainText(note.remarks or '')

        self._images = (note.images or []).copy()
        for filename in self._images:
            self._add_image_thumbnail(filename)

    def validate(self) -> bool:
        content = self.content_input.toPlainText().strip()
        return bool(content)

    def get_note_data(self) -> dict:
        category_id = self.category_combo.currentData()
        if category_id is not None:
            category_id = int(category_id)

        code_blocks = []
        for widget in self._code_block_widgets:
            try:
                cb = widget.get_code_block()
                code_blocks.append(cb.to_dict())
            except Exception:
                pass

        return {
            'title': self.title_input.text().strip(),
            'content': self.content_input.toPlainText().strip(),
            'category_id': category_id,
            'tags': self._tags.copy(),
            'code_blocks': code_blocks,
            'remarks': self.remarks_input.toPlainText().strip(),
            'images': self._images.copy()
        }
