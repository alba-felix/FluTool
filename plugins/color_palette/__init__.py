import os
import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from ctypes import windll, byref, c_int, c_long, POINTER, WINFUNCTYPE, Structure, sizeof
from ctypes.wintypes import DWORD, HINSTANCE, MSG, POINT, WPARAM, LPARAM
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QEvent, QPoint, QRect, QPoint
from PyQt5.QtGui import QColor, QPalette, QPixmap, QPainter, QCursor, QIcon, QScreen
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QColorDialog,
    QGridLayout, QScrollArea, QFrame, QTabWidget,
    QSplitter, QListWidget, QListWidgetItem, QMessageBox, QToolTip,
    QMenu, QAction, QApplication
)
from qfluentwidgets import (
    StrongBodyLabel, PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, ScrollArea, PrimaryPushButton, ToolButton,
    CardWidget, SpinBox, isDarkTheme, qconfig
)
from core import PluginInterface, SearchResult
from plugins.color_palette.service import ColorPaletteService

# Windows Hook 常量
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207

# MSLLHOOKSTRUCT 结构体定义
class MSLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", DWORD),
        ("flags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", POINTER(c_long))
    ]

# 鼠标Hook类型定义
LowLevelMouseProc = WINFUNCTYPE(c_int, c_int, WPARAM, POINTER(MSLLHOOKSTRUCT))

# 全局变量
_mouse_hook = None
_mouse_hook_proc = None
_mouse_callback = None

def _mouse_hook_callback(nCode, wParam, lParam):
    """鼠标Hook回调"""
    if nCode >= 0 and _mouse_callback:
        try:
            _mouse_callback(wParam)
        except Exception as e:
            print(f"Mouse hook callback error: {e}")
    return windll.user32.CallNextHookEx(_mouse_hook, nCode, wParam, lParam)

def install_mouse_hook(callback):
    """安装鼠标Hook"""
    global _mouse_hook, _mouse_hook_proc, _mouse_callback
    try:
        _mouse_callback = callback
        _mouse_hook_proc = LowLevelMouseProc(_mouse_hook_callback)
        _mouse_hook = windll.user32.SetWindowsHookExW(
            WH_MOUSE_LL, 
            _mouse_hook_proc, 
            None,  # hMod设为None表示当前线程
            0      # dwThreadId为0表示系统全局Hook
        )
        return _mouse_hook is not None
    except Exception as e:
        print(f"Install mouse hook error: {e}")
        return False

def uninstall_mouse_hook():
    """卸载鼠标Hook"""
    global _mouse_hook, _mouse_callback, _mouse_hook_proc
    try:
        if _mouse_hook:
            windll.user32.UnhookWindowsHookEx(_mouse_hook)
            _mouse_hook = None
        _mouse_callback = None
        _mouse_hook_proc = None
    except Exception as e:
        print(f"Uninstall mouse hook error: {e}")


