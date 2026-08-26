"""
图片服务模块
负责图片的保存、删除和路径管理
"""
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union
from dataclasses import dataclass


@dataclass
class ImageInfo:
    """图片信息"""
    filename: str
    path: Path
    size: int
    exists: bool


class ImageService:
    """
    图片服务类
    
    负责管理笔记相关的图片资源
    
    属性:
        _image_dir: 图片存储目录
    """
    
    def __init__(self, image_dir: Path):
        self._image_dir = Path(image_dir)
        self._ensure_dir()
    
    @classmethod
    def create_default(cls) -> 'ImageService':
        """使用默认路径创建实例"""
        from ..core.path_util import PathUtil
        return cls(PathUtil.get_image_path())
    
    def _ensure_dir(self) -> None:
        self._image_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def image_dir(self) -> Path:
        return self._image_dir
    
    def generate_filename(
        self,
        category_name: str = '',
        index: int = 0,
        extension: str = 'png'
    ) -> str:
        """
        生成图片文件名
        
        格式: {分类前缀}_{时间戳}_{序号}.{扩展名}
        例如: 工作_20260322_143025_00.png
        
        参数:
            category_name: 分类名称（用于文件名前缀）
            index: 序号
            extension: 文件扩展名
            
        返回:
            生成的文件名
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        prefix = category_name if category_name else 'untitled'
        prefix = ''.join(c for c in prefix if c.isalnum() or c in '_-')[:20]
        
        return f"{prefix}_{timestamp}_{max(index, 0):02d}.{extension}"
    
    def save(
        self,
        image_data: Union[bytes, 'QPixmap'],
        filename: Optional[str] = None,
        category_name: str = '',
        index: int = 0
    ) -> Optional[str]:
        """
        保存图片到本地（先轻微压缩：JPEG 85 重编码，谁小留谁）

        参数:
            image_data: 图片数据（bytes 或 QPixmap）
            filename: 可选的文件名（不含扩展名）
            category_name: 分类名称
            index: 序号

        返回:
            保存的文件名（扩展名随最终格式 .jpg/.png），失败返回 None
        """
        if image_data is None:
            return None
        try:
            original = self._to_bytes(image_data)
            if original is None:
                return None
            data, ext = self._compress_light(original)
            if filename is None or not filename.strip():
                filename = self.generate_filename(category_name, max(index, 0),
                                                  extension=ext)
            elif '.' not in Path(filename).name:
                filename = f"{filename}.{ext}"
            elif not filename.rsplit('.', 1)[1].lower() in ('png', 'jpg', 'jpeg', 'bmp', 'gif', 'webp'):
                filename = f"{filename}.{ext}"

            with open(self._image_dir / filename, 'wb') as f:
                f.write(data)
            return filename
        except Exception:
            return None

    @staticmethod
    def _to_bytes(image_data: Union[bytes, 'QPixmap']) -> Optional[bytes]:
        """统一转 bytes（QPixmap 先编码为 PNG 字节再走压缩管线）"""
        if hasattr(image_data, 'save'):
            from PyQt5.QtCore import QBuffer
            buf = QBuffer()
            if not buf.open(QBuffer.ReadWrite) or not image_data.save(buf, 'PNG'):
                return None
            return bytes(buf.data())
        if isinstance(image_data, (bytes, bytearray)):
            return bytes(image_data)
        return None

    @staticmethod
    def _compress_light(original: bytes):
        """轻微压缩：JPEG 85 重编码 + EXIF 方向烘焙，谁小留谁。

        与 Android 端 ImageService.compressLight 语义一致：
        - 已压缩图片（微信图/截图）重编码后更大时保留原文件，数学上不可能膨胀
        - GIF（重编码丢动画）与 Pillow 解码失败 → 原样返回 (original, 'png')
        - 超过 4096 边长的超大图先降采样（防内存峰值，常规照片不受影响）
        """
        if original[:4] == b'GIF8':
            return original, 'png'
        try:
            from PIL import Image, ImageOps
            img = Image.open(io.BytesIO(original))
            img.load()
        except Exception:
            return original, 'png'
        try:
            img = ImageOps.exif_transpose(img)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            max_edge = max(img.size)
            if max_edge > 4096:
                ratio = 4096 / max_edge
                img = img.resize((max(1, round(img.width * ratio)),
                                  max(1, round(img.height * ratio))),
                                 Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=85, optimize=True)
            compressed = buf.getvalue()
            if len(compressed) < len(original):
                return compressed, 'jpg'
        except Exception:
            pass
        return original, 'png'
    
    def get_path(self, filename: str) -> Optional[Path]:
        """
        获取图片的完整路径
        
        参数:
            filename: 图片文件名
            
        返回:
            图片路径，文件不存在返回 None
        """
        if not filename:
            return None
        image_path = self._image_dir / filename
        return image_path if image_path.exists() else None
    
    def get_info(self, filename: str) -> Optional[ImageInfo]:
        """
        获取图片信息
        
        参数:
            filename: 图片文件名
            
        返回:
            ImageInfo 对象，文件不存在返回 None
        """
        path = self.get_path(filename)
        if path is None:
            return None
        
        return ImageInfo(
            filename=filename,
            path=path,
            size=path.stat().st_size,
            exists=True
        )
    
    def delete(self, filename: str) -> bool:
        """
        删除图片文件
        
        参数:
            filename: 图片文件名
            
        返回:
            删除成功返回 True
        """
        if not filename:
            return False
        path = self._image_dir / filename
        if path.exists():
            try:
                os.remove(path)
                return True
            except Exception:
                return False
        return True
    
    def exists(self, filename: str) -> bool:
        """检查图片是否存在"""
        if not filename:
            return False
        return (self._image_dir / filename).exists()
    
    def list_all(self) -> list[str]:
        """列出所有图片文件名"""
        if not self._image_dir.exists():
            return []
        return [f.name for f in self._image_dir.iterdir() if f.is_file()]
    
    def get_total_size(self) -> int:
        """获取所有图片的总大小（字节）"""
        total = 0
        if not self._image_dir.exists():
            return 0
        for f in self._image_dir.iterdir():
            if f.is_file():
                total += f.stat().st_size
        return total
    
    def cleanup_unused(self, used_filenames: set[str]) -> int:
        """
        清理未使用的图片
        
        参数:
            used_filenames: 正在使用的图片文件名集合
            
        返回:
            删除的文件数量
        """
        deleted = 0
        if not self._image_dir.exists():
            return 0
        for f in self._image_dir.iterdir():
            if f.is_file() and f.name not in used_filenames:
                try:
                    os.remove(f)
                    deleted += 1
                except Exception:
                    pass
        return deleted