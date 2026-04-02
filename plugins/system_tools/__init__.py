"""
系统工具插件
提供 Windows 系统常用工具的快捷访问
"""
import os
import subprocess
from typing import List, Tuple

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QApplication
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, CardWidget, StrongBodyLabel,
    SmoothScrollArea
)
from core import PluginInterface
from ui import CustomFluentIcon as CFIF


class SystemTools:
    """Windows 系统工具类"""
    
    @staticmethod
    def run_command(command: str, admin: bool = False) -> bool:
        """
        执行系统命令
        
        Args:
            command: 要执行的命令
            admin: 是否以管理员权限运行
            
        Returns:
            是否成功
        """
        try:
            if admin:
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(None, "runas", command, None, None, 1)
            else:
                subprocess.Popen(command, shell=True)
            return True
        except Exception as e:
            print(f"执行命令失败: {e}")
            return False
    
    @staticmethod
    def open_tool(command: str, admin: bool = False, tool_name: str = "") -> Tuple[bool, str]:
        """
        打开系统工具
        
        Args:
            command: 工具命令
            admin: 是否需要管理员权限
            tool_name: 工具名称（用于提示信息）
            
        Returns:
            (是否成功, 提示信息)
        """
        success = SystemTools.run_command(command, admin)
        if success:
            msg = f"已打开 {tool_name}" + (" (管理员模式)" if admin else "")
            return True, msg
        else:
            return False, f"打开 {tool_name} 失败"