class MagnifierWindow(QWidget):
    """放大镜窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._magnifier_size = 150  # 放大镜大小
        self._zoom = 8  # 放大倍数
        self._last_color = None
        
        self.setFixedSize(self._magnifier_size + 60, self._magnifier_size + 80)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.NoFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # 放大镜显示区域
        self._magnifier_label = QLabel()
        self._magnifier_label.setFixedSize(self._magnifier_size, self._magnifier_size)
        self._magnifier_label.setAlignment(Qt.AlignCenter)
        self._magnifier_label.setStyleSheet("""
            QLabel {
                border: 2px solid #333;
                border-radius: 8px;
                background-color: #000;
            }
        """)
        layout.addWidget(self._magnifier_label)
        
        # 颜色信息区域
        info_layout = QHBoxLayout()
        info_layout.setSpacing(8)
        
        # 颜色预览块
        self._color_preview = QLabel()
        self._color_preview.setFixedSize(40, 25)
        self._color_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #666;
                border-radius: 3px;
            }
        """)
        info_layout.addWidget(self._color_preview)
        
        # 颜色值
        self._color_info = QLabel()
        self._color_info.setStyleSheet("""
            QLabel {
                color: #fff;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        info_layout.addWidget(self._color_info)
        
        layout.addLayout(info_layout)
        
        # 提示文字
        hint_label = QLabel("左键选取颜色")
        hint_label.setStyleSheet("""
            QLabel {
                color: #aaa;
                font-size: 10px;
                qproperty-alignment: AlignCenter;
            }
        """)
        layout.addWidget(hint_label)
    
    def update_magnifier(self, cursor_pos: QPoint, screen: QScreen):
        """更新放大镜内容"""
        if not screen:
            return
        
        try:
            # 截图区域
            x, y = cursor_pos.x(), cursor_pos.y()
            half_size = (self._magnifier_size // self._zoom) // 2
            
            grab_x = max(0, x - half_size)
            grab_y = max(0, y - half_size)
            
            pixmap = screen.grabWindow(
                0, 
                grab_x, 
                grab_y, 
                half_size * 2, 
                half_size * 2
            )
            
            # 放大显示
            scaled_pixmap = pixmap.scaled(
                self._magnifier_size, 
                self._magnifier_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self._magnifier_label.setPixmap(scaled_pixmap)
            
            # 获取中心点颜色
            center_pixmap = screen.grabWindow(0, x, y, 1, 1)
            image = center_pixmap.toImage()
            if not image.isNull():
                color = QColor(image.pixel(0, 0))
                if color.isValid():
                    self._last_color = color
                    self._color_preview.setStyleSheet(f"""
                        QLabel {{
                            background-color: {color.name()};
                            border: 1px solid #666;
                            border-radius: 3px;
                        }}
                    """)
                    self._color_info.setText(f"{color.name()}\nRGB: {color.red()}, {color.green()}, {color.blue()}")
            
            # 更新窗口位置（跟随鼠标，右下角）
            screen_geo = screen.geometry()
            new_x = cursor_pos.x() + 30
            new_y = cursor_pos.y() + 30
            
            if new_x + self.width() > screen_geo.right():
                new_x = cursor_pos.x() - self.width() - 30
            if new_y + self.height() > screen_geo.bottom():
                new_y = cursor_pos.y() - self.height() - 30
            
            self.move(new_x, new_y)
            self.show()
            
        except Exception as e:
            print(f"Update magnifier error: {e}")
    
    def get_last_color(self):
        """获取最后一次鼠标位置的颜色"""
        return self._last_color
    
    def hide(self):
        """隐藏窗口"""
        super().hide()
    
    def close(self):
        """关闭窗口"""
        super().close()


class ColorPaletteWidget(QWidget):
    """调色板插件界面"""
    PLUGIN_ID = "color_palette"
    color_changed = pyqtSignal(str)

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.service = ColorPaletteService(self.PLUGIN_ID)
        self.current_color = QColor(255, 255, 255)
        self.is_picking = False
        self.updating_display = False
        self.pick_timer = None
        self.pick_button = None
        
        self.init_ui()
        self.setup_style()
        self.load_colors()
        qconfig.themeChangedFinished.connect(self.on_theme_changed)

    def on_theme_changed(self):
        """主题变化时更新样式"""
        QTimer.singleShot(0, self.setup_style)

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建最外层滚动区域
        self._scroll_area = ScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setObjectName("colorPaletteScrollArea")

        # 创建内容容器
        self._content_widget = QWidget()
        self._content_widget.setObjectName("contentWidget")
        self._content_layout = QHBoxLayout(self._content_widget)
        self._content_layout.setSpacing(8)
        self._content_layout.setContentsMargins(8, 8, 8, 8)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        self._left_panel = self.create_left_panel()
        splitter.addWidget(self._left_panel)

        self._right_panel = self.create_right_panel()
        splitter.addWidget(self._right_panel)

        splitter.setSizes([400, 600])
        self._content_layout.addWidget(splitter)

        # 将内容容器添加到滚动区域
        self._scroll_area.setWidget(self._content_widget)

        main_layout.addWidget(self._scroll_area)

    def setup_style(self):
        """设置样式（支持主题）"""
        dark = isDarkTheme()
        
        if dark:
            bg_color = "#1e1e1e"
            text_color = "#ffffff"
            tab_bg = "#2d2d2d"
            tab_selected = "#1e1e1e"
            accent_color = "#009faa"
        else:
            bg_color = "#f5f5f5"
            text_color = "#333333"
            tab_bg = "#e6e6e6"
            tab_selected = "#f5f5f5"
            accent_color = "#009faa"
        
        # 滚动区域
        self._scroll_area.setStyleSheet(f"""
            ScrollArea#colorPaletteScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollArea#colorPaletteScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
        """)
        
        # 内容容器
        self._content_widget.setStyleSheet(f"QWidget#contentWidget{{background-color: {bg_color};}}")
        
        # 左侧面板
        self._left_panel.setStyleSheet(f"""
            QWidget#leftPanel {{
                background-color: {bg_color};
            }}
            QLabel#colorInputLabel {{
                color: {text_color};
                background-color: transparent;
            }}
        """)
        
        # 右侧面板
        self._right_panel.setStyleSheet(f"QWidget{{background-color: {bg_color};}}")
        
        # 收藏标签页
        self._favorite_tab.setStyleSheet(f"QWidget{{background-color: {bg_color};}}")
        
        # 颜色对照表标签页
        self._color_table_tab.setStyleSheet(f"QWidget{{background-color: {bg_color};}}")
        
        # 标签页 - 使用对象名称选择器
        self._tab_widget.setStyleSheet(f"""
            QTabWidget#colorPaletteTabWidget {{
                color: {text_color};
                background-color: {bg_color};
            }}
            QTabWidget#colorPaletteTabWidget::pane {{
                border: none;
                background-color: {bg_color};
                color: {text_color};
            }}
            QTabWidget#colorPaletteTabWidget QTabBar {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QTabWidget#colorPaletteTabWidget QTabBar::tab {{
                background-color: {tab_bg};
                color: {text_color};
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabWidget#colorPaletteTabWidget QTabBar::tab:hover {{
                background-color: {tab_selected};
                color: {text_color};
            }}
            QTabWidget#colorPaletteTabWidget QTabBar::tab:selected {{
                background-color: {tab_selected};
                color: {accent_color};
            }}
            
            QTabWidget#colorPaletteTabWidget QLabel {{
                color: {text_color};
                background-color: {bg_color};
            }}
            
            QTabWidget#colorPaletteTabWidget QListWidget {{
                color: {text_color};
                background-color: {bg_color};
            }}
        """)
        
        # 颜色对照表标签页内的值标签
        if hasattr(self, '_table_widget'):
            link_color = "#4da6ff" if dark else "#2c5aa0"
            self._table_widget.setStyleSheet(f"""
                QWidget#colorTableTabContent {{
                    background-color: {bg_color};
                }}
                QWidget#colorTableScrollWidget {{
                    background-color: {bg_color};
                }}
                QLabel {{
                    color: {text_color};
                    background-color: {bg_color};
                }}
                QLabel#colorTableValueLabel {{
                    font-family: monospace;
                    color: {link_color};
                    text-decoration: underline;
                }}
            """)

    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QWidget()
        left_widget.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        color_group = CardWidget()
        color_layout = QVBoxLayout(color_group)
        color_layout.setSpacing(12)

        # 标题
        title_label = StrongBodyLabel("颜色选择器")
        color_layout.addWidget(title_label)

        # 颜色显示
        display_layout = QHBoxLayout()
        display_layout.setSpacing(12)

        self.color_display = QLabel()
        self.color_display.setFixedSize(120, 120)
        self.color_display.setStyleSheet(
            "border: 2px solid #cccccc; border-radius: 8px; background-color: #ffffff;"
        )
        display_layout.addWidget(self.color_display)

        display_info_layout = QVBoxLayout()
        display_info_layout.setSpacing(8)

        self.color_name_label = QLabel("颜色名称")
        self.color_name_label.setObjectName("colorInputLabel")
        display_info_layout.addWidget(self.color_name_label)

        self.color_info_label = QLabel("RGB: 255, 255, 255")
        self.color_info_label.setObjectName("colorInputLabel")
        self.color_info_label.setWordWrap(True)
        display_info_layout.addWidget(self.color_info_label)

        display_info_layout.addStretch()
        display_layout.addLayout(display_info_layout)
        color_layout.addLayout(display_layout)

        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.choose_btn = PushButton("选择颜色")
        self.choose_btn.setIcon(FIF.PALETTE)
        self.choose_btn.clicked.connect(self.open_color_dialog)
        button_layout.addWidget(self.choose_btn)

        self.pick_button = PrimaryPushButton("屏幕取色")
        self.pick_button.setIcon(FIF.CAMERA)
        self.pick_button.clicked.connect(self.toggle_color_picker)
        button_layout.addWidget(self.pick_button)

        color_layout.addLayout(button_layout)

        # 保存按钮
        self.save_btn = PrimaryPushButton("保存到收藏")
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.clicked.connect(self.save_color_to_db)
        color_layout.addWidget(self.save_btn)

        left_layout.addWidget(color_group)

        # 颜色格式转换
        convert_group = CardWidget()
        convert_layout = QVBoxLayout(convert_group)
        convert_layout.setSpacing(12)

        convert_title = StrongBodyLabel("颜色格式转换")
        convert_layout.addWidget(convert_title)

        # HEX输入
        hex_layout = QHBoxLayout()
        hex_label = QLabel("HEX:")
        hex_label.setObjectName("colorInputLabel")
        hex_label.setFixedWidth(60)
        self.hex_input = LineEdit()
        self.hex_input.setPlaceholderText("#FFFFFF")
        self.hex_input.textChanged.connect(self.hex_input_changed)
        hex_layout.addWidget(hex_label)
        hex_layout.addWidget(self.hex_input)

        hex_btn = ToolButton(FIF.COPY)
        hex_btn.clicked.connect(lambda: self.copy_color_value(self.hex_input.text()))
        hex_layout.addWidget(hex_btn)

        convert_layout.addLayout(hex_layout)

        # RGB输入
        rgb_layout = QHBoxLayout()
        rgb_label = QLabel("RGB:")
        rgb_label.setObjectName("colorInputLabel")
        rgb_label.setFixedWidth(60)
        self.rgb_input = LineEdit()
        self.rgb_input.setPlaceholderText("255,255,255")
        self.rgb_input.textChanged.connect(self.rgb_input_changed)
        rgb_layout.addWidget(rgb_label)
        rgb_layout.addWidget(self.rgb_input)

        rgb_btn = ToolButton(FIF.COPY)
        rgb_btn.clicked.connect(lambda: self.copy_color_value(self.rgb_input.text()))
        rgb_layout.addWidget(rgb_btn)

        convert_layout.addLayout(rgb_layout)

        # HSV输入
        hsv_layout = QHBoxLayout()
        hsv_label = QLabel("HSV:")
        hsv_label.setObjectName("colorInputLabel")
        hsv_label.setFixedWidth(60)
        self.hsv_input = LineEdit()
        self.hsv_input.setPlaceholderText("0,0,100")
        self.hsv_input.setReadOnly(True)
        hsv_layout.addWidget(hsv_label)
        hsv_layout.addWidget(self.hsv_input)

        hsv_btn = ToolButton(FIF.COPY)
        hsv_btn.clicked.connect(lambda: self.copy_color_value(self.hsv_input.text()))
        hsv_layout.addWidget(hsv_btn)

        convert_layout.addLayout(hsv_layout)

        # CMYK输入
        cmyk_layout = QHBoxLayout()
        cmyk_label = QLabel("CMYK:")
        cmyk_label.setObjectName("colorInputLabel")
        cmyk_label.setFixedWidth(60)
        self.cmyk_input = LineEdit()
        self.cmyk_input.setPlaceholderText("0,0,0,0")
        self.cmyk_input.setReadOnly(True)
        cmyk_layout.addWidget(cmyk_label)
        cmyk_layout.addWidget(self.cmyk_input)

        cmyk_btn = ToolButton(FIF.COPY)
        cmyk_btn.clicked.connect(lambda: self.copy_color_value(self.cmyk_input.text()))
        cmyk_layout.addWidget(cmyk_btn)

        convert_layout.addLayout(cmyk_layout)

        # 转换按钮
        convert_btn_layout = QHBoxLayout()
        convert_btn_layout.setSpacing(8)

        hex_to_rgb_btn = PushButton("HEX → RGB")
        hex_to_rgb_btn.clicked.connect(self.hex_to_rgb)
        convert_btn_layout.addWidget(hex_to_rgb_btn)

        rgb_to_hex_btn = PushButton("RGB → HEX")
        rgb_to_hex_btn.clicked.connect(self.rgb_to_hex)
        convert_btn_layout.addWidget(rgb_to_hex_btn)

        convert_layout.addLayout(convert_btn_layout)

        left_layout.addWidget(convert_group)
        left_layout.addStretch()

        return left_widget

    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._tab_widget = QTabWidget()
        self._tab_widget.setObjectName("colorPaletteTabWidget")

        # 收藏标签页
        self._favorite_tab = QWidget()
        favorite_layout = QVBoxLayout(self._favorite_tab)
        favorite_layout.setSpacing(8)
        favorite_layout.setContentsMargins(8, 8, 8, 8)

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_input = LineEdit()
        self.search_input.setPlaceholderText("搜索颜色...")
        self.search_input.textChanged.connect(self.search_colors)
        search_layout.addWidget(self.search_input)

        clear_btn = PushButton("清空收藏")
        clear_btn.setIcon(FIF.DELETE)
        clear_btn.clicked.connect(self.clear_colors)
        search_layout.addWidget(clear_btn)

        favorite_layout.addLayout(search_layout)

        # 收藏列表
        self.favorite_list = QListWidget()
        self.favorite_list.setViewMode(QListWidget.IconMode)
        self.favorite_list.setIconSize(QSize(80, 80))
        self.favorite_list.setSpacing(10)
        self.favorite_list.setResizeMode(QListWidget.Adjust)
        self.favorite_list.itemClicked.connect(self.select_favorite_color)
        self.favorite_list.itemDoubleClicked.connect(self.copy_favorite_color)
        self.favorite_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.favorite_list.customContextMenuRequested.connect(self.show_favorite_context_menu)
        favorite_layout.addWidget(self.favorite_list)

        self._tab_widget.addTab(self._favorite_tab, "收藏")

        # 颜色对照表标签页
        self._color_table_tab = self.create_color_table_tab()
        self._tab_widget.addTab(self._color_table_tab, "颜色对照表")

        right_layout.addWidget(self._tab_widget)

        return right_widget

    def create_color_table_tab(self):
        """创建颜色对照表标签页"""
        table_tab = QWidget()
        table_tab.setObjectName("colorTableTabContent")
        table_layout = QVBoxLayout(table_tab)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setSpacing(8)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_widget.setObjectName("colorTableScrollWidget")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        # 常用颜色
        common_colors = {
            "红色系": [
                ("红色", "#FF0000"), ("深红", "#8B0000"), ("暗红", "#DC143C"),
                ("粉红", "#FF69B4"), ("玫瑰红", "#FF007F"), ("珊瑚红", "#FF7F50")
            ],
            "橙色系": [
                ("橙色", "#FFA500"), ("深橙", "#FF8C00"), ("橙红", "#FF4500"),
                ("番茄色", "#FF6347"), ("桃色", "#FFDAB9"), ("杏色", "#FAEBD7")
            ],
            "黄色系": [
                ("黄色", "#FFFF00"), ("金黄", "#FFD700"), ("柠檬黄", "#FFFACD"),
                ("卡其色", "#F0E68C"), ("米色", "#F5F5DC"), ("象牙色", "#FFFFF0")
            ],
            "绿色系": [
                ("绿色", "#008000"), ("深绿", "#006400"), ("春绿", "#00FF7F"),
                ("浅绿", "#90EE90"), ("薄荷绿", "#98FB98"), ("橄榄绿", "#808000")
            ],
            "青色系": [
                ("青色", "#00FFFF"), ("深青", "#008B8B"), ("浅青", "#E0FFFF"),
                ("蓝绿", "#00CED1"), ("天蓝", "#87CEEB"), ("天空蓝", "#87CEFA")
            ],
            "蓝色系": [
                ("蓝色", "#0000FF"), ("深蓝", "#00008B"), ("海军蓝", "#000080"),
                ("钢蓝", "#4682B4"), ("浅蓝", "#ADD8E6"), ("皇家蓝", "#4169E1")
            ],
            "紫色系": [
                ("紫色", "#800080"), ("深紫", "#4B0082"), ("蓝紫", "#8A2BE2"),
                ("紫罗兰", "#EE82EE"), ("淡紫", "#DDA0DD"), ("兰花紫", "#DA70D6")
            ],
            "灰色系": [
                ("黑色", "#000000"), ("深灰", "#2F4F4F"), ("灰色", "#808080"),
                ("银色", "#C0C0C0"), ("浅灰", "#D3D3D3"), ("白色", "#FFFFFF")
            ],
            "棕色系": [
                ("棕色", "#A52A2A"), ("巧克力色", "#D2691E"), ("秘鲁色", "#CD853F"),
                ("沙褐色", "#F4A460"), ("赭石色", "#B8860B"), ("古铜色", "#CD5C5C")
            ]
        }

        for category, colors in common_colors.items():
            category_label = StrongBodyLabel(category)
            scroll_layout.addWidget(category_label)

            grid = QGridLayout()
            grid.setSpacing(8)

            for i, (name, hex_val) in enumerate(colors):
                row = i // 3
                col = i % 3

                color_widget = QFrame()
                color_widget.setFixedHeight(60)
                color_widget_layout = QHBoxLayout(color_widget)
                color_widget_layout.setContentsMargins(8, 4, 8, 4)

                # 颜色块
                color_block = QLabel()
                color_block.setFixedSize(50, 50)
                color_block.setStyleSheet(f"background-color: {hex_val}; border: 1px solid #cccccc; border-radius: 4px;")
                color_widget_layout.addWidget(color_block)

                # 颜色信息
                info_layout = QVBoxLayout()
                info_layout.setSpacing(2)

                name_label = QLabel(name)
                name_label.setStyleSheet("font-weight: bold;")
                info_layout.addWidget(name_label)

                value_label = QLabel(hex_val)
                value_label.setObjectName("colorTableValueLabel")
                value_label.setCursor(Qt.PointingHandCursor)
                value_label.mousePressEvent = lambda e, v=hex_val: self.copy_color_value(v)
                info_layout.addWidget(value_label)

                color_widget_layout.addLayout(info_layout)
                color_widget_layout.addStretch()

                grid.addWidget(color_widget, row, col)

            scroll_layout.addLayout(grid)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        table_layout.addWidget(scroll_area)

        self._table_widget = scroll_widget

        return table_tab

    def toggle_color_picker(self):
        """切换屏幕取色状态"""
        if self.is_picking:
            self.stop_color_picker()
        else:
            self.start_color_picker()

    def start_color_picker(self):
        """开始屏幕取色"""
        self.is_picking = True
        self.pick_button.setText("取消取色 (右键)")
        
        # 最小化主窗口
        main_window = self.window()
        if main_window:
            main_window.showMinimized()
        
        # 创建放大镜窗口
        if not hasattr(self, '_magnifier') or not self._magnifier:
            self._magnifier = MagnifierWindow()
        self._magnifier.show()
        
        # 安装鼠标Hook
        hook_success = install_mouse_hook(self.on_mouse_click)
        
        if hook_success:
            # 创建定时器持续更新放大镜
            self.pick_timer = QTimer(self)
            self.pick_timer.timeout.connect(self.update_magnifier)
            self.pick_timer.start(30)  # 每30ms更新一次
            
            # 修改鼠标光标
            QApplication.setOverrideCursor(Qt.CrossCursor)
        else:
            self.is_picking = False
            self.pick_button.setText("屏幕取色")
            if hasattr(self, '_magnifier'):
                self._magnifier.hide()
            InfoBar.error(
                title="错误",
                content="无法启动屏幕取色功能",
                parent=self,
                duration=2000
            )

    def update_magnifier(self):
        """更新放大镜显示"""
        if not self.is_picking:
            return
        
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()
        
        if screen and hasattr(self, '_magnifier'):
            self._magnifier.update_magnifier(cursor_pos, screen)

    def stop_color_picker(self):
        """停止屏幕取色"""
        if not self.is_picking:
            return
            
        self.is_picking = False
        self.pick_button.setText("屏幕取色")
        
        # 停止定时器
        if self.pick_timer:
            self.pick_timer.stop()
            self.pick_timer = None
        
        # 隐藏放大镜
        if hasattr(self, '_magnifier'):
            self._magnifier.hide()
        
        # 卸载Hook
        uninstall_mouse_hook()
        
        # 恢复鼠标光标
        QApplication.restoreOverrideCursor()
        
        # 恢复主窗口
        main_window = self.window()
        if main_window:
            if hasattr(main_window, 'show_and_activate'):
                main_window.show_and_activate()
            else:
                main_window.show()
                main_window.activateWindow()

    def update_pick_color(self):
        """更新鼠标位置的颜色预览"""
        if not self.is_picking:
            return
        
        try:
            # 获取当前鼠标位置的颜色
            color = self.get_color_at_cursor()
            if color and color.isValid():
                # 显示提示（不更新到界面，只预览）
                cursor_pos = QCursor.pos()
                tooltip_text = f"RGB: {color.red()}, {color.green()}, {color.blue()}\n{color.name()}"
                QToolTip.showText(cursor_pos + QPoint(10, 10), tooltip_text)
        except Exception as e:
            # 忽略错误继续运行
            pass

    def get_color_at_cursor(self):
        """获取鼠标当前位置的颜色"""
        try:
            cursor_pos = QCursor.pos()
            screen = QApplication.primaryScreen()
            if screen:
                pixmap = screen.grabWindow(0, cursor_pos.x(), cursor_pos.y(), 1, 1)
                image = pixmap.toImage()
                if not image.isNull():
                    return QColor(image.pixel(0, 0))
        except Exception as e:
            pass
        return None

    def on_mouse_click(self, wParam):
        """鼠标点击回调"""
        if not self.is_picking:
            return
        
        if wParam == WM_LBUTTONDOWN:
            # 左键点击 - 获取放大镜窗口记录的颜色
            color = None
            if hasattr(self, '_magnifier'):
                color = self._magnifier.get_last_color()
            
            if not color or not color.isValid():
                color = self.get_color_at_cursor()
            
            if color and color.isValid():
                self.stop_color_picker()
                self.set_color(color)
                InfoBar.success(
                    title="颜色已选择",
                    content=f"已选择颜色: {color.name()}",
                    parent=self,
                    duration=2000
                )
            else:
                self.stop_color_picker()
        elif wParam == WM_RBUTTONDOWN:
            # 右键点击 - 取消
            self.stop_color_picker()
            InfoBar.info(
                title="已取消",
                content="已取消屏幕取色",
                parent=self,
                duration=2000
            )

    def open_color_dialog(self):
        """打开颜色选择对话框"""
        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.set_color(color)

    def set_color(self, color: QColor):
        """设置当前颜色"""
        if not color.isValid():
            return

        self.current_color = color

        # 更新颜色显示
        self.color_display.setStyleSheet(
            f"background-color: {color.name()}; "
            f"border: 2px solid #cccccc; border-radius: 8px;"
        )

        # 更新颜色信息
        self.color_name_label.setText(color.name().upper())
        self.color_info_label.setText(
            f"RGB: {color.red()}, {color.green()}, {color.blue()}"
        )

        # 更新输入框
        if not self.updating_display:
            self.updating_display = True
            self.hex_input.setText(color.name().upper())
            self.rgb_input.setText(f"{color.red()},{color.green()},{color.blue()}")

            # 更新HSV
            h, s, v = color.hsvHue(), color.hsvSaturation(), color.value()
            if h < 0:
                h = 0
            self.hsv_input.setText(f"{h},{s},{v}")

            # 更新CMYK
            c, m, y, k = color.cyan(), color.magenta(), color.yellow(), color.black()
            self.cmyk_input.setText(f"{c},{m},{y},{k}")

            self.updating_display = False

        self.color_changed.emit(color.name())

    def hex_input_changed(self):
        """HEX输入框变化"""
        if self.updating_display:
            return

        hex_text = self.hex_input.text().strip()
        if not hex_text.startswith('#'):
            hex_text = '#' + hex_text

        color = QColor(hex_text)
        if color.isValid():
            self.set_color(color)

    def rgb_input_changed(self):
        """RGB输入框变化"""
        if self.updating_display:
            return

        rgb_text = self.rgb_input.text().strip()
        try:
            parts = [int(x.strip()) for x in rgb_text.split(',')]

            if len(parts) >= 3:
                r, g, b = parts[0], parts[1], parts[2]
                a = parts[3] if len(parts) > 3 else 255

                if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255 and 0 <= a <= 255:
                    color = QColor(r, g, b, a)
                    self.set_color(color)
        except (ValueError, IndexError):
            pass

    def hex_to_rgb(self):
        """HEX 转 RGB"""
        hex_text = self.hex_input.text().strip()
        if hex_text.startswith('#'):
            hex_text = hex_text[1:]

        if len(hex_text) in [3, 6]:
            try:
                if len(hex_text) == 3:
                    hex_text = ''.join([c * 2 for c in hex_text])
                r = int(hex_text[0:2], 16)
                g = int(hex_text[2:4], 16)
                b = int(hex_text[4:6], 16)
                self.rgb_input.setText(f"{r},{g},{b}")
            except ValueError:
                InfoBar.warning(
                    title="转换错误",
                    content="无效的 HEX 颜色值",
                    parent=self,
                    duration=2000
                )

    def rgb_to_hex(self):
        """RGB 转 HEX"""
        rgb_text = self.rgb_input.text().strip()
        try:
            parts = [int(x.strip()) for x in rgb_text.split(',')]
            if len(parts) >= 3:
                r, g, b = parts[0], parts[1], parts[2]
                if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                    hex_val = f"#{r:02X}{g:02X}{b:02X}"
                    self.hex_input.setText(hex_val)
                else:
                    InfoBar.warning(
                        title="转换错误",
                        content="RGB 值必须在 0-255 范围内",
                        parent=self,
                        duration=2000
                    )
            else:
                InfoBar.warning(
                    title="转换错误",
                    content="RGB 格式应为：R,G,B",
                    parent=self,
                    duration=2000
                )
        except (ValueError, IndexError):
            InfoBar.warning(
                title="转换错误",
                content="无效的 RGB 颜色值",
                parent=self,
                duration=2000
            )

    def save_color_to_db(self):
        """保存颜色到数据库"""
        color_hex = self.current_color.name()
        color_rgb = f"{self.current_color.red()},{self.current_color.green()},{self.current_color.blue()}"

        if self.service.color_exists(color_hex):
            InfoBar.warning(
                title="已存在",
                content=f"颜色 {color_hex} 已存在于数据库中",
                parent=self,
                duration=2000
            )
            return

        color_name = color_hex
        self.service.add_color(
            name=color_name,
            color_hex=color_hex,
            color_rgb=color_rgb
        )

        InfoBar.success(
            title="保存成功",
            content=f"颜色 {color_name} 已保存到数据库",
            parent=self,
            duration=2000
        )
        self.load_colors()

    def load_colors(self):
        """加载颜色列表"""
        self.favorite_list.clear()
        colors = self.service.list_colors()

        for color_data in colors:
            item = QListWidgetItem()
            item.setText(color_data['color_hex'])
            item.setToolTip(f"{color_data['name']}\n{color_data['color_hex']}\n{color_data['color_rgb']}")

            pixmap = QPixmap(80, 80)
            pixmap.fill(QColor(color_data['color_hex']))

            icon = QIcon(pixmap)
            item.setIcon(icon)

            self.favorite_list.addItem(item)

    def select_favorite_color(self, item):
        """选择收藏颜色"""
        color_str = item.text()
        color = QColor(color_str)
        if color.isValid():
            self.set_color(color)

    def clear_colors(self):
        """清空颜色"""
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            "确定要清空所有收藏的颜色吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.service.clear_colors()
            self.load_colors()
            InfoBar.success(
                title="清空成功",
                content="已清空所有收藏的颜色",
                parent=self,
                duration=2000
            )

    def search_colors(self, keyword):
        """搜索颜色"""
        self.favorite_list.clear()
        if not keyword:
            self.load_colors()
            return

        colors = self.service.search_colors(keyword)
        for color_data in colors:
            item = QListWidgetItem()
            item.setText(color_data['color_hex'])
            item.setToolTip(f"{color_data['name']}\n{color_data['color_hex']}\n{color_data['color_rgb']}")

            pixmap = QPixmap(80, 80)
            pixmap.fill(QColor(color_data['color_hex']))

            icon = QIcon(pixmap)
            item.setIcon(icon)

            self.favorite_list.addItem(item)

    def copy_color_value(self, value):
        """复制颜色值"""
        app_clipboard = QApplication.clipboard()
        app_clipboard.setText(value)
        QToolTip.showText(QCursor.pos(), f"已复制：{value}")

    def copy_favorite_color(self, item):
        """双击复制收藏颜色"""
        color_str = item.text()
        self.copy_color_value(color_str)

    def show_favorite_context_menu(self, position):
        """显示收藏右键菜单"""
        selected_items = self.favorite_list.selectedItems()
        if not selected_items:
            return

        menu = QMenu()

        delete_action = QAction("删除所选颜色", self)
        delete_action.triggered.connect(lambda: self.delete_favorite_color(selected_items))
        menu.addAction(delete_action)

        menu.exec_(self.favorite_list.viewport().mapToGlobal(position))

    def delete_favorite_color(self, items):
        """删除收藏颜色"""
        if not items:
            return

        count = len(items)
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除这 {count} 个颜色吗？",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.service.delete_colors_by_hex([item.text() for item in items])

            self.load_colors()
            InfoBar.success(
                title="删除成功",
                content=f"已删除 {count} 个颜色",
                parent=self,
                duration=2000
            )

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 确保停止取色
        if self.is_picking:
            self.stop_color_picker()
        super().closeEvent(event)


class Plugin(PluginInterface):
    """调色板插件"""

    PLUGIN_ID = "color_palette"
    PLUGIN_NAME = "调色板"
    PLUGIN_ICON = FIF.PALETTE
    PLUGIN_PRIORITY = 13

    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")

    def shutdown(self) -> None:
        """关闭插件"""
        # 确保清理Hook
        uninstall_mouse_hook()
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")

    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return ColorPaletteWidget(self.core, parent)

    def _do_load_data(self) -> None:
        """加载数据"""
        if self._widget is None:
            return
        pass

    def supports_search(self) -> bool:
        """支持全局搜索"""
        return True

    def search(self, query: str):
        """搜索颜色"""
        service = ColorPaletteService(self.PLUGIN_ID)
        results = []
        colors = service.search_colors(query)
        for color in colors[:20]:
            result = SearchResult(
                plugin_id=self.PLUGIN_ID,
                plugin_name=self.get_name(),
                title=color['name'],
                description=f"HEX: {color['color_hex']} | RGB: {color['color_rgb']}",
                icon=self.PLUGIN_ICON,
                relevance=1.0 if query in color['name'].lower() else 0.5,
                action=lambda c=color: self._copy_color(c),
                metadata={'color_id': color['id']}
            )
            results.append(result)
        return results

    def _copy_color(self, color: Dict[str, Any]) -> None:
        """复制颜色值到剪贴板"""
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QCursor
        from qfluentwidgets import QToolTip
        color_hex = color.get('color_hex', '')
        if color_hex:
            app_clipboard = QApplication.clipboard()
            app_clipboard.setText(color_hex)
            QToolTip.showText(QCursor.pos(), f"已复制：{color_hex}")
