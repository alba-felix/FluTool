"""
插件使用说明文档界面
提供每个插件的关键性使用说明
"""
from typing import Dict, List, Any

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QFrame, QLabel, QSizePolicy
)
from PyQt5.QtGui import QColor
from qfluentwidgets import (
    ScrollArea, CardWidget, BodyLabel, CaptionLabel,
    StrongBodyLabel, SubtitleLabel, FluentIcon as FIF,
    IconWidget, isDarkTheme, qconfig, TransparentToolButton,
    PushButton, InfoBar, InfoBarPosition
)
from .custom_icon import CustomFluentIcon as CFIF


PLUGIN_DOCS: Dict[str, Dict[str, Any]] = {
    "notebook": {
        "name": "随手记",
        "icon": CFIF.NOTEBOOK,
        "description": "快速记录笔记和想法",
        "usage": [
            "点击「新建」按钮创建新笔记",
            "支持 Markdown 格式",
            "双击笔记可编辑",
            "右键菜单支持删除和重命名"
        ],
        "shortcuts": ["Ctrl+N: 新建笔记", "Ctrl+S: 保存笔记", "Ctrl+F: 搜索笔记"]
    },
    "todo": {
        "name": "待办事项",
        "icon": FIF.CALENDAR,
        "description": "管理待办任务和日程",
        "usage": [
            "输入任务名称后按回车添加",
            "点击复选框标记完成",
            "支持设置优先级和截止日期",
            "已完成任务自动移至底部"
        ],
        "shortcuts": ["Ctrl+N: 新建任务", "Delete: 删除选中任务"]
    },
    "bookmark": {
        "name": "书签管理",
        "icon": CFIF.BOOKMARK_TAG,
        "description": "管理和快速访问网页书签",
        "usage": [
            "点击「添加」按钮新建书签",
            "双击书签在浏览器中打开",
            "支持分类管理",
            "可导入浏览器书签"
        ],
        "shortcuts": ["Ctrl+N: 新建书签", "Ctrl+F: 搜索书签"]
    },
    "app_launcher": {
        "name": "应用启动",
        "icon": FIF.APPLICATION,
        "description": "快速启动应用程序和脚本",
        "usage": [
            "支持 exe、py、bat、ps1、vbs 等文件",
            "Python 脚本使用项目解释器运行",
            "支持分类管理应用",
            "右键菜单删除应用"
        ],
        "shortcuts": ["输入关键词搜索应用"]
    },
    "clipboard": {
        "name": "剪贴板",
        "icon": FIF.PASTE,
        "description": "剪贴板历史记录管理",
        "usage": [
            "自动记录复制的内容",
            "点击历史记录快速粘贴",
            "支持文本和图片",
            "可固定常用内容"
        ],
        "shortcuts": ["Ctrl+Shift+V: 显示剪贴板历史"]
    },
    "color_palette": {
        "name": "取色器",
        "icon": FIF.PALETTE,
        "description": "屏幕取色和颜色管理",
        "usage": [
            "点击「取色」按钮开始取色",
            "鼠标移动实时预览颜色",
            "点击复制颜色值",
            "支持 HEX、RGB、HSL 格式"
        ],
        "shortcuts": ["托盘菜单可快速启动取色"]
    },
    "command": {
        "name": "命令工具",
        "icon": FIF.COMMAND_PROMPT,
        "description": "快速执行系统命令",
        "usage": [
            "输入命令后按回车执行",
            "支持保存常用命令",
            "显示命令执行结果",
            "支持命令历史记录"
        ],
        "shortcuts": ["上下箭头: 浏览历史命令"]
    },
    "quick_copy": {
        "name": "快速复制",
        "icon": FIF.COPY,
        "description": "快速复制常用文本",
        "usage": [
            "添加常用的文本片段",
            "点击即可复制到剪贴板",
            "支持分类管理",
            "可设置快捷键"
        ],
        "shortcuts": ["双击快速复制"]
    },
    "script_manager": {
        "name": "脚本管理",
        "icon": FIF.CODE,
        "description": "管理和执行脚本文件",
        "usage": [
            "支持 Python、Bat、PowerShell 脚本",
            "一键执行脚本",
            "查看脚本输出",
            "支持脚本分类"
        ],
        "shortcuts": ["F5: 执行选中脚本"]
    },
    "password": {
        "name": "密码管理",
        "icon": FIF.FINGERPRINT,
        "description": "安全存储和管理密码",
        "usage": [
            "主密码加密存储",
            "自动生成强密码",
            "一键复制用户名密码",
            "支持密码分类"
        ],
        "shortcuts": ["首次使用需设置主密码"]
    },
    "folder_tree": {
        "name": "文件夹树",
        "icon": FIF.FOLDER,
        "description": "快速浏览文件夹结构",
        "usage": [
            "添加常用文件夹",
            "展开/折叠目录树",
            "双击在资源管理器中打开",
            "支持文件搜索"
        ],
        "shortcuts": ["Ctrl+F: 搜索文件"]
    },
    "text_tools": {
        "name": "文本工具",
        "icon": FIF.TILES,
        "description": "文本处理和转换工具",
        "usage": [
            "支持大小写转换",
            "JSON 格式化",
            "Base64 编解码",
            "文本对比"
        ],
        "shortcuts": ["Ctrl+V: 粘贴文本"]
    },
    "time_converter": {
        "name": "时间转换",
        "icon": CFIF.TIME,
        "description": "时间戳和日期转换",
        "usage": [
            "时间戳转日期",
            "日期转时间戳",
            "支持多种格式",
            "显示当前时间戳"
        ],
        "shortcuts": ["实时更新当前时间"]
    },
    "network": {
        "name": "网络工具",
        "icon": FIF.GLOBE,
        "description": "网络诊断和信息查询",
        "usage": [
            "IP 地址查询",
            "域名 DNS 解析",
            "网络连通测试",
            "查看本机网络信息"
        ],
        "shortcuts": ["回车执行查询"]
    },
    "ai_assistant": {
        "name": "AI 助手",
        "icon": FIF.ROBOT,
        "description": "AI 聊天和智能助手",
        "usage": [
            "支持多种 AI 模型",
            "对话历史记录",
            "可自定义提示词",
            "支持代码高亮"
        ],
        "shortcuts": ["Ctrl+Enter: 发送消息"]
    },
    "image_assistant": {
        "name": "图片助手",
        "icon": CFIF.PICTURE,
        "description": "图片处理和转换工具",
        "usage": [
            "图片格式转换",
            "图片压缩",
            "尺寸调整",
            "批量处理"
        ],
        "shortcuts": ["拖拽图片快速导入"]
    },
    "dev_tools": {
        "name": "开发工具",
        "icon": FIF.DEVELOPER_TOOLS,
        "description": "开发者常用工具集",
        "usage": [
            "Cron 表达式生成",
            "正则表达式测试",
            "UUID 生成",
            "Hash 计算"
        ],
        "shortcuts": ["一键复制结果"]
    },
    "environment": {
        "name": "环境变量",
        "icon": CFIF.ENV,
        "description": "系统环境变量管理",
        "usage": [
            "查看系统/用户环境变量",
            "快速搜索变量",
            "复制变量值",
            "编辑环境变量（需管理员权限）"
        ],
        "shortcuts": ["Ctrl+F: 搜索变量"]
    },
    "text_compare": {
        "name": "文本对比",
        "icon": CFIF.DIFFER,
        "description": "对比两段文本的差异",
        "usage": [
            "左右两栏输入文本",
            "高亮显示差异",
            "支持行级对比",
            "可导出对比结果"
        ],
        "shortcuts": ["Ctrl+Shift+V: 粘贴到当前栏"]
    },
    "system_tools": {
        "name": "系统工具",
        "icon": CFIF.SYSTEM,
        "description": "系统信息和工具",
        "usage": [
            "查看系统信息",
            "快速打开系统设置",
            "进程管理",
            "系统清理"
        ],
        "shortcuts": ["一键打开常用系统工具"]
    }
}


