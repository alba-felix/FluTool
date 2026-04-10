"""文本处理工具 - 性能优化版本"""

import re
from typing import List, Dict, Callable, Tuple
from functools import lru_cache


class RegexCache:
    """正则表达式缓存"""
    _cache: Dict[str, re.Pattern] = {}
    
    @classmethod
    def get(cls, pattern: str) -> re.Pattern:
        """获取或编译正则表达式"""
        if pattern not in cls._cache:
            cls._cache[pattern] = re.compile(pattern)
        return cls._cache[pattern]


class TextProcessor:
    """文本处理器 - 性能优化版本"""

    _number_pattern = RegexCache.get(r'[-+]?\d+\.?\d*[eE][-+]?\d+')
    _normal_number_pattern = RegexCache.get(r'\b\d+\.?\d+\b')
    _thousandth_pattern = RegexCache.get(r'\b[\d,\.]+\b')
    _hump_pattern = RegexCache.get(r'(?<!^)(?=[A-Z])')

    @staticmethod
    def trim_blank(text: str) -> str:
        """去除空格"""
        return text.replace(" ", "")

    @staticmethod
    def trim_blank_row(lines: List[str]) -> List[str]:
        """去除空白行"""
        return [line for line in lines if line.strip()]

    @staticmethod
    def clear_tab(text: str) -> str:
        """去除Tab"""
        return text.replace("\t", "")

    @classmethod
    def scientific_to_normal(cls, text: str) -> str:
        """科学计数法转普通数字"""
        def convert_match(match):
            try:
                from decimal import Decimal
                num = Decimal(match.group(0).replace('e', 'E'))
                return str(num)
            except:
                return match.group(0)
        
        return cls._number_pattern.sub(convert_match, text)

    @classmethod
    def normal_to_scientific(cls, text: str) -> str:
        """普通数字转科学计数法"""
        def convert_match(match):
            try:
                from decimal import Decimal
                num = Decimal(match.group(0))
                int_part = str(num).split('.')[0] if '.' in str(num) else str(num)
                precision = max(len(int_part) - 1, 1)
                return f"{num:.{precision}E}"
            except:
                return match.group(0)
        
        return cls._normal_number_pattern.sub(convert_match, text)

    @classmethod
    def to_thousandth(cls, text: str) -> str:
        """数字转千分位"""
        def convert_match(match):
            try:
                num_str = match.group(0)
                num = float(num_str)
                if '.' in num_str:
                    decimal_places = len(num_str.split('.')[1])
                    return f"{num:,.{decimal_places}f}"
                return f"{num:,.0f}"
            except:
                return match.group(0)
        
        return cls._normal_number_pattern.sub(convert_match, text)

    @classmethod
    def to_normal_num(cls, text: str) -> str:
        """千分位转普通数字"""
        def convert_match(match):
            try:
                num_str = match.group(0)
                if re.match(r'^[0-9,\.]+$', num_str):
                    return num_str.replace(",", "")
                return num_str
            except:
                return match.group(0)
        
        return cls._thousandth_pattern.sub(convert_match, text)

    @staticmethod
    def underline_to_hump(text: str) -> str:
        """下划线转驼峰"""
        parts = text.split('_')
        if len(parts) == 1:
            return text
        result = parts[0].lower()
        for part in parts[1:]:
            if part:
                result += part[0].upper() + part[1:].lower()
        return result

    @staticmethod
    def hump_to_underline(text: str) -> str:
        """驼峰转下划线"""
        return TextProcessor._hump_pattern.sub('_', text).lower()

    @staticmethod
    def upper_to_lower(text: str) -> str:
        """大写转小写"""
        return text.lower()

    @staticmethod
    def lower_to_upper(text: str) -> str:
        """小写转大写"""
        return text.upper()

    @staticmethod
    def comma_to_enter(text: str) -> str:
        """逗号转换行"""
        return text.replace(",", "\n")

    @staticmethod
    def comma_single_quotes_to_enter(text: str) -> str:
        """逗号单引号转换行"""
        return text.replace("','", "\n").replace("'", "")

    @staticmethod
    def comma_double_quotes_to_enter(text: str) -> str:
        """逗号双引号转换行"""
        return text.replace("\",\"", "\n").replace("\"", "")

    @staticmethod
    def tab_to_enter(text: str) -> str:
        """Tab转换行"""
        return text.replace("\t", "\n")

    @staticmethod
    def deduplication_by_line(lines: List[str]) -> List[str]:
        """行去重"""
        seen = set()
        result = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                result.append(line)
        return result

    @staticmethod
    def deduplication_by_line_cnt(lines: List[str]) -> List[str]:
        """行去重并统计次数"""
        from collections import Counter
        counts = Counter(lines)
        return [f'"{line}" 出现了 {cnt} 次' for line, cnt in counts.items()]

    @staticmethod
    def reverse_by_row(lines: List[str]) -> List[str]:
        """行反转"""
        return lines[::-1]

    @staticmethod
    def sort_a_to_z(lines: List[str]) -> List[str]:
        """行排序(A-Z)"""
        return sorted(lines)

    @staticmethod
    def sort_z_to_a(lines: List[str]) -> List[str]:
        """行排序(Z-A)"""
        return sorted(lines, reverse=True)

    @staticmethod
    def sort_by_pinyin(lines: List[str]) -> List[str]:
        """按拼音排序"""
        try:
            from pypinyin import lazy_pinyin
            return sorted(lines, key=lambda x: lazy_pinyin(x))
        except ImportError:
            return sorted(lines)

    @staticmethod
    def escape_text(text: str) -> str:
        """转义"""
        return text.encode('unicode_escape').decode('utf-8')

    @staticmethod
    def unescape_text(text: str) -> str:
        """反转义"""
        try:
            return text.encode('utf-8').decode('unicode_escape')
        except:
            return text

    @classmethod
    def process(cls, content: str, options: dict) -> str:
        """根据选项处理文本 - 优化版本"""
        lines = content.split('\n')
        
        processors: List[Tuple[str, Callable]] = [
            ('trim_blank', lambda l: [cls.trim_blank(line) for line in l]),
            ('trim_blank_row', cls.trim_blank_row),
            ('clear_tab', lambda l: [cls.clear_tab(line) for line in l]),
            ('scientific_to_normal', lambda l: [cls.scientific_to_normal(line) for line in l]),
            ('normal_to_scientific', lambda l: [cls.normal_to_scientific(line) for line in l]),
            ('to_thousandth', lambda l: [cls.to_thousandth(line) for line in l]),
            ('to_normal_num', lambda l: [cls.to_normal_num(line) for line in l]),
            ('underline_to_hump', lambda l: [cls.underline_to_hump(line) for line in l]),
            ('hump_to_underline', lambda l: [cls.hump_to_underline(line) for line in l]),
            ('upper_to_lower', lambda l: [cls.upper_to_lower(line) for line in l]),
            ('lower_to_upper', lambda l: [cls.lower_to_upper(line) for line in l]),
            ('comma_to_enter', lambda l: [cls.comma_to_enter(line) for line in l]),
            ('comma_single_quotes_to_enter', lambda l: [cls.comma_single_quotes_to_enter(line) for line in l]),
            ('comma_double_quotes_to_enter', lambda l: [cls.comma_double_quotes_to_enter(line) for line in l]),
            ('tab_to_enter', lambda l: [cls.tab_to_enter(line) for line in l]),
            ('deduplication_by_line', cls.deduplication_by_line),
            ('deduplication_by_line_cnt', cls.deduplication_by_line_cnt),
            ('reverse_by_row', cls.reverse_by_row),
            ('sort_a_to_z', cls.sort_a_to_z),
            ('sort_z_to_a', cls.sort_z_to_a),
            ('sort_by_pinyin', cls.sort_by_pinyin),
        ]
        
        for key, processor in processors:
            if options.get(key):
                lines = processor(lines)
        
        result = '\n'.join(lines)
        
        if options.get('clear_enter'):
            result = result.replace('\n', '')
        elif options.get('enter_to_comma'):
            result = result.replace('\n', ',')
        elif options.get('enter_to_comma_single_quotes'):
            result = "'" + result.replace('\n', "','") + "'"
        elif options.get('enter_to_comma_double_quotes'):
            result = '"' + result.replace('\n', '","') + '"'
        
        if options.get('escape'):
            result = cls.escape_text(result)
        
        if options.get('unescape'):
            result = cls.unescape_text(result)
        
        return result
