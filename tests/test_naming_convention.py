"""
Python 代码规范测试
检测类、函数、变量的命名是否符合 Python 规范
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


QT_EVENT_METHODS = {
    'enterEvent', 'leaveEvent', 'paintEvent', 'resizeEvent',
    'mousePressEvent', 'mouseReleaseEvent', 'mouseMoveEvent',
    'keyPressEvent', 'keyReleaseEvent', 'wheelEvent', 'focusInEvent', 'focusOutEvent',
    'showEvent', 'hideEvent', 'closeEvent', 'moveEvent',
    'dragEnterEvent', 'dragMoveEvent', 'dragLeaveEvent', 'dropEvent',
    'contextMenuEvent', 'inputMethodEvent', 'changeEvent',
    'mouseDoubleClickEvent', 'tabletEvent', 'touchEvent',
    'nativeEvent', 'eventFilter', 'customEvent',
    'highlightBlock', 'setupUi',
    'setExpandWidth', 'setCompacted', 'isCompacted', 'getOverflowItems',
    'addSubInterface', 'removeInterface', 'switchTo'
}

PYQT_METHODS = {'setText', 'setIcon', 'setEnabled', 'setDisabled', 'setVisible',
                'setToolTip', 'setStatusTip', 'setWhatsThis', 'setObjectName',
                'setStyleSheet', 'setLayout', 'setCentralWidget', 'setMenuBar',
                'addAction', 'removeAction', 'addWidget', 'removeWidget',
                'addItem', 'removeItem', 'clear', 'setCurrentItem', 'currentItem',
                'setChecked', 'isChecked', 'setExpanded', 'isExpanded',
                'setCollapsed', 'isCollapsed', 'setCurrentIndex', 'currentIndex',
                'setCurrentRow', 'currentRow', 'setText', 'text', 'setIcon',
                'addTab', 'removeTab', 'clear', 'setTabText', 'tabText',
                'setAlignment', 'alignment', 'setSpacing', 'spacing',
                'setContentsMargins', 'contentsMargins', 'setMinimumSize', 'setMaximumSize',
                'setSizePolicy', 'setFont', 'font', 'setCursor', 'setFocus',
                'setWindowTitle', 'windowTitle', 'setWindowIcon', 'windowIcon',
                'setWindowFlags', 'windowFlags', 'setAttribute', 'testAttribute',
                'setLayoutDirection', 'layoutDirection', 'setUniformRowHeights',
                'setExpandsOnDoubleClick', 'setHeaderHidden', 'isHeaderHidden',
                'setIndentation', 'indentation', 'setRootIsDecorated', 'rootIsDecorated',
                'setAutoExpandDelay', 'setItemAnimated', 'setToolTipDuration',
                'setStatusTip', 'setWhatsThis', 'setAccessibleName', 'accessibleName',
                'setAccessibleDescription', 'accessibleDescription', 'setDefault', 'isDefault',
                'setAutoDefault', 'autoDefault', 'setFlat', 'isFlat',
                'clearItems', 'setItems'}

WINDOWS_API_STRUCTS = {
    'PROCESS_POWER_THROTTLING_STATE',
    'SYSTEM_POWER_INFORMATION',
    'BATTERY_INFORMATION',
    'PROCESS_INFORMATION',
    'THREAD_INFORMATION',
    'MEMORY_INFORMATION',
    'SYSTEM_INFORMATION'
}


class NamingConventionChecker(ast.NodeVisitor):
    """检测命名规范的 AST 访问器"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.errors: List[Dict] = []
        self.class_names: List[str] = []
        self.function_names: List[str] = []
        self.variable_names: List[str] = []
        self.constant_names: List[str] = []
        self._is_inside_enum = False

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """检测类名"""
        self.class_names.append(node.name)

        is_enum = any(
            (isinstance(base, ast.Name) and base.id == 'Enum') or
            (isinstance(base, ast.Attribute) and hasattr(base.value, 'id') and base.value.id == 'Enum')
            for base in node.bases
        )

        if is_enum:
            self._is_inside_enum = True

        if not self._is_camel_case(node.name):
            if node.name != '_' and not node.name.startswith('__'):
                if not is_enum and node.name not in WINDOWS_API_STRUCTS:
                    self.errors.append({
                        'file': self.file_path,
                        'line': node.lineno,
                        'type': 'class',
                        'name': node.name,
                        'expected': 'CamelCase',
                        'message': f"类名 '{node.name}' 应使用 CamelCase 格式"
                    })
        self.generic_visit(node)
        self._is_inside_enum = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """检测函数名"""
        if not node.name.startswith('_'):
            self.function_names.append(node.name)
            if not self._is_snake_case(node.name):
                if node.name not in QT_EVENT_METHODS and node.name not in PYQT_METHODS:
                    self.errors.append({
                        'file': self.file_path,
                        'line': node.lineno,
                        'type': 'function',
                        'name': node.name,
                        'expected': 'snake_case',
                        'message': f"函数名 '{node.name}' 应使用 snake_case 格式"
                    })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """检测异步函数名"""
        if not node.name.startswith('_'):
            self.function_names.append(node.name)
            if not self._is_snake_case(node.name):
                if node.name not in QT_EVENT_METHODS and node.name not in PYQT_METHODS:
                    self.errors.append({
                        'file': self.file_path,
                        'line': node.lineno,
                        'type': 'function',
                        'name': node.name,
                        'expected': 'snake_case',
                        'message': f"异步函数名 '{node.name}' 应使用 snake_case 格式"
                    })
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """检测变量和常量赋值"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if name.isupper() and '_' in name:
                    self.constant_names.append(name)
                    if not self._is_upper_snake_case(name):
                        self.errors.append({
                            'file': self.file_path,
                            'line': node.lineno,
                            'type': 'constant',
                            'name': name,
                            'expected': 'UPPER_SNAKE_CASE',
                            'message': f"常量 '{name}' 应使用 UPPER_SNAKE_CASE 格式"
                        })
                elif not name.startswith('_') and not name.startswith('__'):
                    self.variable_names.append(name)
                    if self._looks_like_constant(name) and not self._is_inside_enum:
                        if not self._is_upper_snake_case(name):
                            self.errors.append({
                                'file': self.file_path,
                                'line': node.lineno,
                                'type': 'variable',
                                'name': name,
                                'expected': 'UPPER_SNAKE_CASE (常量)',
                                'message': f"变量名 '{name}' 像是常量，应使用 UPPER_SNAKE_CASE 格式"
                            })
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """检测变量名（用于 for、while 等循环中的变量）"""
        if isinstance(node.ctx, ast.Store):
            name = node.id
            if not name.startswith('_') and not name.startswith('__'):
                if name.isupper() and '_' in name:
                    self.constant_names.append(name)
                else:
                    self.variable_names.append(name)
        self.generic_visit(node)

    def _is_camel_case(self, name: str) -> bool:
        """检查是否为 CamelCase"""
        if not name:
            return False
        if name.startswith('_') or name.startswith('__'):
            return True
        return name[0].isupper() and '_' not in name

    def _is_snake_case(self, name: str) -> bool:
        """检查是否为 snake_case"""
        if not name:
            return False
        if name.startswith('_') or name.startswith('__'):
            return True
        return '_' in name or name.islower()

    def _is_upper_snake_case(self, name: str) -> bool:
        """检查是否为 UPPER_SNAKE_CASE"""
        if not name:
            return False
        return name.isupper() and '_' in name

    def _looks_like_constant(self, name: str) -> bool:
        """检查变量名是否像是常量（全大写）"""
        return name.isupper()


def check_file(file_path: str) -> Tuple[List[Dict], Dict]:
    """检查单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=file_path)
        checker = NamingConventionChecker(file_path)
        checker.visit(tree)

        stats = {
            'classes': len(checker.class_names),
            'functions': len(checker.function_names),
            'variables': len(checker.variable_names),
            'constants': len(checker.constant_names)
        }

        return checker.errors, stats
    except SyntaxError as e:
        return [{
            'file': file_path,
            'line': e.lineno or 0,
            'type': 'syntax',
            'name': '',
            'expected': 'valid Python',
            'message': f"语法错误: {e.msg}"
        }], {}
    except Exception as e:
        return [{
            'file': file_path,
            'line': 0,
            'type': 'error',
            'name': '',
            'expected': '',
            'message': f"解析错误: {str(e)}"
        }], {}


