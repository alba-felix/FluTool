"""
系统工具插件
提供 Windows 系统常用工具的快捷访问
"""
import os
import subprocess
from typing import List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QApplication
from qfluentwidgets import (
    PushButton, LineEdit, FluentIcon as FIF,
    InfoBar, InfoBarPosition, CardWidget, StrongBodyLabel
)
from core.plugin_interface import PluginInterface
from ui.custom_icon import CustomFluentIcon


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
        self._setup_ui()
    
    def _setup_ui(self):
        """构建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
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
        
        main_layout.addWidget(search_card)
        
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
            ("注册表编辑器", "regedit", FIF.SETTING, True, ["注册表", "regedit", "registry"]),
            ("设备管理器", "devmgmt.msc", FIF.APPLICATION, True, ["设备", "devmgmt", "硬件"]),
            ("磁盘管理", "diskmgmt.msc", FIF.SAVE, True, ["磁盘", "diskmgmt", "分区"]),
            ("服务管理", "services.msc", FIF.SETTING, True, ["服务", "services", "管理"]),
            
            ("环境变量", "rundll32 sysdm.cpl,EditEnvironmentVariables", FIF.EDIT, False, ["环境变量", "environment", "变量"]),
            ("任务管理器", "taskmgr", FIF.CALENDAR, False, ["任务", "taskmgr", "管理器"]),
            ("控制面板", "control", FIF.MENU, False, ["控制面板", "control", "设置"]),
            ("命令提示符", "cmd", FIF.COMMAND_PROMPT, True, ["命令", "cmd", "控制台"]),
            
            ("PowerShell", "powershell", FIF.CODE, True, ["powershell", "脚本", "命令"]),
            ("网络连接", "ncpa.cpl", FIF.GLOBE, True, ["网络", "ncpa", "连接"]),
            ("防火墙", "wf.msc", FIF.CERTIFICATE, True, ["防火墙", "firewall", "安全"]),
            ("计算机管理", "compmgmt.msc", FIF.APPLICATION, True, ["计算机", "compmgmt", "管理"]),
            
            ("系统配置", "msconfig", FIF.SETTING, True, ["系统配置", "msconfig", "启动"]),
            ("磁盘清理", "cleanmgr", FIF.DELETE, False, ["磁盘清理", "cleanmgr", "清理"]),
            ("事件查看器", "eventvwr", FIF.INFO, True, ["事件", "eventvwr", "日志"]),
            ("远程桌面", "mstsc", FIF.VIDEO, False, ["远程桌面", "mstsc", "远程"]),
            
            ("系统信息", "msinfo32", FIF.INFO, False, ["系统信息", "msinfo32", "信息"]),
            ("性能监视器", "perfmon", FIF.STOP_WATCH, True, ["性能", "perfmon", "监视"]),
            ("资源监视器", "resmon", FIF.MUSIC, True, ["资源", "resmon", "监视"]),
            ("DirectX诊断", "dxdiag", FIF.GAME, False, ["directx", "dxdiag", "诊断"]),
            
            ("程序和功能", "appwiz.cpl", FIF.FOLDER, True, ["程序", "appwiz", "卸载"]),
            ("系统属性", "sysdm.cpl", FIF.SETTING, True, ["系统属性", "sysdm", "属性"]),
            ("Windows功能", "optionalfeatures", FIF.ADD, True, ["windows功能", "功能", "features"]),
            ("回收站", "explorer shell:RecycleBinFolder", FIF.DELETE, False, ["回收站", "recycle", "垃圾桶"]),
        ]
        
        # 创建按钮
        for i, (name, command, icon, admin, keywords) in enumerate(tools):
            btn = PushButton(name, self)
            btn.setIcon(icon)
            btn.setFixedHeight(40)
            btn.setProperty("command", command)
            btn.setProperty("admin", admin)
            btn.setProperty("keywords", keywords)
            btn.clicked.connect(lambda checked, c=command, a=admin, n=name: self._open_tool(c, a, n))
            
            self.buttons.append(btn)
            row = i // 4  # 一行4个按钮
            col = i % 4
            self.button_grid.addWidget(btn, row, col)
        
        tools_layout.addLayout(self.button_grid)
        main_layout.addWidget(tools_card)
        
        # 底部提示
        main_layout.addStretch(1)
    
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
    PLUGIN_ICON = CustomFluentIcon.SYSTEM
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
