"""
文件夹树插件单元测试
测试核心逻辑：树形生成、深度控制、规则过滤、取消操作
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from typing import List, Tuple
import pytest
from pytest import MonkeyPatch
from unittest.mock import Mock, patch, MagicMock, PropertyMock


sys.path.insert(0, str(Path(__file__).parent.parent))


FOLDER_TREE_PATH = "plugins.folder_tree"


@pytest.fixture
def qapp():
    """提供 QApplication 实例"""
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def temp_dir_with_files():
    """创建临时目录结构用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        # level 1
        (base / "file1.txt").write_text("test", encoding="utf-8")
        (base / "file2.py").write_text("print('test')", encoding="utf-8")
        dir_a = base / "dir_a"
        dir_a.mkdir()
        dir_b = base / "dir_b"
        dir_b.mkdir()
        # level 2
        (dir_a / "file_a1.txt").write_text("test", encoding="utf-8")
        (dir_a / "file_a2.log").write_text("log", encoding="utf-8")
        sub_a1 = dir_a / "sub_a1"
        sub_a1.mkdir()
        (dir_b / "file_b1.txt").write_text("test", encoding="utf-8")
        # level 3
        (sub_a1 / "deep_file.txt").write_text("deep", encoding="utf-8")
        sub_a1_deep = sub_a1 / "deep_dir"
        sub_a1_deep.mkdir()
        # level 4
        (sub_a1_deep / "very_deep.txt").write_text("very deep", encoding="utf-8")

        yield base


@pytest.fixture
def temp_dir_with_skip():
    """创建包含需要跳过的目录结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        (base / "normal_file.txt").write_text("test", encoding="utf-8")
        (base / ".venv").mkdir()
        ((base / ".venv") / "lib.py").write_text("lib", encoding="utf-8")
        (base / ".git").mkdir()
        ((base / ".git") / "config").write_text("config", encoding="utf-8")
        (base / ".idea").mkdir()
        ((base / ".idea") / "workspace.xml").write_text("xml", encoding="utf-8")

        yield base


class TestFolderTreeWorkerBuildTree:
    """测试 FolderTreeWorker 树形生成逻辑"""

    def test_build_tree_full_depth(self, temp_dir_with_files: Path, qapp):
        """测试完全递归扫描（depth=-1）"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=-1
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert folder_count >= 3
        assert file_count >= 5
        assert "dir_a/" in tree
        assert "dir_b/" in tree
        assert "sub_a1/" in tree
        assert "deep_dir/" in tree
        assert "file1.txt" in tree
        assert "deep_file.txt" in tree
        assert "very_deep.txt" in tree

    def test_build_tree_depth_1(self, temp_dir_with_files: Path, qapp):
        """测试深度为1的扫描"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=1
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert folder_count >= 2
        assert file_count >= 2
        assert "dir_a/" in tree
        assert "dir_b/" in tree
        assert "file1.txt" in tree
        assert "file2.py" in tree
        assert "sub_a1/" not in tree
        assert "deep_file.txt" not in tree

    def test_build_tree_depth_2(self, temp_dir_with_files: Path, qapp):
        """测试深度为2的扫描"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=2
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert "sub_a1/" in tree
        assert "deep_dir/" not in tree
        assert "very_deep.txt" not in tree

    def test_build_tree_depth_3(self, temp_dir_with_files: Path, qapp):
        """测试深度为3的扫描"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=3
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert "deep_dir/" in tree
        assert "very_deep.txt" not in tree

    def test_build_tree_zero_items(self, qapp):
        """测试空目录"""
        from plugins.folder_tree import FolderTreeWorker

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            worker = FolderTreeWorker(
                root_path=base, mode="tree",
                rule_index=0, custom_rules={}, depth=-1
            )
            tree, folder_count, file_count = worker._build_tree(base, '', 0, 0, 0)

        assert folder_count == 0
        assert file_count == 0
        assert tree == ""

    def test_build_tree_cancelled(self, temp_dir_with_files: Path, qapp):
        """测试取消操作"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=-1
        )
        worker.cancel()
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert tree == ""
        assert folder_count == 0
        assert file_count == 0


