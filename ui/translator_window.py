"""翻译小窗口 - 独立悬浮窗口"""

from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QApplication
from PyQt5.QtGui import QKeyEvent
from qfluentwidgets import (
    ComboBox, PushButton, TextEdit, ToolButton, 
    FluentIcon as FIF, isDarkTheme
)
from qframelesswindow import FramelessWindow


class TranslateWorker(QThread):
    """翻译工作线程"""
    finished = pyqtSignal(str, str)
    
    def __init__(self, text: str, source_lang: str, target_lang_name: str):
        super().__init__()
        self.text = text
        self.source_lang = source_lang
        self.target_lang_name = target_lang_name
    
    def run(self):
        """执行翻译"""
        try:
            # 导入翻译服务
            from plugins.sub_plugin.translation_service import get_translation_service
            
            service = get_translation_service()
            # target_lang 需要传递语言名称（如"中文"），不是代码
            result, source = service.translate(
                self.text, 
                source_lang=self.source_lang,
                target_lang=self.target_lang_name
            )
            
            # 添加来源标记
            if source == "local":
                result = f"[本地词典]\n{result}"
            elif source == "api":
                result = f"[有道翻译]\n{result}"
            
            self.finished.emit(result, "")
        except Exception as e:
            self.finished.emit("", str(e))


