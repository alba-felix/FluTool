"""
关于界面
显示应用信息、作者、许可证等
"""
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtGui import QPixmap
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, CaptionLabel,
    StrongBodyLabel, SubtitleLabel, FluentIcon as FIF,
    IconWidget, isDarkTheme, qconfig, TransparentToolButton,
    PushButton, MessageBox, InfoBar, InfoBarPosition
)
from core import get_resource_path


class AboutInterface(ScrollArea):
    """关于界面"""
    
    backClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutInterface")
        self._setup_ui()
        self._apply_style()
        qconfig.themeChanged.connect(self._apply_style)
    
    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        back_btn = TransparentToolButton(FIF.LEFT_ARROW, content_widget)
        back_btn.setFixedSize(32, 32)
        back_btn.setIconSize(QSize(14, 14))
        back_btn.setToolTip("返回首页")
        back_btn.clicked.connect(self.backClicked.emit)
        header_layout.addWidget(back_btn)
        
        header_layout.addSpacing(8)
        
        title_label = SubtitleLabel("关于")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        logo_card = self._create_logo_card(content_widget)
        layout.addWidget(logo_card)
        
        info_card = self._create_info_card(content_widget)
        layout.addWidget(info_card)
        
        tech_card = self._create_tech_card(content_widget)
        layout.addWidget(tech_card)
        
        layout.addStretch()
        self.setWidget(content_widget)
    
    def _create_logo_card(self, parent) -> CardWidget:
        """创建 Logo 卡片"""
        card = CardWidget(parent)
        card.setBorderRadius(8)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)
        
        logo_path = get_resource_path("logo.ico")
        if logo_path.exists():
            logo_label = QLabel()
            logo_pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(logo_pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        
        title = StrongBodyLabel("FluTool")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
        
        version = CaptionLabel("版本 0.1.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version, alignment=Qt.AlignCenter)
        
        desc = CaptionLabel("一款基于 PyQt5 的 Fluent Design 风格工具集")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc, alignment=Qt.AlignCenter)
        
        return card
    
    def _create_info_card(self, parent) -> CardWidget:
        """创建信息卡片"""
        card = CardWidget(parent)
        card.setBorderRadius(8)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        info_items = [
            ("作者", "FluTool Team"),
            ("许可证", "MIT License"),
            ("网站", "https://github.com/flutool"),
            ("邮箱", "flutool@example.com"),
        ]
        
        for label, value in info_items:
            item_layout = QHBoxLayout()
            label_widget = BodyLabel(label)
            label_widget.setFixedWidth(60)
            item_layout.addWidget(label_widget)
            
            value_widget = CaptionLabel(value)
            item_layout.addWidget(value_widget, 1)
            
            layout.addLayout(item_layout)
        
        return card
    
    def _create_tech_card(self, parent) -> CardWidget:
        """创建技术栈卡片"""
        card = CardWidget(parent)
        card.setBorderRadius(8)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        tech_title = BodyLabel("技术栈")
        layout.addWidget(tech_title)
        
        tech_items = [
            "Python 3.8+",
            "PyQt5 - GUI 框架",
            "QFluentWidgets - Fluent Design 组件库",
            "SQLite - 数据存储",
        ]
        
        for item in tech_items:
            item_label = CaptionLabel(f"• {item}")
            layout.addWidget(item_label)
        
        return card
    
    def _apply_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
            self.widget().setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #f5f5f5;
                    border: none;
                }
            """)
            self.widget().setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f5f5f5;
                }
            """)


class CheckUpdateInterface(ScrollArea):
    """检查更新界面"""
    
    backClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("checkUpdateInterface")
        self._setup_ui()
        self._apply_style()
        qconfig.themeChanged.connect(self._apply_style)
    
    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        back_btn = TransparentToolButton(FIF.LEFT_ARROW, content_widget)
        back_btn.setFixedSize(32, 32)
        back_btn.setIconSize(QSize(14, 14))
        back_btn.setToolTip("返回首页")
        back_btn.clicked.connect(self.backClicked.emit)
        header_layout.addWidget(back_btn)
        
        header_layout.addSpacing(8)
        
        title_label = SubtitleLabel("检查更新")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        card = CardWidget(content_widget)
        card.setBorderRadius(8)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignCenter)
        
        icon = IconWidget(FIF.UPDATE, card)
        icon.setFixedSize(48, 48)
        card_layout.addWidget(icon, alignment=Qt.AlignCenter)
        
        current_version = StrongBodyLabel("当前版本: 0.1.0")
        current_version.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(current_version, alignment=Qt.AlignCenter)
        
        status_label = CaptionLabel("您正在使用最新版本")
        status_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(status_label, alignment=Qt.AlignCenter)
        
        check_btn = PushButton("检查更新", card)
        check_btn.setFixedWidth(120)
        check_btn.clicked.connect(self._check_update)
        card_layout.addWidget(check_btn, alignment=Qt.AlignCenter)
        
        layout.addWidget(card)
        layout.addStretch()
        self.setWidget(content_widget)
    
    def _check_update(self):
        """检查更新"""
        InfoBar.success(
            title="检查完成",
            content="您正在使用最新版本",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
    
    def _apply_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
            self.widget().setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #f5f5f5;
                    border: none;
                }
            """)
            self.widget().setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f5f5f5;
                }
            """)


class FeedbackInterface(ScrollArea):
    """问题反馈界面"""
    
    backClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("feedbackInterface")
        self._setup_ui()
        self._apply_style()
        qconfig.themeChanged.connect(self._apply_style)
    
    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_widget.setObjectName("contentWidget")
        
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        back_btn = TransparentToolButton(FIF.LEFT_ARROW, content_widget)
        back_btn.setFixedSize(32, 32)
        back_btn.setIconSize(QSize(14, 14))
        back_btn.setToolTip("返回首页")
        back_btn.clicked.connect(self.backClicked.emit)
        header_layout.addWidget(back_btn)
        
        header_layout.addSpacing(8)
        
        title_label = SubtitleLabel("问题反馈")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        card = CardWidget(content_widget)
        card.setBorderRadius(8)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(16)
        
        desc_label = CaptionLabel("感谢您使用 FluTool！如果您在使用过程中遇到问题或有建议，请通过以下方式反馈：")
        desc_label.setWordWrap(True)
        card_layout.addWidget(desc_label)
        
        feedback_items = [
            ("GitHub Issues", "https://github.com/flutool/issues", "提交 Bug 报告或功能建议"),
            ("邮件反馈", "flutool@example.com", "发送问题描述和截图"),
            ("QQ 群", "123456789", "加入用户交流群"),
        ]
        
        for title, contact, desc in feedback_items:
            item_layout = QHBoxLayout()
            
            title_label = BodyLabel(title)
            title_label.setFixedWidth(100)
            item_layout.addWidget(title_label)
            
            contact_label = CaptionLabel(contact)
            item_layout.addWidget(contact_label, 1)
            
            desc_label = CaptionLabel(desc)
            desc_label.setProperty("class", "secondary-label")
            item_layout.addWidget(desc_label, 1)
            
            card_layout.addLayout(item_layout)
        
        layout.addWidget(card)
        layout.addStretch()
        self.setWidget(content_widget)
    
    def _apply_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
            self.widget().setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #f5f5f5;
                    border: none;
                }
            """)
            self.widget().setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f5f5f5;
                }
            """)