class SystemToolsWidget(QWidget):
    """系统工具组件"""
    
    PLUGIN_ID = "system_tools"
    
    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.buttons = []
        self._init_scroll_buttons()
        self._setup_ui()
    
    def _init_scroll_buttons(self):
        """初始化滚动按钮"""
        self._up_btn = PushButton("", self)
        self._up_btn.setIcon(FIF.CARE_UP_SOLID)
        self._up_btn.setFixedSize(48, 24)
        self._up_btn.setCursor(Qt.PointingHandCursor)
        self._up_btn.hide()
        self._up_btn.clicked.connect(self._scroll_up)
        
        self._down_btn = PushButton("", self)
        self._down_btn.setIcon(FIF.CARE_DOWN_SOLID)
        self._down_btn.setFixedSize(48, 24)
        self._down_btn.setCursor(Qt.PointingHandCursor)
        self._down_btn.hide()
        self._down_btn.clicked.connect(self._scroll_down)
    
    def _scroll_up(self):
        if hasattr(self, '_scroll_area'):
            bar = self._scroll_area.verticalScrollBar()
            bar.setValue(bar.value() - 100)
    
    def _scroll_down(self):
        if hasattr(self, '_scroll_area'):
            bar = self._scroll_area.verticalScrollBar()
            bar.setValue(bar.value() + 100)
    
    def _check_scroll_buttons(self):
        """检查并更新滚动按钮显示"""
        if not hasattr(self, '_scroll_area'):
            return
        widget_height = self._scroll_widget.height()
        viewport_height = self._scroll_area.viewport().height()
        
        if widget_height > viewport_height:
            bar = self._scroll_area.verticalScrollBar()
            self._up_btn.setVisible(bar.value() > 0)
            self._down_btn.setVisible(bar.value() < bar.maximum())
        else:
            self._up_btn.hide()
            self._down_btn.hide()
    
    def resizeEvent(self, e):
        """窗口大小改变时检查滚动按钮"""
        super().resizeEvent(e)
        self._check_scroll_buttons()
    
    def _setup_ui(self):
        """构建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 向上滚动按钮
        up_container = QWidget()
        up_layout = QHBoxLayout(up_container)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.addStretch()
        up_layout.addWidget(self._up_btn)
        
        # 滚动区域
        self._scroll_area = SmoothScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # 滚动内容widget
        self._scroll_widget = QWidget()
        self._scroll_widget.setStyleSheet("background: transparent;")
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setSpacing(16)
        self._scroll_layout.setContentsMargins(20, 20, 20, 20)
        
        self._scroll_area.setWidget(self._scroll_widget)
        
        # 向下滚动按钮
        down_container = QWidget()
        down_layout = QHBoxLayout(down_container)
        down_layout.setContentsMargins(0, 0, 0, 0)
        down_layout.addStretch()
        down_layout.addWidget(self._down_btn)
        
        # 添加到主布局
        main_layout.addWidget(up_container)
        main_layout.addWidget(self._scroll_area, 1)
        main_layout.addWidget(down_container)
        
        # === 搜索区域 ===
        search_card = CardWidget(self)
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(16, 12, 16, 12)
        
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText("搜索系统工具...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_buttons)
        
        search_layout.addWidget(StrongBodyLabel("搜索:"))
        search_layout.addWidget(self.search_input, 1)
        
        self._scroll_layout.addWidget(search_card)
        
        # === 工具按钮区域 ===
        tools_card = CardWidget(self)
        tools_layout = QVBoxLayout(tools_card)
        tools_layout.setContentsMargins(16, 16, 16, 16)
        tools_layout.setSpacing(12)
        
        # 按钮网格布局 - 一行4个按钮
        self.button_grid = QGridLayout()
        self.button_grid.setSpacing(8)
        
        # 定义工具列表 (名称, 命令, 图标, 是否管理员, 关键词)
        tools = [
            ("注册表编辑器", "regedit", CFIF.REGEDIT, True, ["注册表", "regedit", "registry"]),
            ("设备管理器", "devmgmt.msc", CFIF.DEVICE, True, ["设备", "devmgmt", "硬件"]),
            ("磁盘管理", "diskmgmt.msc", CFIF.DISK, True, ["磁盘", "diskmgmt", "分区"]),
            ("服务管理", "services.msc", CFIF.SERVICES, True, ["服务", "services", "管理"]),
            
            ("环境变量", "rundll32 sysdm.cpl,EditEnvironmentVariables", CFIF.ENV, False, ["环境变量", "environment", "变量"]),
            ("任务管理器", "taskmgr", CFIF.TASK, False, ["任务", "taskmgr", "管理器"]),
            ("控制面板", "control", CFIF.CONTROL_PANEL, False, ["控制面板", "control", "设置"]),
            ("命令提示符", "cmd", CFIF.CMD, True, ["命令", "cmd", "控制台"]),
            
            ("PowerShell", "powershell", CFIF.POWERSHELL, True, ["powershell", "脚本", "命令"]),
            ("网络连接", "ncpa.cpl", FIF.GLOBE, True, ["网络", "ncpa", "连接"]),
            ("防火墙", "wf.msc", CFIF.NETFW, True, ["防火墙", "firewall", "安全"]),
            ("计算机管理", "compmgmt.msc", CFIF.COMPUTER, True, ["计算机", "compmgmt", "管理"]),
            
            ("系统配置", "msconfig", CFIF.SYSCONFIG, True, ["系统配置", "msconfig", "启动"]),
            ("磁盘清理", "cleanmgr", FIF.DELETE, False, ["磁盘清理", "cleanmgr", "清理"]),
            ("事件查看器", "eventvwr", CFIF.WINVIEW, True, ["事件", "eventvwr", "日志"]),
            ("远程桌面", "mstsc", CFIF.DESK, False, ["远程桌面", "mstsc", "远程"]),
            
            ("系统信息", "msinfo32", FIF.INFO, False, ["系统信息", "msinfo32", "信息"]),
            ("性能监视器", "perfmon", FIF.STOP_WATCH, True, ["性能", "perfmon", "监视"]),
            ("资源监视器", "resmon", FIF.MUSIC, True, ["资源", "resmon", "监视"]),
            ("DirectX诊断", "dxdiag", FIF.GAME, False, ["directx", "dxdiag", "诊断"]),
            
            ("程序和功能", "appwiz.cpl", FIF.FOLDER, True, ["程序", "appwiz", "卸载"]),
            ("系统属性", "sysdm.cpl", FIF.SETTING, True, ["系统属性", "sysdm", "属性"]),
            ("Windows功能", "optionalfeatures", FIF.ADD, True, ["windows功能", "功能", "features"]),
            ("回收站", "explorer shell:RecycleBinFolder", CFIF.RECYCLE_BIN, False, ["回收站", "recycle", "垃圾桶"]),
            ("组策略", "gpedit.msc", CFIF.GROUP_POLICY, True, ["组策略", "gpedit", "策略", "gpo"]),
            ("任务计划程序", "taskschd.msc", FIF.STOP_WATCH, True, ["任务计划", "taskschd", "计划任务", "task"]),
        ]
        
        # 创建按钮
        for i, (name, command, icon, admin, keywords) in enumerate(tools):
            btn = PushButton(name, self)
            btn.setIcon(icon)
            btn.setFixedHeight(40)
            btn.setProperty("command", command)
            btn.setProperty("admin", admin)
            btn.setProperty("keywords", keywords)
            btn.setToolTip(command)
            btn.clicked.connect(lambda checked, c=command, a=admin, n=name: self._open_tool(c, a, n))
            
            self.buttons.append(btn)
            row = i // 4  # 一行4个按钮
            col = i % 4
            self.button_grid.addWidget(btn, row, col)
        
        tools_layout.addLayout(self.button_grid)
        self._scroll_layout.addWidget(tools_card)
        
        # 底部提示
        self._scroll_layout.addStretch(1)
    
    def _open_tool(self, command: str, admin: bool, name: str):
        """打开系统工具"""
        success, message = SystemTools.open_tool(command, admin, name)
        
        if success:
            InfoBar.success(
                title="打开成功",
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        else:
            InfoBar.error(
                title="打开失败",
                content=message,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def _filter_buttons(self, text: str):
        """根据搜索文本过滤按钮"""
        search_text = text.lower().strip()
        
        # 重新布局按钮
        row = 0
        col = 0
        
        for button in self.buttons:
            # 获取按钮的关键词和文本
            keywords = button.property("keywords") or []
            button_text = button.text().lower()
            
            # 检查是否匹配搜索条件
            is_match = False
            if not search_text:  # 空搜索显示所有按钮
                is_match = True
            else:
                # 检查按钮文本是否包含搜索词
                if search_text in button_text:
                    is_match = True
                # 检查关键词是否包含搜索词
                else:
                    for keyword in keywords:
                        if search_text in keyword.lower():
                            is_match = True
                            break
            
            # 显示或隐藏按钮
            button.setVisible(is_match)
            
            # 如果按钮可见，重新布局
            if is_match:
                self.button_grid.addWidget(button, row, col)
                col += 1
                if col >= 4:  # 一行4个按钮
                    col = 0
                    row += 1


class Plugin(PluginInterface):
    """系统工具插件"""
    
    PLUGIN_ID = "system_tools"
    PLUGIN_NAME = "系统工具"
    PLUGIN_ICON = CFIF.SYSTEM
    PLUGIN_PRIORITY = 5
    
    def initialize(self, core) -> None:
        """初始化插件"""
        self.core = core
        core.logger.info(f"Plugin '{self.PLUGIN_NAME}' initialized")
    
    def shutdown(self) -> None:
        """关闭插件"""
        self.core.logger.info(f"Plugin '{self.PLUGIN_NAME}' shutdown")
    
    def _create_widget(self, parent=None) -> QWidget:
        """创建插件界面"""
        return SystemToolsWidget(self.core, parent)
    
    def load_data(self) -> None:
        """加载数据"""
        pass
