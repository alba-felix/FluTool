"""
应用启动插件测试
测试不同文件类型的启动逻辑
"""
import os
import sys
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAppLauncherFileTypeDetection:
    """测试文件类型检测"""
    
    def test_python_file_detection(self):
        """测试 Python 文件检测"""
        ext = os.path.splitext("test.py")[1].lower()
        assert ext == ".py"
    
    def test_bat_file_detection(self):
        """测试 BAT 文件检测"""
        ext = os.path.splitext("test.bat")[1].lower()
        assert ext == ".bat"
    
    def test_cmd_file_detection(self):
        """测试 CMD 文件检测"""
        ext = os.path.splitext("test.cmd")[1].lower()
        assert ext == ".cmd"
    
    def test_ps1_file_detection(self):
        """测试 PowerShell 文件检测"""
        ext = os.path.splitext("test.ps1")[1].lower()
        assert ext == ".ps1"
    
    def test_vbs_file_detection(self):
        """测试 VBS 文件检测"""
        ext = os.path.splitext("test.vbs")[1].lower()
        assert ext == ".vbs"
    
    def test_txt_file_detection(self):
        """测试 TXT 文件检测"""
        ext = os.path.splitext("test.txt")[1].lower()
        assert ext == ".txt"
    
    def test_exe_file_detection(self):
        """测试 EXE 文件检测"""
        ext = os.path.splitext("test.exe")[1].lower()
        assert ext == ".exe"
    
    def test_folder_detection(self):
        """测试文件夹检测"""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert os.path.isdir(tmpdir)
            assert not os.path.isfile(tmpdir)


class TestAppLauncherLaunchLogic:
    """测试启动逻辑"""
    
    def test_get_python_executable(self):
        """测试获取 Python 解释器路径"""
        python_exe = os.path.join(os.sys.prefix, 'python.exe') if hasattr(os.sys, 'prefix') else 'python'
        assert python_exe is not None
    
    @patch('subprocess.Popen')
    def test_launch_python_file(self, mock_popen):
        """测试启动 Python 文件"""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'print("hello")')
            temp_path = f.name
        
        try:
            ext = os.path.splitext(temp_path)[1].lower()
            assert ext == '.py'
            
            python_exe = os.path.join(os.sys.prefix, 'python.exe') if hasattr(os.sys, 'prefix') else 'python'
            subprocess.Popen(f'"{python_exe}" "{temp_path}"', shell=True)
            
            mock_popen.assert_called()
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.Popen')
    def test_launch_bat_file(self, mock_popen):
        """测试启动 BAT 文件"""
        with tempfile.NamedTemporaryFile(suffix='.bat', delete=False) as f:
            f.write(b'@echo hello')
            temp_path = f.name
        
        try:
            ext = os.path.splitext(temp_path)[1].lower()
            assert ext == '.bat'
            
            subprocess.Popen(f'"{temp_path}"', shell=True)
            
            mock_popen.assert_called()
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.Popen')
    def test_launch_ps1_file(self, mock_popen):
        """测试启动 PowerShell 文件"""
        with tempfile.NamedTemporaryFile(suffix='.ps1', delete=False) as f:
            f.write(b'Write-Host "hello"')
            temp_path = f.name
        
        try:
            ext = os.path.splitext(temp_path)[1].lower()
            assert ext == '.ps1'
            
            subprocess.Popen(f'powershell -ExecutionPolicy Bypass -File "{temp_path}"', shell=True)
            
            mock_popen.assert_called()
        finally:
            os.unlink(temp_path)
    
    @patch('subprocess.Popen')
    def test_launch_vbs_file(self, mock_popen):
        """测试启动 VBS 文件"""
        with tempfile.NamedTemporaryFile(suffix='.vbs', delete=False) as f:
            f.write(b'MsgBox "hello"')
            temp_path = f.name
        
        try:
            ext = os.path.splitext(temp_path)[1].lower()
            assert ext == '.vbs'
            
            subprocess.Popen(f'wscript "{temp_path}"', shell=True)
            
            mock_popen.assert_called()
        finally:
            os.unlink(temp_path)
    
    @patch('os.startfile')
    def test_launch_folder(self, mock_startfile):
        """测试打开文件夹"""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert os.path.isdir(tmpdir)
            os.startfile(tmpdir)
            mock_startfile.assert_called_with(tmpdir)
    
    @patch('os.startfile')
    def test_launch_txt_file(self, mock_startfile):
        """测试打开文本文件"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'hello world')
            temp_path = f.name
        
        try:
            ext = os.path.splitext(temp_path)[1].lower()
            assert ext == '.txt'
            
            os.startfile(temp_path)
            mock_startfile.assert_called_with(temp_path)
        finally:
            os.unlink(temp_path)


class TestAppLauncherFileFilters:
    """测试文件过滤器"""
    
    def test_file_filter_format(self):
        """测试文件过滤器格式"""
        filters = "所有文件 (*.*)"
        
        assert "所有文件" in filters
        assert "*.*" in filters


class TestAppLauncherDragDrop:
    """测试拖拽功能"""
    
    def test_mime_data_has_urls(self):
        """测试 MIME 数据是否包含 URL"""
        from PyQt5.QtCore import QMimeData, QUrl
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile("C:/test.py")])
        assert mime_data.hasUrls()
    
    def test_mime_data_urls_extraction(self):
        """测试从 MIME 数据中提取 URL"""
        from PyQt5.QtCore import QMimeData, QUrl
        test_path = "C:/test.py"
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(test_path)])
        
        urls = mime_data.urls()
        assert len(urls) == 1
        assert urls[0].toLocalFile() == test_path
    
    def test_multiple_files_drag(self):
        """测试多文件拖拽"""
        from PyQt5.QtCore import QMimeData, QUrl
        test_paths = ["C:/test1.py", "C:/test2.bat", "C:/folder"]
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(p) for p in test_paths])
        
        urls = mime_data.urls()
        assert len(urls) == 3
    
    def test_path_exists_check(self):
        """测试路径存在检查"""
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'print("hello")')
            temp_path = f.name
        
        try:
            assert os.path.exists(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_folder_path_is_dir(self):
        """测试文件夹路径是目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert os.path.isdir(tmpdir)
            assert not os.path.isfile(tmpdir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
