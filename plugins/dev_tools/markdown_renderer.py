"""Markdown 渲染器"""
import re
from typing import Dict


class MarkdownRenderer:
    """简单的 Markdown 渲染器，将 Markdown 转换为 HTML"""

    def __init__(self):
        self._in_code_block = False
        self._code_block_lines = []
        self._code_block_language = ""

    def render(self, text: str) -> str:
        """将 Markdown 文本渲染为 HTML"""
        if not text:
            return ""

        lines = text.split("\n")
        html_parts = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # 处理代码块
            if line.strip().startswith("```"):
                if self._in_code_block:
                    # 结束代码块
                    lang = self._code_block_language or "code"
                    code_content = "\n".join(self._code_block_lines)
                    code_content = self._escape_html(code_content)
                    html_parts.append(
                        f'<pre style="background-color: #1a1a2e; color: #e0e0e0; padding: 12px; border-radius: 6px; margin: 8px 0; overflow-x: auto;">'
                        f'<code class="{lang}" style="font-family: Consolas, Monaco, monospace; font-size: 13px; line-height: 1.5;">{code_content}</code>'
                        f'</pre>'
                    )
                    self._in_code_block = False
                    self._code_block_lines = []
                    self._code_block_language = ""
                else:
                    # 开始代码块
                    self._in_code_block = True
                    lang = line.strip()[3:].strip()
                    self._code_block_language = lang
                i += 1
                continue

            # 如果在代码块中，收集代码行
            if self._in_code_block:
                self._code_block_lines.append(line)
                i += 1
                continue

            # 处理标题
            if line.startswith("### "):
                html_parts.append(f'<h3 style="margin: 12px 0 6px 0; font-size: 15px;">{line[4:]}</h3>')
            elif line.startswith("## "):
                html_parts.append(f'<h2 style="margin: 14px 0 8px 0; font-size: 17px;">{line[3:]}</h2>')
            elif line.startswith("# "):
                html_parts.append(f'<h1 style="margin: 16px 0 10px 0; font-size: 20px;">{line[2:]}</h1>')
            # 处理粗体、斜体
            elif line.strip():
                rendered = self._render_inline(line)
                # 检测列表
                if line.startswith("- ") or line.startswith("* "):
                    html_parts.append(f'<div style="margin-left: 20px; padding: 2px 0;">• {rendered}</div>')
                elif line.startswith("> "):
                    html_parts.append(f'<div style="border-left: 3px solid #888; padding: 4px 12px; margin: 4px 0; color: #888;">{rendered}</div>')
                else:
                    html_parts.append(f'<div style="padding: 2px 0; line-height: 1.6;">{rendered}</div>')
            else:
                html_parts.append('<div style="height: 4px;"></div>')

            i += 1

        # 如果还有未闭合的代码块
        if self._in_code_block and self._code_block_lines:
            lang = self._code_block_language or "code"
            code_content = "\n".join(self._code_block_lines)
            code_content = self._escape_html(code_content)
            html_parts.append(
                f'<pre style="background-color: #1a1a2e; color: #e0e0e0; padding: 12px; border-radius: 6px; margin: 8px 0; overflow-x: auto;">'
                f'<code class="{lang}" style="font-family: Consolas, Monaco, monospace; font-size: 13px; line-height: 1.5;">{code_content}</code>'
                f'</pre>'
            )

        return "\n".join(html_parts)

    def _render_inline(self, text: str) -> str:
        """渲染行内 Markdown 元素"""
        # 粗体
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        # 斜体
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        # 行内代码
        text = re.sub(r'`(.+?)`', r'<code style="background-color: #1a1a2e; color: #e0e0e0; padding: 2px 6px; border-radius: 3px; font-family: Consolas, Monaco, monospace; font-size: 12px;">\1</code>', text)
        # 链接
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color: #009faa;">\1</a>', text)
        # 换行转 <br>
        text = text.replace("\\n", "<br>")
        return text

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        return text
