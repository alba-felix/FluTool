from PyQt5.QtWidgets import (
	QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget, QFileDialog,
)
from PyQt5.QtCore import QSize, Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QFont, QTextCharFormat, QColor, QSyntaxHighlighter, QIcon, QKeyEvent
from qfluentwidgets import BodyLabel, CaptionLabel, isDarkTheme, ToolTipFilter, FluentIcon as FIF, RoundMenu
from qfluentwidgets.common.icon import Action

from ..models.note import Note
from ..resources.styles.note_card_style import DARK_STYLE, LIGHT_STYLE
from ..highlighter.factory import HighlighterFactory
from ..highlighter.language_detector import detect_language
from ..core.custom_icon import CustomFluentIcon


class NoteCardTextEdit(QTextEdit):
    """笔记内容编辑框，右键菜单走 Fluent 风格圆角菜单"""

    def contextMenuEvent(self, event):
        menu = RoundMenu(parent=self)

        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        editable = not self.isReadOnly()

        undo_action = Action('撤销')
        undo_action.triggered.connect(self.undo)
        undo_action.setEnabled(self.document().isUndoAvailable())

        redo_action = Action('重做')
        redo_action.triggered.connect(self.redo)
        redo_action.setEnabled(self.document().isRedoAvailable())

        cut_action = Action(FIF.CUT, '剪切')
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(has_selection and editable)

        copy_action = Action(FIF.COPY, '复制')
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(has_selection)

        paste_action = Action(FIF.PASTE, '粘贴')
        paste_action.triggered.connect(self.paste)
        paste_action.setEnabled(editable)

        delete_action = Action(FIF.DELETE, '删除')
        delete_action.triggered.connect(cursor.removeSelectedText)
        delete_action.setEnabled(has_selection and editable)

        select_all_action = Action('全选')
        select_all_action.triggered.connect(self.selectAll)

        menu.addAction(undo_action)
        menu.addAction(redo_action)
        menu.addSeparator()
        menu.addAction(cut_action)
        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(select_all_action)

        menu.exec(event.globalPos())


