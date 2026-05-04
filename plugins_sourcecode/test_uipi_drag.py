"""拖拽测试 - 完整的 UIPI 绕过方案"""
import sys
import os
import ctypes
from ctypes import wintypes, c_void_p, POINTER, byref, c_long

print('='*60)
print('UIPI 拖拽绕过测试')
print('='*60)

# 检查管理员权限
try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    print(f'管理员权限: {"是" if is_admin else "否"}')
except:
    is_admin = False

print('='*60)

# Windows 常量
WM_DROPFILES = 0x0233
WM_COPYDATA = 0x004A
WM_COPYGLOBALDATA = 0x0049
MSGFLT_ALLOW = 1
S_OK = 0

user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32
shell32 = ctypes.windll.shell32

class CHANGEFILTERSTRUCT(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("cInFlight", wintypes.DWORD),
    ]

def enable_drag_for_hwnd(hwnd):
    """为指定窗口启用拖拽"""
    print(f'为窗口 0x{hwnd:08X} 启用拖拽...')
    
    # 1. 使用 ChangeWindowMessageFilterEx
    user32.ChangeWindowMessageFilterEx.argtypes = [
        wintypes.HWND, wintypes.UINT, wintypes.DWORD,
        POINTER(CHANGEFILTERSTRUCT)
    ]
    user32.ChangeWindowMessageFilterEx.restype = wintypes.BOOL
    
    cfs = CHANGEFILTERSTRUCT()
    cfs.cbSize = ctypes.sizeof(CHANGEFILTERSTRUCT)
    
    messages = [WM_DROPFILES, WM_COPYDATA, WM_COPYGLOBALDATA]
    for msg in messages:
        result = user32.ChangeWindowMessageFilterEx(hwnd, msg, MSGFLT_ALLOW, byref(cfs))
        print(f'  ChangeWindowMessageFilterEx(0x{msg:04X}): {"✓" if result else "✗"}')
    
    # 2. 尝试使用 AllowDropTargetWindow (Windows 8+)
    try:
        # 这个函数可能不存在于所有 Windows 版本
        user32.AllowDropTargetWindow.argtypes = [wintypes.HWND]
        user32.AllowDropTargetWindow.restype = wintypes.BOOL
        result = user32.AllowDropTargetWindow(hwnd)
        print(f'  AllowDropTargetWindow: {"✓" if result else "✗/不可用"}')
    except Exception as e:
        print(f'  AllowDropTargetWindow: 不可用')
    
    # 3. 初始化 OLE
    ole32.OleInitialize.argtypes = [c_void_p]
    ole32.OleInitialize.restype = c_long
    result = ole32.OleInitialize(None)
    if result == S_OK:
        print('  OLE 初始化: ✓')
    elif result == 0x80010106:  # RPC_E_CHANGED_MODE
        print('  OLE 初始化: 已初始化')
    else:
        print(f'  OLE 初始化: 失败 0x{result:08X}')
    
    # 4. 尝试 RevokeDragDrop + RegisterDragDrop
    try:
        ole32.RevokeDragDrop.argtypes = [wintypes.HWND]
        ole32.RevokeDragDrop.restype = c_long
        ole32.RevokeDragDrop(hwnd)  # 先撤销
        
        # 这里需要实现 IDropTarget 接口，比较复杂
        print('  RevokeDragDrop: ✓')
    except Exception as e:
        print(f'  RevokeDragDrop: {e}')
    
    # 5. 设置窗口属性
    try:
        # 设置窗口为接受文件拖放
        GWL_EXSTYLE = -20
        WS_EX_ACCEPTFILES = 0x00000010
        
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, c_long]
        user32.GetWindowLongPtrW.restype = c_long
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, c_long, c_long]
        user32.SetWindowLongPtrW.restype = c_long
        
        style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_ACCEPTFILES)
        print('  WS_EX_ACCEPTFILES: ✓')
    except Exception as e:
        print(f'  WS_EX_ACCEPTFILES: {e}')
    
    # 6. 尝试 ChangeWindowMessageFilter (全局)
    try:
        user32.ChangeWindowMessageFilter.argtypes = [wintypes.UINT, wintypes.DWORD]
        user32.ChangeWindowMessageFilter.restype = wintypes.BOOL
        
        for msg in messages:
            result = user32.ChangeWindowMessageFilter(msg, 1)  # MSGFLT_ADD
        print('  全局消息过滤器: ✓')
    except Exception as e:
        print(f'  全局消息过滤器: {e}')

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt5.QtCore import Qt, QTimer


class DropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('UIPI 拖拽绕过测试')
        self.resize(500, 450)
        self.setAcceptDrops(True)
        
        layout = QVBoxLayout(self)
        
        self.label = QLabel('拖放文件或文件夹到这里\n(从资源管理器拖拽)')
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet('''
            QLabel {
                border: 3px dashed #888;
                border-radius: 10px;
                background-color: #f5f5f5;
                font-size: 16px;
                color: #666;
            }
        ''')
        layout.addWidget(self.label)
        
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(180)
        layout.addWidget(self.log)
        
        self._log('窗口已就绪')
        
        # 延迟启用拖拽
        QTimer.singleShot(200, self._enable_drag)
    
    def _enable_drag(self):
        hwnd = int(self.winId())
        self._log(f'窗口句柄: 0x{hwnd:08X}')
        enable_drag_for_hwnd(hwnd)
        self._log('拖拽支持已启用!')
        self._log('请从资源管理器拖拽文件测试')
    
    def _log(self, msg):
        self.log.append(f'> {msg}')
        print(f'[LOG] {msg}')
    
    def dragEnterEvent(self, event):
        self._log('>>> dragEnterEvent 触发!')
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._log('    已接受')
            self.label.setStyleSheet('''
                QLabel {
                    border: 3px dashed #0078d4;
                    border-radius: 10px;
                    background-color: #e3f2fd;
                    font-size: 16px;
                    color: #0078d4;
                }
            ''')
        else:
            event.ignore()
            self._log('    已忽略')
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        self.label.setStyleSheet('''
            QLabel {
                border: 3px dashed #888;
                border-radius: 10px;
                background-color: #f5f5f5;
                font-size: 16px;
                color: #666;
            }
        ''')
    
    def dropEvent(self, event):
        self.label.setStyleSheet('''
            QLabel {
                border: 3px dashed #888;
                border-radius: 10px;
                background-color: #f5f5f5;
                font-size: 16px;
                color: #666;
            }
        ''')
        
        urls = event.mimeData().urls()
        self._log(f'>>> dropEvent 触发! 接收到 {len(urls)} 个项目')
        for url in urls:
            self._log(f'    {url.toLocalFile()}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    window = DropWidget()
    window.show()
    
    ret = app.exec_()
    
    # 清理
    ole32.OleUninitialize.argtypes = []
    ole32.OleUninitialize()
    
    sys.exit(ret)