def check_directory(directory: str, exclude_dirs: List[str] = None) -> Dict:
    """检查目录下的所有 Python 文件"""
    if exclude_dirs is None:
        exclude_dirs = ['.venv', 'venv', '__pycache__', '.git', 'build', 'dist', '.eggs', '*.egg-info']

    exclude_dirs = set(exclude_dirs)
    results = {
        'files_checked': 0,
        'files_with_errors': 0,
        'total_errors': 0,
        'errors': [],
        'stats': {}
    }

    abs_directory = os.path.abspath(directory)

    for root, dirs, files in os.walk(abs_directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                errors, stats = check_file(file_path)

                results['files_checked'] += 1
                results['stats'][file_path] = stats

                if errors:
                    results['files_with_errors'] += 1
                    results['total_errors'] += len(errors)
                    results['errors'].extend(errors)

    return results


def print_results(results: Dict) -> None:
    """打印测试结果"""
    print("=" * 80)
    print("Python 代码规范测试结果")
    print("=" * 80)
    print()

    print(f"检查文件数: {results['files_checked']}")
    print(f"有问题的文件: {results['files_with_errors']}")
    print(f"错误总数: {results['total_errors']}")
    print()

    if results['errors']:
        print("-" * 80)
        print("错误详情:")
        print("-" * 80)

        current_file = None
        for error in sorted(results['errors'], key=lambda x: (x['file'], x['line'])):
            if error['file'] != current_file:
                current_file = error['file']
                rel_path = os.path.relpath(error['file'])
                print(f"\n文件: {rel_path}")

            print(f"  行 {error['line']}: {error['message']}")

        print()
        print("-" * 80)
        print("统计信息:")
        print("-" * 80)

        for file_path, stats in sorted(results['stats'].items()):
            if stats:
                rel_path = os.path.relpath(file_path)
                print(f"\n{rel_path}:")
                print(f"  类: {stats.get('classes', 0)}, "
                      f"函数: {stats.get('functions', 0)}, "
                      f"变量: {stats.get('variables', 0)}, "
                      f"常量: {stats.get('constants', 0)}")
    else:
        print("✓ 所有文件都符合命名规范!")

    print()
    print("=" * 80)


def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = '.'

    if os.path.isfile(target):
        errors, stats = check_file(target)
        results = {
            'files_checked': 1,
            'files_with_errors': 1 if errors else 0,
            'total_errors': len(errors),
            'errors': errors,
            'stats': {target: stats}
        }
    else:
        results = check_directory(target)

    print_results(results)

    return 0 if not results['errors'] else 1


if __name__ == '__main__':
    exit(main())