class TestFolderTreeWorkerBuildFolders:
    """测试 FolderTreeWorker 仅文件夹模式"""

    def test_build_folders_full_depth(self, temp_dir_with_files: Path, qapp):
        """测试仅文件夹完全递归"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="folders",
            rule_index=0,
            custom_rules={},
            depth=-1
        )
        tree, folder_count, _ = worker._build_folders_only(
            temp_dir_with_files, '', 0, 0
        )

        assert folder_count >= 3
        assert "dir_a/" in tree
        assert "sub_a1/" in tree
        assert "deep_dir/" in tree
        assert "file1.txt" not in tree
        assert "file2.py" not in tree


class TestFolderTreeWorkerSkipRules:
    """测试跳过规则"""

    def test_skip_rule_1(self, temp_dir_with_skip: Path, qapp):
        """测试规则1（跳过 .venv, .git, .idea）"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_skip,
            mode="tree",
            rule_index=1,
            custom_rules={},
            depth=-1
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_skip, '', 0, 0, 0
        )

        assert ".venv" not in tree
        assert ".git" not in tree
        assert ".idea" not in tree
        assert "normal_file.txt" in tree
        assert folder_count == 0
        assert file_count == 1

    def test_skip_rule_custom(self, temp_dir_with_files: Path, qapp):
        """测试自定义规则"""
        from plugins.folder_tree import FolderTreeWorker

        custom_rules = {"test_rule": ["dir_a", "dir_b"]}
        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=2,
            custom_rules=custom_rules,
            depth=-1
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert "dir_a" not in tree
        assert "dir_b" not in tree
        assert folder_count == 0
        assert file_count == 2

    def test_skip_rule_custom_out_of_range(self, temp_dir_with_files: Path, qapp):
        """测试自定义规则索引超出范围时的降级行为"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=10,
            custom_rules={},
            depth=-1
        )
        tree, folder_count, file_count = worker._build_tree(
            temp_dir_with_files, '', 0, 0, 0
        )

        assert folder_count >= 3
        assert file_count >= 5


class TestFolderTreeWorkerCountItems:
    """测试项目计数"""

    def test_count_items_full_depth(self, temp_dir_with_files: Path, qapp):
        """测试完整深度计数"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=-1
        )
        count = worker._count_items(temp_dir_with_files, 0)

        assert count == 11

    def test_count_items_depth_1(self, temp_dir_with_files: Path, qapp):
        """测试深度1计数"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=1
        )
        count = worker._count_items(temp_dir_with_files, 0)

        assert count == 8

    def test_count_items_cancelled(self, temp_dir_with_files: Path, qapp):
        """测试取消计数"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=temp_dir_with_files,
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=-1
        )
        worker.cancel()
        count = worker._count_items(temp_dir_with_files, 0)

        assert count == 0


class TestFolderTreeWidgetLogic:
    """测试 FolderTreeWidget 业务逻辑"""

    def test_validate_rule_items_valid(self, qapp):
        """测试有效规则项验证"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        valid, items = widget.validate_rule_items(".git,.venv,node_modules")

        assert valid is True
        assert items == [".git", ".venv", "node_modules"]

    def test_validate_rule_items_empty(self, qapp):
        """测试空字符串验证"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        valid, items = widget.validate_rule_items("")

        assert valid is False
        assert items == []

    def test_validate_rule_items_whitespace_only(self, qapp):
        """测试纯空白字符串"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        valid, items = widget.validate_rule_items("   ")

        assert valid is False

    def test_validate_rule_items_chinese(self, qapp):
        """测试中文规则项"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        valid, items = widget.validate_rule_items("临时文件,下载内容")

        assert valid is True
        assert items == ["临时文件", "下载内容"]

    def test_validate_rule_items_invalid_chars(self, qapp):
        """测试无效字符"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        valid, invalid_items = widget.validate_rule_items("test@dir,good_dir")

        assert valid is False
        assert "test@dir" in invalid_items
        assert "good_dir" not in invalid_items

    def test_scan_depth_persistence(self, qapp, tmp_path: Path):
        """测试扫描深度持久化"""
        import json
        from core import get_app_data_path
        from unittest.mock import patch

        from plugins.folder_tree import FolderTreeWidget

        config_dir = tmp_path / "FluTool"
        config_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = config_dir / "folder_tree_config.json"
        cfg_path.write_text(json.dumps({"scan_depth": 2}, ensure_ascii=False), encoding="utf-8")

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        with patch('plugins.folder_tree.get_app_data_path', return_value=config_dir):
            depth = widget._load_scan_depth()
            assert depth == 2

    def test_scan_depth_persistence_default(self, qapp, tmp_path: Path):
        """测试扫描深度持久化默认值"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        depth = widget._load_scan_depth()
        assert depth == -1

    def test_scan_depth_persistence_save(self, qapp, tmp_path: Path):
        """测试保存扫描深度"""
        from plugins.folder_tree import FolderTreeWidget
        from unittest.mock import patch

        config_dir = tmp_path / "FluTool"
        config_dir.mkdir(parents=True, exist_ok=True)

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        with patch('plugins.folder_tree.get_app_data_path', return_value=config_dir):
            widget._save_scan_depth(3)
            cfg_path = config_dir / "folder_tree_config.json"
            assert cfg_path.exists()
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            assert cfg["scan_depth"] == 3

    def test_on_depth_changed(self, qapp):
        """测试深度变更回调（下拉框索引 1 -> 深度 2）"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        widget._scan_depth = -1

        with patch('plugins.folder_tree.InfoBar.info') as mock_info:
            widget._on_depth_changed(1)

            assert widget._scan_depth == 2

    def test_on_depth_changed_all(self, qapp):
        """测试深度变更为全部（下拉框索引 3 -> 深度 -1）"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        widget._scan_depth = 2

        with patch('plugins.folder_tree.InfoBar.info') as mock_info:
            widget._on_depth_changed(3)

            assert widget._scan_depth == -1

    def test_on_depth_changed_level_1(self, qapp):
        """测试深度变更为 1 级（下拉框索引 0 -> 深度 1）"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        widget._scan_depth = 3

        with patch('plugins.folder_tree.InfoBar.info') as mock_info:
            widget._on_depth_changed(0)

            assert widget._scan_depth == 1

    def test_on_depth_changed_level_3(self, qapp):
        """测试深度变更为 3 级（下拉框索引 2 -> 深度 3）"""
        from plugins.folder_tree import FolderTreeWidget

        widget = FolderTreeWidget.__new__(FolderTreeWidget)
        widget._scan_depth = 1

        with patch('plugins.folder_tree.InfoBar.info') as mock_info:
            widget._on_depth_changed(2)

            assert widget._scan_depth == 3


class TestFolderTreeWorkerCancel:
    """测试取消操作"""

    def test_cancel_flag(self, qapp):
        """测试取消标记设置"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=Path("."),
            mode="tree",
            rule_index=0,
            custom_rules={},
            depth=-1
        )
        assert worker._cancelled is False
        worker.cancel()
        assert worker._cancelled is True