class NoteCard(QFrame):
	"""笔记卡片组件 - 可展开式"""

	# 媒体文件扩展名常量
	MEDIA_EXTENSIONS = ['.mp3', '.mp4', '.wav', '.avi', '.mkv', '.flac', '.m4a', '.wmv', '.mov']
	
	edit_clicked = pyqtSignal(int)
	delete_clicked = pyqtSignal(int)
	favorite_clicked = pyqtSignal(int)
	archive_clicked = pyqtSignal(int)
	content_updated = pyqtSignal(int, str)
	
	def __init__(self, note: Note, parent=None):
		super().__init__(parent)
		self.note = note
		self.is_expanded = False
		self._height = 130
		self._note_manager = None
		self._preview_highlighter = None
		self._content_highlighter = None
		
		self._apply_style()
		self._init_ui()
		self._setup_animation()
		self._setup_preview_content()
		self._ensure_collapsed_state()
	
	def _apply_style(self):
		style = DARK_STYLE if isDarkTheme() else LIGHT_STYLE
		self.setStyleSheet(style)
	
	def update_style(self):
		"""更新样式（主题切换时调用）"""
		self._apply_style()
		self._update_button_styles()
	
	def _update_button_styles(self):
		"""根据当前主题更新所有按钮的内联样式"""
		common_style = """
			QPushButton {
				background-color: transparent;
				border: none;
				border-radius: 4px;
				padding: 2px;
			}
		"""
		hover_style = """
			QPushButton:hover {
				background-color: %s;
			}
		"""
		hover_color = "rgba(255, 255, 255, 0.1)" if isDarkTheme() else "rgba(0, 0, 0, 0.05)"
		save_hover = "rgba(0, 120, 212, 0.2)" if isDarkTheme() else "rgba(0, 120, 212, 0.1)"
		delete_hover = "rgba(255, 107, 107, 0.2)" if isDarkTheme() else "rgba(211, 47, 47, 0.1)"
		
		self.expand_button.setIcon(QIcon(CustomFluentIcon.EXPAND.icon()))
		self.save_button.setIcon(QIcon(CustomFluentIcon.SAVE.icon()))
		self.edit_button.setIcon(QIcon(CustomFluentIcon.EDIT.icon()))
		self.code_button.setIcon(QIcon(CustomFluentIcon.CODE.icon()))
		self.images_button.setIcon(QIcon(CustomFluentIcon.IMAGE.icon()))
		self._update_favorite_button()
		self._update_archive_button()
		self.delete_button.setIcon(QIcon(CustomFluentIcon.DELETE.icon()))
		
		hover_color = "rgba(255, 255, 255, 0.1)" if isDarkTheme() else "rgba(0, 0, 0, 0.05)"
		for btn in [self.expand_button, self.edit_button, self.favorite_button,
					self.archive_button, self.code_button, self.images_button]:
			btn.setStyleSheet(common_style + hover_style % hover_color)
		
		self.save_button.setStyleSheet(common_style + hover_style % save_hover)
		self.delete_button.setStyleSheet(common_style + hover_style % delete_hover)
	
	def _init_ui(self):
		self.setFrameStyle(QFrame.StyledPanel)
		self.setLineWidth(1)
		
		layout = QVBoxLayout(self)
		layout.setSpacing(10)
		layout.setContentsMargins(15, 15, 15, 0)
		
		top_widget = QWidget()
		top_layout = QVBoxLayout(top_widget)
		top_layout.setSpacing(5)
		top_layout.setContentsMargins(0, 0, 0, 0)
		
		title_layout = QHBoxLayout()
		
		self.title_label = QLabel(self.note.title or '无标题')
		self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
		self.title_label.setObjectName("card_title")
		
		self.category_label = CaptionLabel(self.note.category_name or '未分类')
		self.category_label.setObjectName("card_category")
		
		self.create_time_label = CaptionLabel(self._get_relative_time())
		self.create_time_label.setObjectName("card_create_time")
		
		self.export_pdf_button = QPushButton()
		self.export_pdf_button.setObjectName("card_export_pdf_button")
		self.export_pdf_button.setIcon(QIcon(CustomFluentIcon.EXPORT.icon()))
		self.export_pdf_button.setFixedSize(24, 24)
		self.export_pdf_button.setIconSize(QSize(14, 14))
		self.export_pdf_button.setToolTip("导出 TXT")
		self.export_pdf_button.installEventFilter(ToolTipFilter(self.export_pdf_button, 100))
		self.export_pdf_button.clicked.connect(self._export_pdf)
		
		# 设置导出按钮的样式
		export_hover_color = "rgba(255, 255, 255, 0.1)" if isDarkTheme() else "rgba(0, 0, 0, 0.05)"
		self.export_pdf_button.setStyleSheet("""
			QPushButton {
				background-color: transparent;
				border: none;
				border-radius: 4px;
				padding: 2px;
			}
			QPushButton:hover {
				background-color: %s;
			}
		""" % export_hover_color)
		
		title_layout.addWidget(self.title_label)
		title_layout.addWidget(self.category_label)
		
		for tag in self.note.tags:
			tag_label = CaptionLabel(tag)
			tag_label.setObjectName("card_tag")
			title_layout.addWidget(tag_label)
		
		title_layout.addStretch()
		title_layout.addWidget(self.export_pdf_button)
		title_layout.addWidget(self.create_time_label)
		
		top_layout.addLayout(title_layout)
		
		self.preview_text = NoteCardTextEdit()
		self.preview_text.setReadOnly(True)
		self.preview_text.setObjectName("card_preview")
		self.preview_text.setLineWrapMode(QTextEdit.WidgetWidth)
		self.preview_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.preview_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		self.preview_text.setFrameStyle(QFrame.NoFrame)
		self.preview_text.setStyleSheet("border: none; background: transparent;")
		
		self.content_text = NoteCardTextEdit()
		self.content_text.setPlainText(self.note.content)
		self.content_text.setReadOnly(True)
		self.content_text.setObjectName("card_content")
		self.content_text.setLineWrapMode(QTextEdit.WidgetWidth)
		self.content_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.content_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.content_text.setFrameStyle(QFrame.NoFrame)
		self.content_text.setStyleSheet(
		    "QTextEdit { border: none; }"
		    " QTextEdit QScrollBar:vertical { background: transparent; width: 6px; border-radius: 3px; }"
		    " QTextEdit QScrollBar::handle:vertical { background: rgba(128, 128, 128, 0.4); border-radius: 3px; min-height: 30px; }"
		    " QTextEdit QScrollBar::handle:vertical:hover { background: rgba(128, 128, 128, 0.6); }"
		    " QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical { height: 0px; }"
		    " QTextEdit QScrollBar::add-page:vertical, QTextEdit QScrollBar::sub-page:vertical { background: transparent; }"
		)
		self.content_text.setVisible(False)
		self.content_text.setMouseTracking(True)
		self.content_text.viewport().installEventFilter(self)
		
		buttons_widget = QWidget()
		buttons_layout = QHBoxLayout(buttons_widget)
		buttons_layout.setContentsMargins(0, 5, 0, 0)
		buttons_layout.setSpacing(4)
		
		self.expand_button = QPushButton()
		self.expand_button.setObjectName("card_expand_button")
		self.expand_button.setIcon(QIcon(CustomFluentIcon.EXPAND.icon()))
		self.expand_button.setIconSize(QSize(16, 16))
		self.expand_button.setFixedSize(28, 28)
		self.expand_button.setToolTip("展开")
		self.expand_button.installEventFilter(ToolTipFilter(self.expand_button, 100))
		self.expand_button.clicked.connect(self._toggle_expand)
		self.expand_button.setText("")
		
		self.save_button = QPushButton()
		self.save_button.setObjectName("card_save_button")
		self.save_button.setIcon(QIcon(CustomFluentIcon.SAVE.icon()))
		self.save_button.setFixedSize(28, 28)
		self.save_button.setToolTip("保存")
		self.save_button.installEventFilter(ToolTipFilter(self.save_button, 100))
		self.save_button.clicked.connect(self._on_save)
		self.save_button.setVisible(False)
		
		self.edit_button = QPushButton()
		self.edit_button.setObjectName("card_edit_button")
		self.edit_button.setIcon(QIcon(CustomFluentIcon.EDIT.icon()))
		self.edit_button.setFixedSize(28, 28)
		self.edit_button.setToolTip("编辑")
		self.edit_button.installEventFilter(ToolTipFilter(self.edit_button, 100))
		self.edit_button.clicked.connect(lambda: self.edit_clicked.emit(self.note.id))
		
		self.code_button = QPushButton()
		self.code_button.setObjectName("card_code_button")
		self.code_button.setIcon(QIcon(CustomFluentIcon.CODE.icon()))
		self.code_button.setFixedSize(28, 28)
		self.code_button.setToolTip("查看代码")
		self.code_button.installEventFilter(ToolTipFilter(self.code_button, 100))
		self.code_button.clicked.connect(self._on_view_code)
		
		self.images_button = QPushButton()
		self.images_button.setObjectName("card_images_button")
		self.images_button.setIcon(QIcon(CustomFluentIcon.IMAGE.icon()))
		self.images_button.setFixedSize(28, 28)
		self.images_button.setToolTip("查看图片")
		self.images_button.installEventFilter(ToolTipFilter(self.images_button, 100))
		self.images_button.clicked.connect(self._on_view_images)
		
		self.favorite_button = QPushButton()
		self.favorite_button.setObjectName("card_favorite_button")
		self._update_favorite_button()
		self.favorite_button.setFixedSize(28, 28)
		self.favorite_button.setToolTip("取消收藏" if self.note.is_favorite else "收藏")
		self.favorite_button.installEventFilter(ToolTipFilter(self.favorite_button, 100))
		self.favorite_button.clicked.connect(lambda: self.favorite_clicked.emit(self.note.id))
		
		self.archive_button = QPushButton()
		self.archive_button.setObjectName("card_archive_button")
		self._update_archive_button()
		self.archive_button.setFixedSize(28, 28)
		self.archive_button.setToolTip("取消归档" if self.note.is_archived else "归档")
		self.archive_button.installEventFilter(ToolTipFilter(self.archive_button, 100))
		self.archive_button.clicked.connect(lambda: self.archive_clicked.emit(self.note.id))
		
		self.delete_button = QPushButton()
		self.delete_button.setObjectName("card_delete_button")
		self.delete_button.setIcon(QIcon(CustomFluentIcon.DELETE.icon()))
		self.delete_button.setFixedSize(28, 28)
		self.delete_button.setToolTip("删除")
		self.delete_button.installEventFilter(ToolTipFilter(self.delete_button, 100))
		self.delete_button.clicked.connect(lambda: self.delete_clicked.emit(self.note.id))
		
		buttons_layout.addWidget(self.expand_button)
		buttons_layout.addWidget(self.save_button)
		buttons_layout.addWidget(self.edit_button)
		buttons_layout.addWidget(self.favorite_button)
		buttons_layout.addWidget(self.archive_button)
		
		if (self.note.code_blocks or []) and len(self.note.code_blocks) > 0:
			buttons_layout.addWidget(self.code_button)
		if (self.note.images or []) and len(self.note.images) > 0:
			buttons_layout.addWidget(self.images_button)
		
		buttons_layout.addStretch()
		buttons_layout.addWidget(self.delete_button)
		
		layout.addWidget(top_widget)
		layout.addWidget(self.preview_text)
		layout.addWidget(self.content_text)
		layout.addWidget(buttons_widget)
		
		layout.setStretchFactor(top_widget, 0)
		layout.setStretchFactor(self.preview_text, 0)
		layout.setStretchFactor(self.content_text, 1)
		layout.setStretchFactor(buttons_widget, 0)
		
		self._update_button_styles()
	
	def _setup_animation(self):
		self.animation = QPropertyAnimation(self, b"height")
		self.animation.setDuration(300)
		self.animation.setEasingCurve(QEasingCurve.OutCubic)
	
	def _setup_preview_content(self):
		content = self.note.content or ''
		lines = content.split('\n')
		preview_lines = []
		for i, line in enumerate(lines):
			if i >= 2:
				break
			if line.strip():
				preview_lines.append(line)
		
		preview_content = '\n'.join(preview_lines)
		if not preview_content and content.strip():
			preview_content = lines[0]
		
		self.preview_text.setPlainText(preview_content)
		self.preview_text.setFixedHeight(50)
		
		self._apply_preview_highlight()
	
	def _apply_preview_highlight(self):
		"""应用预览高亮"""
		# 优先使用代码块的语言
		code_blocks = self.note.code_blocks or []
		if code_blocks:
			language = code_blocks[0].language
			self._preview_highlighter = HighlighterFactory.create(language, self.preview_text.document())
			if self._preview_highlighter:
				return
		
		# 使用语言检测器自动检测
		content = (self.note.content or '').strip()
		detected_language = detect_language(content)
		if detected_language:
			self._preview_highlighter = HighlighterFactory.create(detected_language, self.preview_text.document())
	
	def _ensure_collapsed_state(self):
		self.content_text.setVisible(False)
		self.preview_text.setVisible(True)
		self.expand_button.setToolTip("展开")
		self._height = 130
		self.setFixedHeight(130)
	
	@pyqtProperty(int)
	def height(self):
		return self._height
	
	@height.setter
	def height(self, value):
		self._height = value
		self.setFixedHeight(value)
	
	def set_note_manager(self, note_manager):
		self._note_manager = note_manager
	
	def _get_relative_time(self) -> str:
		created_at = self.note.created_at
		if not created_at:
			return ''
		
		from datetime import datetime
		now = datetime.now()
		diff = now - created_at
		
		# 如果创建时间在未来，直接返回日期
		if diff.days < 0 or diff.total_seconds() < 0:
			return created_at.strftime('%Y/%m/%d')
		
		date_str = created_at.strftime('%Y/%m/%d')
		
		if diff.days > 365:
			years = diff.days // 365
			relative = f'{years}年前'
		elif diff.days > 30:
			months = diff.days // 30
			relative = f'{months}个月前'
		elif diff.days > 0:
			relative = f'{diff.days}天前'
		elif diff.seconds > 3600:
			hours = diff.seconds // 3600
			relative = f'{hours}小时前'
		elif diff.seconds > 60:
			minutes = diff.seconds // 60
			relative = f'{minutes}分钟前'
		else:
			relative = '刚刚'
		
		if relative == '刚刚':
			return f'{date_str}(刚刚)'
		return f'{date_str}({relative})'
	
	def _toggle_expand(self):
		# 如果动画正在运行，先停止
		if self.animation.state() == QPropertyAnimation.Running:
			self.animation.stop()
		
		self.is_expanded = not self.is_expanded
		
		if self.is_expanded:
			self.expand_button.setToolTip("收起")
			self.content_text.setVisible(True)
			self.content_text.setReadOnly(False)
			self.content_text.setPlainText(self.note.content or '')
			self.preview_text.setVisible(False)
			self.save_button.setVisible(True)
			
			self._apply_content_highlight()
			
			target_height = 500
			self.animation.setStartValue(self._height)
			self.animation.setEndValue(target_height)
		else:
			self.expand_button.setToolTip("展开")
			self.content_text.setReadOnly(True)
			self.save_button.setVisible(False)
			self.animation.setStartValue(self._height)
			self.animation.setEndValue(130)
			try:
				self.animation.finished.disconnect(self._hide_content)
			except TypeError:
				pass
			self.animation.finished.connect(self._hide_content)
		
		self.animation.start()
	
	def _apply_content_highlight(self):
		"""应用内容高亮"""
		# 优先使用代码块的语言
		code_blocks = self.note.code_blocks or []
		if code_blocks:
			language = code_blocks[0].language
			self._content_highlighter = HighlighterFactory.create(language, self.content_text.document())
			if self._content_highlighter:
				return
		
		# 使用语言检测器自动检测
		content = (self.note.content or '').strip()
		detected_language = detect_language(content)
		if detected_language:
			self._content_highlighter = HighlighterFactory.create(detected_language, self.content_text.document())
	
	def _hide_content(self):
		self.content_text.setVisible(False)
		self.preview_text.setVisible(True)
		try:
			self.animation.finished.disconnect(self._hide_content)
		except (TypeError, RuntimeError):
			pass
	
	def _on_save(self):
		new_content = self.content_text.toPlainText()
		if new_content != self.note.content:
			self.note.content = new_content
			if self._note_manager:
				try:
					self._note_manager.update_note(self.note)
					self.content_updated.emit(self.note.id, new_content)
				except Exception as e:
					from qfluentwidgets import InfoBar, InfoBarPosition
					InfoBar.error(
						title='保存失败',
						content=f'保存笔记失败：{str(e)}',
						orient=Qt.Horizontal,
						isClosable=True,
						position=InfoBarPosition.TOP,
						duration=3000,
						parent=self.window()
					)
	
	def _export_pdf(self):
		"""导出笔记为 TXT 文件"""
		file_path, _ = QFileDialog.getSaveFileName(
			self,
			'导出笔记',
			f'{self.note.title or "无标题"}.txt',
			'TXT 文件 (*.txt)'
		)
		
		if not file_path:
			return
		
		try:
			content = self._build_txt_content()
			with open(file_path, 'w', encoding='utf-8') as f:
				f.write(content)
			from qfluentwidgets import InfoBar, InfoBarPosition
			InfoBar.success(
				title='成功',
				content='笔记已导出',
				orient=Qt.Horizontal,
				isClosable=True,
				position=InfoBarPosition.TOP,
				duration=2000,
				parent=self.window()
			)
		except Exception as e:
			from qfluentwidgets import InfoBar, InfoBarPosition
			InfoBar.error(
				title='错误',
				content=f'导出失败：{str(e)}',
				orient=Qt.Horizontal,
				isClosable=True,
				position=InfoBarPosition.TOP,
				duration=3000,
				parent=self.window()
			)
	
	def _build_txt_content(self) -> str:
		"""构建 TXT 文件内容"""
		lines = []
		
		# 标题
		lines.append(self.note.title or '无标题')
		lines.append('=' * 50)
		lines.append('')
		
		# 元数据
		category_name = self.note.category_name or '未分类'
		create_time = self.note.created_at.strftime('%Y/%m/%d %H:%M') if self.note.created_at else '未知'
		lines.append(f'分类：{category_name}')
		lines.append(f'创建时间：{create_time}')
		
		# 标签
		if self.note.tags:
			lines.append(f'标签：{", ".join(self.note.tags)}')
		
		lines.append('')
		lines.append('-' * 50)
		lines.append('')
		
		# 正文内容
		lines.append(self.note.content)
		lines.append('')
		
		# 代码块
		if self.note.code_blocks:
			lines.append('-' * 50)
			lines.append('代码块')
			lines.append('-' * 50)
			lines.append('')
			for code_block in self.note.code_blocks:
				lines.append(f'[{code_block.language}]')
				lines.append(code_block.content)
				lines.append('')
		
		return '\n'.join(lines)
	
	def _on_view_code(self):
		if not self.note.code_blocks:
			return
		from .code_viewer import CodeViewer
		viewer = CodeViewer(self.note.code_blocks, title='代码块查看', parent=self.window())
		viewer.exec_()
	
	def _on_view_images(self):
		if not self.note.images:
			return
		from .image_viewer import ImageViewer
		viewer = ImageViewer(self.note.images, title='图片查看', parent=self.window())
		viewer.exec_()
	
	def mouseDoubleClickEvent(self, event):
		"""处理双击事件"""
		if self.is_expanded and self.content_text.isVisible():
			# 将坐标转换为相对于 content_text 的坐标
			content_pos = self.content_text.mapFromParent(event.pos())
			cursor = self.content_text.cursorForPosition(content_pos)
			cursor.select(cursor.LineUnderCursor)
			text = cursor.selectedText().strip()
			
			# 检查是否是 URL
			text_lower = text.lower()
			if text_lower.startswith('http://') or text_lower.startswith('https://'):
				import webbrowser
				webbrowser.open(text)
				return
			
			# 检查是否是媒体文件路径
			text_lower = text.lower()
			for ext in self.MEDIA_EXTENSIONS:
				if text_lower.endswith(ext):
					import os
					import subprocess
					import platform
					
					path = text.strip()
					if not os.path.exists(path):
						continue
					try:
						if platform.system() == 'Windows':
							os.startfile(path)
						elif platform.system() == 'Darwin':
							subprocess.run(['open', path], check=False)
						else:
							subprocess.run(['xdg-open', path], check=False)
					except Exception:
						pass
					return
		
		super().mouseDoubleClickEvent(event)
	
	def eventFilter(self, obj, event):
		"""事件过滤器 - 处理 content_text 的双击和悬停事件"""
		from PyQt5.QtCore import QEvent
		from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
		
		if obj == self.content_text.viewport():
			if event.type() == QEvent.MouseButtonDblClick:
				cursor = self.content_text.cursorForPosition(event.pos())
				cursor.select(cursor.LineUnderCursor)
				text = cursor.selectedText().strip()
				
				# 检查是否是 URL
				text_lower = text.lower()
				if text_lower.startswith('http://') or text_lower.startswith('https://'):
					import webbrowser
					webbrowser.open(text)
					return True
				
				# 检查是否是媒体文件路径
				for ext in self.MEDIA_EXTENSIONS:
					if text_lower.endswith(ext):
						import os
						import subprocess
						import platform
						
						path = text.strip()
						if not os.path.exists(path):
							continue
						try:
							if platform.system() == 'Windows':
								os.startfile(path)
							elif platform.system() == 'Darwin':
								subprocess.run(['open', path], check=False)
							else:
								subprocess.run(['xdg-open', path], check=False)
						except Exception:
							pass
						return True
			
			elif event.type() == QEvent.MouseMove:
				# 鼠标移动时检测并高亮链接/媒体文件
				cursor = self.content_text.cursorForPosition(event.pos())
				cursor.select(cursor.LineUnderCursor)
				text = cursor.selectedText().strip()
				text_lower = text.lower()
				
				# 检查是否是可交互的文本
				is_url = text_lower.startswith('http://') or text_lower.startswith('https://')
				is_media = any(text_lower.endswith(ext) for ext in self.MEDIA_EXTENSIONS)
				
				if is_url or is_media:
					# 设置鼠标为手型
					self.content_text.viewport().setCursor(Qt.PointingHandCursor)
				else:
					# 恢复默认鼠标
					self.content_text.viewport().setCursor(Qt.IBeamCursor)
			
			elif event.type() == QEvent.Leave:
				# 鼠标离开时恢复默认鼠标
				self.content_text.viewport().setCursor(Qt.IBeamCursor)
		
		return super().eventFilter(obj, event)
	
	def _update_favorite_button(self):
		if self.note.is_favorite:
			self.favorite_button.setIcon(QIcon(CustomFluentIcon.FAVORITE.icon()))
		else:
			self.favorite_button.setIcon(QIcon(CustomFluentIcon.FAVORITE.icon()))
		self.favorite_button.setToolTip("取消收藏" if self.note.is_favorite else "收藏")
	
	def _update_archive_button(self):
		if self.note.is_archived:
			self.archive_button.setIcon(QIcon(CustomFluentIcon.ARCHIVE.icon()))
		else:
			self.archive_button.setIcon(QIcon(CustomFluentIcon.ARCHIVE.icon()))
		self.archive_button.setToolTip("取消归档" if self.note.is_archived else "归档")
	
	def keyPressEvent(self, event: QKeyEvent):
		"""处理键盘事件"""
		if self.is_expanded and self.content_text.isVisible():
			if event.key() == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
				self._on_save()
				return
		super().keyPressEvent(event)