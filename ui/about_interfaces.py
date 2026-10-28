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
            if not logo_pixmap.isNull():
                logo_label.setPixmap(logo_pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        
        title = StrongBodyLabel("FluTool")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title, alignment=Qt.AlignCenter)
        
        version = CaptionLabel("版本 0.2.2")
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
        
        current_version = StrongBodyLabel("当前版本: 0.2.2")
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


# 更新日志数据：版本 -> [(标签, 描述), ...]，新版本在列表前部追加
CHANGELOG_ENTRIES = [
    ("v0.2.2", [
        ("新功能", "新增 JSON 工具插件，支持格式化、校验与语法高亮"),
        ("新功能", "新增硬件工具插件，并注册插件索引与导航图标"),
        ("新功能", "新增端口监听检测工具"),
        ("新功能", "新增 SKILL 管理器，支持技能查看与管理"),
        ("新功能", "图片转换器支持尺寸选择与批量转换"),
        ("新功能", "翻译插件新增有道密钥自管理对话框"),
        ("新功能", "生词本新增默认分类，联动筛选下拉框"),
        ("新功能", "剪贴板图片图库新增清空按钮"),
        ("新功能", "导航栏与标题栏按钮增加悬浮提示"),
        ("优化", "插件加载与初始化流程优化，启动更轻快"),
        ("优化", "待办提醒支持稍后提醒与弹窗排队"),
        ("重构", "Repository 搜索逻辑统一，移除冗余实现"),
        ("重构", "app_launcher 模块拆分，3020 行拆为 9 个文件"),
        ("重构", "dev_tools 与 text_tools 子工具拆分独立文件夹"),
        ("重构", "笔记插件服务分层重构，优化代码结构"),
        ("修复", "笔记编辑框输入法候选窗下移，不再遮挡标题与标签"),
        ("修复", "打包后笔记插件不可用，plugin_index 缺少 notes 条目"),
        ("修复", "PluginManager 支持子模块 Plugin 类加载"),
        ("修复", "Notes EventBus 桥接内核，支持跨模块事件通信"),
        ("修复", "github_trending 网络异常未捕获导致崩溃"),
        ("修复", "应用启动器添加应用时去重检查"),
    ]),
    ("v0.2.1", [
        ("新功能", "新增笔记管理插件，支持富文本编辑与知识卡片"),
        ("新功能", "新增单词背诵插件与生词本"),
        ("新功能", "新增 AI 助手插件，支持 DeepSeek、硅基流动与 Ollama Cloud"),
        ("新功能", "新增翻译插件与 MCP 服务器管理插件"),
        ("新功能", "新增全局搜索，覆盖全部适用插件"),
        ("新功能", "新增快速复制、脚本管理器、文件夹树等实用插件"),
        ("新功能", "新增开机自启与最小化到系统托盘"),
        ("新功能", "应用启动器支持应用编辑、收藏与排序"),
        ("新功能", "开发工具新增 SVG 查看器与 DeepSeek 对话处理工具"),
        ("优化", "日志系统升级为 loguru，支持插件独立日志文件"),
        ("优化", "侧边栏改为可滚动导航，适配更多插件"),
        ("重构", "重构 DatabaseManager，引入 Repository 模式"),
        ("重构", "用 RoundMenu 替换项目内原生 QMenu"),
        ("重构", "重构运行时目录结构与数据管理流程"),
        ("重构", "JSON 数据迁移到 SQLite 数据库"),
        ("修复", "修复书签链接打开失败、剪贴板插件语法错误等问题"),
    ]),
    ("v0.1.0", [
        ("新功能", "首个版本，搭建微内核 + 插件化框架"),
        ("新功能", "首批插件：书签、命令面板、密码管理"),
        ("新功能", "Fluent Design 界面，支持深色与浅色主题"),
        ("新功能", "基于 SQLite 的本地数据存储"),
    ]),
]

# 标签配色
_TAG_COLORS = {
    "新功能": "#9333ea",
    "优化": "#ea580c",
    "重构": "#0078d4",
    "修复": "#16a34a",
}


class ChangelogInterface(ScrollArea):
    """更新日志界面"""
    
    backClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("changelogInterface")
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
        
        title_label = SubtitleLabel("更新日志")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 当前版本号取自日志首条（最新版本），避免多处硬编码
        if CHANGELOG_ENTRIES:
            version_label = CaptionLabel(f"当前版本 {CHANGELOG_ENTRIES[0][0]}")
            header_layout.addWidget(version_label)
        
        layout.addLayout(header_layout)
        
        for version, items in CHANGELOG_ENTRIES:
            layout.addWidget(self._create_version_card(content_widget, version, items))
        
        layout.addStretch()
        self.setWidget(content_widget)
    
    def _create_version_card(self, parent, version: str, items) -> CardWidget:
        """创建单个版本的更新日志卡片"""
        card = CardWidget(parent)
        card.setBorderRadius(8)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)
        
        version_label = StrongBodyLabel(version)
        card_layout.addWidget(version_label)
        
        for tag, desc in items:
            row = QWidget(card)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(8)
            
            tag_label = CaptionLabel(tag)
            tag_label.setFixedWidth(36)
            tag_label.setAlignment(Qt.AlignCenter)
            tag_label.setStyleSheet(
                f"color: {_TAG_COLORS.get(tag, '#666666')}; font-weight: 600;"
            )
            row_layout.addWidget(tag_label)
            
            desc_label = CaptionLabel(desc)
            desc_label.setWordWrap(True)
            row_layout.addWidget(desc_label, 1)
            
            card_layout.addWidget(row)
        
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
