import string


class CharCryptoTool:
    """字符处理与加解密工具类，支持数字、英文、特殊字符"""
    
    def __init__(self):
        # 定义支持的字符集：数字 + 大小写字母 + 常见特殊字符
        self.chars = (string.digits + 
                      string.ascii_letters + 
                      string.punctuation + 
                      ' ')  # 包含空格
        self.char_set = set(self.chars)
        self.char_len = len(self.chars)

    def is_valid(self, text: str) -> bool:
        """检查文本是否只包含支持的字符"""
        return all(c in self.char_set for c in text)

    def shift_encrypt(self, text: str, key: int) -> str:
        """
        移位加密算法
        :param text: 待加密文本
        :param key: 加密密钥（整数）
        :return: 加密后的文本
        """
        if not self.is_valid(text):
            raise ValueError("文本包含不支持的字符，请检查输入")
        
        encrypted = []
        key = key % self.char_len  # 确保密钥在有效范围内
        for c in text:
            index = self.chars.index(c)
            new_index = (index + key) % self.char_len
            encrypted.append(self.chars[new_index])
        return ''.join(encrypted)

    def shift_decrypt(self, text: str, key: int) -> str:
        """
        移位解密算法
        :param text: 待解密文本
        :param key: 解密密钥（与加密密钥相同）
        :return: 解密后的文本
        """
        if not self.is_valid(text):
            raise ValueError("文本包含不支持的字符，请检查输入")
        
        decrypted = []
        key = key % self.char_len  # 确保密钥在有效范围内
        for c in text:
            index = self.chars.index(c)
            new_index = (index - key) % self.char_len
            decrypted.append(self.chars[new_index])
        return ''.join(decrypted)

    def reverse_text(self, text: str) -> str:
        """反转文本"""
        return text[::-1]

    def count_chars(self, text: str) -> dict:
        """统计文本中各类字符的数量"""
        count = {
            'digits': 0,
            'letters': 0,
            'uppercase': 0,
            'lowercase': 0,
            'special': 0,
            'space': 0,
            'total': len(text)
        }
        
        for c in text:
            if c.isdigit():
                count['digits'] += 1
            elif c.isalpha():
                count['letters'] += 1
                if c.isupper():
                    count['uppercase'] += 1
                else:
                    count['lowercase'] += 1
            elif c.isspace():
                count['space'] += 1
            else:
                count['special'] += 1
        return count

    def replace_char(self, text: str, old_char: str, new_char: str) -> str:
        """替换文本中的字符"""
        if len(old_char) != 1 or len(new_char) != 1:
            raise ValueError("替换字符必须是单个字符")
        if old_char not in self.char_set or new_char not in self.char_set:
            raise ValueError("替换字符包含不支持的字符")
        return text.replace(old_char, new_char)
