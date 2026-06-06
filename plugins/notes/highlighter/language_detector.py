"""
语言检测器 - 自动检测代码片段的编程语言
"""

from typing import Optional


def detect_language(code_snippet: str) -> str:
    """
    检测代码片段的编程语言
    
    参数:
        code_snippet: 代码片段
        
    返回:
        检测到的语言标识符
    """
    if not code_snippet or not code_snippet.strip():
        return 'other'
    
    code = code_snippet.lower()
    lines = code_snippet.split('\n')
    first_line = lines[0].strip() if lines else ""
    
    # 1. 首先检查文件头（shebang）
    if first_line.startswith('#!/'):
        if 'python' in first_line:
            return 'python'
        elif 'bash' in first_line or 'sh' in first_line:
            return 'bash'
        elif 'node' in first_line or 'js' in first_line:
            return 'javascript'
        elif 'php' in first_line:
            return 'php'
        elif 'ruby' in first_line:
            return 'ruby'
        elif 'perl' in first_line:
            return 'perl'
    
    # 2. 检查语言特定的标记
    # Java检测 - 更严格的条件
    java_keywords = ['public class ', 'private ', 'protected ', 'static ', 'void ', 
                     'System.out.println', 'import java.', 'extends ', 'implements ', 'package ']
    java_count = sum(1 for keyword in java_keywords if keyword in code)
    if java_count >= 2:
        return 'java'
    
    # Python检测 - 更严格的条件
    python_keywords = ['def ', 'class ', 'import ', 'from ', 'if __name__', 
                       'print(', 'lambda ', 'with ', 'try:', 'except ', 'finally:']
    python_count = sum(1 for keyword in python_keywords if keyword in code)
    if python_count >= 2:
        return 'python'
    
    # JavaScript检测 - 更严格的条件
    js_keywords = ['function ', '=>', 'const ', 'let ', 'var ', 'console.log', 
                   'document.', 'window.', 'async ', 'await ']
    js_count = sum(1 for keyword in js_keywords if keyword in code)
    if js_count >= 2:
        return 'javascript'
    
    # C/C++检测
    cpp_keywords = ['#include', 'int main()', 'using namespace', 'cout <<', 
                    'cin >>', '#define', '#ifdef', '#endif']
    cpp_count = sum(1 for keyword in cpp_keywords if keyword in code)
    if cpp_count >= 2:
        return 'c_or_cpp'
    
    # HTML检测
    if any(tag in code for tag in ['<html', '<head', '<body', '<div', '<span', '<p', '<a href']) and code.count('<') >= 2:
        return 'html'
    
    # CSS检测
    if any(prop in code for prop in ['color:', 'font-size:', 'margin:', 'padding:', 'background:', 'border:']) and '{' in code and '}' in code:
        return 'css'
    
    # SQL检测
    sql_keywords = ['select ', 'from ', 'where ', 'insert into', 'update ', 
                    'delete from', 'create table', 'alter table']
    sql_count = sum(1 for keyword in sql_keywords if keyword in code)
    if sql_count >= 2:
        return 'sql'
    
    # JSON检测
    stripped = code_snippet.strip()
    if (stripped.startswith('{') and stripped.endswith('}')) or (stripped.startswith('[') and stripped.endswith(']')):
        if stripped.count('"') >= 4 and ':' in stripped:
            return 'json'
    
    # XML检测
    if stripped.startswith('<?xml') or ('<' in stripped and '>' in stripped):
        if stripped.count('<') >= 2 and stripped.count('>') >= 2:
            return 'xml'
    
    # PHP检测
    if '<?php' in code or ('<?' in code and '?>' in code):
        php_keywords = ['$', 'echo ', 'function ', 'class ', 'if (', 'foreach (', 'while (']
        php_count = sum(1 for keyword in php_keywords if keyword in code)
        if php_count >= 2:
            return 'php'
    
    # Bash/Shell检测
    bash_keywords = ['echo ', 'if [', 'then', 'fi', 'for ', 'do', 'done', '#!/bin/', '#!/usr/bin/env']
    bash_count = sum(1 for keyword in bash_keywords if keyword in code)
    if bash_count >= 2:
        return 'bash'
    
    # Markdown检测
    md_patterns = ['# ', '## ', '### ', '* ', '- ', '1. ', '**', '__', '`', '```']
    md_count = sum(1 for pattern in md_patterns if pattern in code)
    if md_count >= 2:
        return 'markdown'
    
    # 3. 单关键词匹配（后备）
    if 'def ' in code and ':' in code:
        return 'python'
    elif 'class ' in code and ':' in code:
        return 'python'
    elif 'public class ' in code:
        return 'java'
    elif 'System.out.println' in code:
        return 'java'
    elif 'function ' in code and ('{' in code or '=>' in code):
        return 'javascript'
    elif '#include' in code:
        return 'c_or_cpp'
    
    return 'other'


class LanguageDetector:
    """语言检测器类"""
    
    # 语言别名映射
    LANGUAGE_ALIASES = {
        'py': 'python',
        'js': 'javascript',
        'ts': 'typescript',
        'jsx': 'javascript',
        'tsx': 'typescript',
        'c++': 'cpp',
        'c#': 'csharp',
        'sh': 'bash',
        'shell': 'bash',
        'zsh': 'bash',
    }
    
    @classmethod
    def detect(cls, code: str) -> str:
        """检测代码语言"""
        return detect_language(code)
    
    @classmethod
    def normalize_language(cls, language: str) -> str:
        """规范化语言名称"""
        if not language:
            return 'other'
        
        language_lower = language.lower().strip()
        return cls.LANGUAGE_ALIASES.get(language_lower, language_lower)
    
    @classmethod
    def get_language_name(cls, language: str) -> str:
        """获取语言的显示名称"""
        names = {
            'python': 'Python',
            'java': 'Java',
            'javascript': 'JavaScript',
            'typescript': 'TypeScript',
            'c_or_cpp': 'C/C++',
            'html': 'HTML',
            'css': 'CSS',
            'sql': 'SQL',
            'json': 'JSON',
            'xml': 'XML',
            'php': 'PHP',
            'bash': 'Bash',
            'markdown': 'Markdown',
            'other': '其他',
        }
        return names.get(language.lower(), language)