class PluginDocCard(CardWidget):
    """插件文档卡片"""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, plugin_id: str, doc: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.plugin_id = plugin_id
        self.doc = doc
        self._is_hover = False
        self._setup_ui()
    
    def _setup_ui(self):
        self.setBorderRadius(8)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_label = IconWidget(self.doc['icon'], self)
        icon_label.setFixedSize(24, 24)
        header_layout.addWidget(icon_label)
        
        title_label = StrongBodyLabel(self.doc['name'])
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        desc_label = CaptionLabel(self.doc['description'])
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        usage_title = BodyLabel("使用方法")
        usage_title.setStyleSheet("color: #009faa; font-weight: bold;")
        layout.addWidget(usage_title)
        
        for usage in self.doc['usage']:
            usage_label = CaptionLabel(f"• {usage}")
            usage_label.setWordWrap(True)
            layout.addWidget(usage_label)
        
        if self.doc.get('shortcuts'):
            shortcuts_title = BodyLabel("快捷键")
            shortcuts_title.setStyleSheet("color: #009faa; font-weight: bold; margin-top: 8px;")
            layout.addWidget(shortcuts_title)
            
            for shortcut in self.doc['shortcuts']:
                shortcut_label = CaptionLabel(f"• {shortcut}")
                layout.addWidget(shortcut_label)
    
    def enterEvent(self, event):
        self._is_hover = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hover = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, e):
        super().paintEvent(e)
        
        if self._is_hover:
            from PyQt5.QtGui import QPainter, QBrush
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            if isDarkTheme():
                painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            else:
                painter.setBrush(QBrush(QColor(0, 0, 0, 5)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.rect(), 8, 8)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.plugin_id)
        super().mousePressEvent(event)


class PluginDocsInterface(ScrollArea):
    """插件使用说明文档界面"""
    
    cardClicked = pyqtSignal(str)
    backClicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pluginDocsInterface")
        self._setup_ui()
        self._apply_style()
        qconfig.themeChanged.connect(self._apply_style)
    
    def _setup_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        
        self._content_widget = QWidget()
        self._content_widget.setObjectName("contentWidget")
        
        layout = QVBoxLayout(self._content_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        header_layout = QHBoxLayout()
        
        back_btn = TransparentToolButton(FIF.LEFT_ARROW, self._content_widget)
        back_btn.setFixedSize(32, 32)
        back_btn.setIconSize(QSize(14, 14))
        back_btn.setToolTip("返回首页")
        back_btn.clicked.connect(self.backClicked.emit)
        header_layout.addWidget(back_btn)
        
        header_layout.addSpacing(8)
        
        title_label = SubtitleLabel("插件使用说明")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc_label = CaptionLabel("以下是每个插件的关键性使用说明，点击卡片可跳转到对应插件页面。")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        for plugin_id, doc in PLUGIN_DOCS.items():
            card = PluginDocCard(plugin_id, doc, self._content_widget)
            card.clicked.connect(self._on_card_clicked)
            layout.addWidget(card)
        
        layout.addStretch()
        self.setWidget(self._content_widget)
    
    def _apply_style(self):
        if isDarkTheme():
            self.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a1a;
                    border: none;
                }
            """)
            self._content_widget.setStyleSheet("""
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
            self._content_widget.setStyleSheet("""
                QWidget#contentWidget {
                    background-color: #f5f5f5;
                }
            """)
    
    def _on_card_clicked(self, plugin_id: str):
        self.cardClicked.emit(plugin_id)