class TranslatorWindow(FramelessWindow):
    """翻译小窗口"""
    
    LANGUAGES = {
        "auto": "自动检测",
        "zh-CHS": "中文",
        "en": "英语",
        "ja": "日语",
        "ko": "韩语",
        "fr": "法语",
        "de": "德语",
        "es": "西班牙语",
        "ru": "俄语",
        "ar": "阿拉伯语",
        "pt": "葡萄牙语",
        "it": "意大利语",
        "nl": "荷兰语",
        "pl": "波兰语",
        "tr": "土耳其语",
        "vi": "越南语",
        "th": "泰语",
        "id": "印尼语",
        "ms": "马来语",
    }
    
    # 自动翻译延迟(毫秒)
    AUTO_TRANSLATE_DELAY = 1100
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("翻译")
        self.setFixedSize(700, 500)
        self._setup_ui()
        self._apply_theme()
        
        # 自动翻译定时器
        self._auto_translate_timer = QTimer()
        self._auto_translate_timer.setSingleShot(True)
        self._auto_translate_timer.timeout.connect(self._do_translate)
    
    def _setup_ui(self):
        """设置UI"""
        self.setObjectName("translatorWindow")
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 12, 12, 12)
        
        # 顶部语言选择栏
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        # 源语言选择
        self._source_lang = ComboBox()
        self._source_lang.addItems(list(self.LANGUAGES.values()))
        self._source_lang.setCurrentText("自动检测")
        self._source_lang.setFixedWidth(120)
        top_layout.addWidget(self._source_lang)
        
        # 交换按钮
        self._swap_btn = ToolButton(FIF.SYNC)
        self._swap_btn.setToolTip("交换语言")
        self._swap_btn.setFixedSize(32, 32)
        self._swap_btn.clicked.connect(self._swap_languages)
        top_layout.addWidget(self._swap_btn)
        
        # 目标语言选择
        self._target_lang = ComboBox()
        self._target_lang.addItems([v for k, v in self.LANGUAGES.items() if k != "auto"])
        self._target_lang.setCurrentText("中文")
        self._target_lang.setFixedWidth(120)
        top_layout.addWidget(self._target_lang)
        
        # 翻译按钮
        self._translate_btn = PushButton("翻译", self, FIF.SEND)
        self._translate_btn.setFixedWidth(80)
        self._translate_btn.clicked.connect(self._do_translate)
        top_layout.addWidget(self._translate_btn)
        
        top_layout.addStretch(1)
        
        main_layout.addLayout(top_layout)
        
        # 文本编辑区域
        splitter = QSplitter(Qt.Horizontal)
        
        # 源文本
        self._source_text = TextEdit()
        self._source_text.setPlaceholderText("输入要翻译的文本...")
        self._source_text.setObjectName("sourceText")
        self._source_text.textChanged.connect(self._on_source_text_changed)
        splitter.addWidget(self._source_text)
        
        # 目标文本
        self._target_text = TextEdit()
        self._target_text.setPlaceholderText("翻译结果...")
        self._target_text.setObjectName("targetText")
        self._target_text.setReadOnly(True)
        splitter.addWidget(self._target_text)
        
        splitter.setSizes([350, 350])
        main_layout.addWidget(splitter)
        
        # 底部按钮栏
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        
        # 清空按钮
        self._clear_btn = PushButton("清空", self, FIF.DELETE)
        self._clear_btn.clicked.connect(self._clear_all)
        bottom_layout.addWidget(self._clear_btn)
        
        # 复制按钮
        self._copy_btn = PushButton("复制结果", self, FIF.COPY)
        self._copy_btn.clicked.connect(self._copy_result)
        bottom_layout.addWidget(self._copy_btn)
        
        bottom_layout.addStretch(1)
        
        main_layout.addLayout(bottom_layout)
    
    def _apply_theme(self):
        """应用主题样式"""
        dark = isDarkTheme()
        
        if dark:
            bg_color = "#2d2d2d"
            text_color = "#e6e6e6"
            border_color = "#3d3d3d"
        else:
            bg_color = "#f5f5f5"
            text_color = "#333333"
            border_color = "#e0e0e0"
        
        self.setStyleSheet(f"""
            TranslatorWindow {{
                background-color: {bg_color};
            }}
            TextEdit {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 8px;
            }}
            TextEdit:focus {{
                border: 1px solid #0078d4;
            }}
        """)
    
    def _swap_languages(self):
        """交换源语言和目标语言"""
        source = self._source_lang.currentText()
        target = self._target_lang.currentText()
        
        # 如果源语言是自动检测，则不交换
        if source == "自动检测":
            return
        
        self._source_lang.setCurrentText(target)
        self._target_lang.setCurrentText(source)
        
        # 同时交换文本
        source_text = self._source_text.toPlainText()
        target_text = self._target_text.toPlainText()
        self._source_text.setPlainText(target_text)
        self._target_text.setPlainText(source_text)
    
    def _do_translate(self):
        """执行翻译"""
        text = self._source_text.toPlainText().strip()
        if not text:
            return
        
        # 获取语言代码和名称
        source_lang = self._get_lang_code(self._source_lang.currentText())
        target_lang_name = self._target_lang.currentText()  # 传递语言名称给翻译服务
        
        # 显示加载中
        self._target_text.setPlainText("翻译中...")
        self._translate_btn.setEnabled(False)
        
        # 启动翻译线程
        self._worker = TranslateWorker(text, source_lang, target_lang_name)
        self._worker.finished.connect(self._on_translate_finished)
        self._worker.start()
    
    def _on_translate_finished(self, result: str, error: str):
        """翻译完成回调"""
        self._translate_btn.setEnabled(True)
        if error:
            self._target_text.setPlainText(f"翻译失败: {error}")
        else:
            self._target_text.setPlainText(result)
    
    def _get_lang_code(self, lang_name: str) -> str:
        """获取语言代码"""
        for code, name in self.LANGUAGES.items():
            if name == lang_name:
                return code
        return "auto"
    
    def _on_source_text_changed(self):
        """源文本变化时启动自动翻译定时器"""
        text = self._source_text.toPlainText().strip()
        if text:
            # 重新启动定时器，延迟1100ms后自动翻译
            self._auto_translate_timer.start(self.AUTO_TRANSLATE_DELAY)
        else:
            # 文本为空时清空结果
            self._target_text.clear()
            self._auto_translate_timer.stop()
    
    def _clear_all(self):
        """清空所有文本"""
        self._source_text.clear()
        self._target_text.clear()
        self._auto_translate_timer.stop()
    
    def _copy_result(self):
        """复制翻译结果"""
        text = self._target_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
    
    def keyPressEvent(self, event: QKeyEvent):
        """按键事件"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
            self._do_translate()
        else:
            super().keyPressEvent(event)
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        self._source_text.setFocus()
    
    def set_source_text(self, text: str):
        """设置源文本"""
        self._source_text.setPlainText(text)