class TestFolderTreeWorkerLargeDirectory:
    """测试大目录性能"""

    def test_large_directory_tree(self, qapp):
        """测试包含大量文件的目录"""
        from plugins.folder_tree import FolderTreeWorker

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            for i in range(50):
                sub_dir = base / f"sub_{i}"
                sub_dir.mkdir()
                for j in range(20):
                    (sub_dir / f"file_{j}.txt").write_text("x", encoding="utf-8")

            worker = FolderTreeWorker(
                root_path=base, mode="tree",
                rule_index=0, custom_rules={}, depth=-1
            )
            tree, folder_count, file_count = worker._build_tree(base, '', 0, 0, 0)

            assert folder_count == 50
            assert file_count == 1000

    def test_large_directory_depth_limited(self, qapp):
        """测试大目录深度限制（depth=1，仅显示根目录项）"""
        from plugins.folder_tree import FolderTreeWorker

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            for i in range(30):
                sub_dir = base / f"sub_{i}"
                sub_dir.mkdir()
                for j in range(30):
                    (sub_dir / f"file_{j}.txt").write_text("x", encoding="utf-8")

            worker = FolderTreeWorker(
                root_path=base, mode="tree",
                rule_index=0, custom_rules={}, depth=1
            )
            tree, folder_count, file_count = worker._build_tree(base, '', 0, 0, 0)

            assert folder_count == 30
            assert file_count == 0


class TestFolderTreeWorkerGetSkipNames:
    """测试 _get_skip_names 方法"""

    def test_no_rule(self, qapp):
        """测试无规则"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=Path("."), mode="tree",
            rule_index=0, custom_rules={}, depth=-1
        )
        names = worker._get_skip_names()
        assert names == set()

    def test_rule_1(self, qapp):
        """测试规则1"""
        from plugins.folder_tree import FolderTreeWorker

        worker = FolderTreeWorker(
            root_path=Path("."), mode="tree",
            rule_index=1, custom_rules={}, depth=-1
        )
        names = worker._get_skip_names()
        assert names == {".venv", ".git", ".idea"}

    def test_custom_rule(self, qapp):
        """测试自定义规则"""
        from plugins.folder_tree import FolderTreeWorker

        custom_rules = {"my_rule": ["node_modules", "__pycache__"]}
        worker = FolderTreeWorker(
            root_path=Path("."), mode="tree",
            rule_index=2, custom_rules=custom_rules, depth=-1
        )
        names = worker._get_skip_names()
        assert names == {"node_modules", "__pycache__"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
