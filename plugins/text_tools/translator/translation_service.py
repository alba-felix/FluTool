"""
翻译服务模块

提供本地词典翻译和有道在线API翻译两种模式。
优先使用本地词典(O(1)查找)，未匹配时使用有道API。
支持多文件词典加载。
"""

import hashlib
import time
import uuid
import urllib.request
import urllib.parse
import json
import os
from typing import Optional

from .dictionary_data import EN_TO_ZH
from .dictionary_manager import get_dictionary_manager


class YoudaoTranslator:
    """有道翻译API封装"""

    API_URL = "https://openapi.youdao.com/api"

    def __init__(self, app_key: str, app_secret: str):
        self._app_key = app_key
        self._app_secret = app_secret

    def _generate_sign(self, query: str, salt: str, curtime: str) -> str:
        """生成API签名"""
        # input计算: q前10个字符 + q长度 + q后10个字符(当q长度>20) 或 q字符串(当q长度<=20)
        q_len = len(query)
        if q_len <= 20:
            input_str = query
        else:
            input_str = query[:10] + str(q_len) + query[-10:]

        # sign=sha256(应用ID+input+salt+curtime+应用密钥)
        sign_str = self._app_key + input_str + salt + curtime + self._app_secret
        return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

    def translate(self, text: str, from_lang: str = "auto", to_lang: str = "zh-CHS") -> Optional[str]:
        """
        调用有道API翻译

        Args:
            text: 待翻译文本
            from_lang: 源语言 (auto为自动检测)
            to_lang: 目标语言 (zh-CHS为中文)

        Returns:
            翻译结果或None(失败时)
        """
        if not text or not text.strip():
            return None

        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        sign = self._generate_sign(text, salt, curtime)

        # 语言代码映射
        lang_map = {
            "中文": "zh-CHS",
            "英语": "en",
            "自动检测": "auto"
        }

        from_code = lang_map.get(from_lang, from_lang)
        to_code = lang_map.get(to_lang, to_lang)

        data = {
            "q": text,
            "from": from_code,
            "to": to_code,
            "appKey": self._app_key,
            "salt": salt,
            "sign": sign,
            "signType": "v3",
            "curtime": curtime
        }

        try:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            encoded_data = urllib.parse.urlencode(data).encode('utf-8')
            req = urllib.request.Request(
                self.API_URL,
                data=encoded_data,
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))

                error_code = result.get('errorCode')
                if error_code != '0':
                    print(f"[YoudaoAPI] Error code: {error_code}")
                    return None

                # 获取翻译结果
                translation = result.get('translation', [])
                if translation:
                    return translation[0]

                return None

        except Exception as e:
            print(f"[YoudaoAPI] Request failed: {e}")
            return None


class TranslationService:
    """翻译服务类"""

    def __init__(self):
        # 使用词典管理器支持多文件
        self._dict_manager = get_dictionary_manager()
        # 加载默认词典
        self._dict_manager.load_from_dict(EN_TO_ZH, "dictionary_data.py")
        # 自动加载dicts目录下的所有词典文件
        dicts_dir = os.path.join(os.path.dirname(__file__), "dicts")
        if os.path.exists(dicts_dir):
            self._dict_manager.load_from_directory(dicts_dir, "*.py")

        # 从配置读取有道 API 凭据
        self._youdao = None
        try:
            from core.api_key_manager import get_api_key_manager
            mgr = get_api_key_manager()
            app_key = mgr.get("youdao_app_key")
            app_secret = mgr.get("youdao_app_secret")
            if app_key and app_secret:
                self._youdao = YoudaoTranslator(app_key, app_secret)
        except Exception:
            pass

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "中文"
    ) -> tuple[str, str]:
        """
        翻译文本

        Args:
            text: 要翻译的文本
            source_lang: 源语言
            target_lang: 目标语言

        Returns:
            (翻译结果, 翻译来源说明: local/api/none)
        """
        if not text or not text.strip():
            return "", "none"

        text = text.strip()
        text_lower = text.lower()

        # 模式1: 本地词典全词匹配 (O(1))
        # 支持空格，直接匹配整个输入（去除首尾空格后）
        if target_lang == "中文":
            local_result = self._dict_manager.get(text_lower)
            if local_result:
                return local_result, "local"

        # 模式2: 有道API翻译
        if self._youdao:
            api_result = self._youdao.translate(text, source_lang, target_lang)
            if api_result:
                return api_result, "api"
            else:
                # API调用失败，返回错误提示
                return f"[翻译失败] {text}\n\n(有道API调用失败，请检查网络或密钥配置)", "api"

        # 回退: 服务未初始化
        return f"[翻译服务] {text}\n\n(在线翻译服务未初始化)", "api"

    def is_in_dictionary(self, word: str) -> bool:
        """检查单词是否在本地词典中"""
        if not word:
            return False
        return word.strip().lower() in self._dict_manager

    def get_dictionary_size(self) -> int:
        """获取词典大小"""
        return len(self._dict_manager)

    def load_dictionary_file(self, file_path: str) -> bool:
        """加载额外的词典文件"""
        return self._dict_manager.load_from_file(file_path)

    def load_dictionary_directory(self, directory: str, pattern: str = "*.py") -> int:
        """从目录加载词典文件"""
        return self._dict_manager.load_from_directory(directory, pattern)

    def set_api_secret(self, secret: str, app_key: str = None) -> None:
        """设置API凭据并初始化有道翻译"""
        try:
            from core.api_key_manager import get_api_key_manager
            mgr = get_api_key_manager()
            if app_key:
                mgr.set("youdao_app_key", app_key)
            else:
                app_key = mgr.get("youdao_app_key")
            mgr.set("youdao_app_secret", secret)
            if app_key and secret:
                self._youdao = YoudaoTranslator(app_key, secret)
        except Exception:
            pass


# 全局翻译服务实例
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """获取翻译服务单例"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def reset_translation_service() -> TranslationService:
    """重置并重新创建翻译服务实例(用于更新配置后)"""
    global _translation_service
    _translation_service = TranslationService()
    return _translation_service
