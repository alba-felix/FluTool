"""图片转换核心逻辑 - 与 UI 解耦，可独立单测"""

import os
from typing import List, Optional, Tuple

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 支持的格式：显示名 -> PIL 格式
SUPPORTED_FORMATS = [
    ("PNG", "PNG"),
    ("JPG", "JPEG"),
    ("WebP", "WEBP"),
    ("BMP", "BMP"),
    ("ICO", "ICO"),
    ("GIF", "GIF"),
    ("TIFF", "TIFF"),
]

# 预设输出尺寸
PRESET_SIZES: List[Tuple[int, int]] = [
    (16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
    (72, 72), (80, 80), (96, 96), (128, 128), (256, 256),
]

# ICO 单帧最大边长（格式规范上限）
ICO_MAX_SIDE = 256

# 可处理的图片扩展名（文件选择与拖拽共用）
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".ico", ".gif", ".tiff"}


def parse_custom_size(text: str) -> Optional[Tuple[int, int]]:
    """解析自定义尺寸：'512x512'、'512'（正方形）；非法输入返回 None"""
    text = text.strip().lower().replace("×", "x").replace("*", "x")
    if not text:
        return None
    parts = text.split("x")
    if len(parts) == 1:
        parts = [parts[0], parts[0]]
    if len(parts) != 2:
        return None
    try:
        w, h = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    if w <= 0 or h <= 0 or w > 9999 or h > 9999:
        return None
    return w, h


def convert_image(src_path: str, output_dir: str, fmt: str,
                  sizes: List[Tuple[int, int]],
                  include_original: bool = False) -> List[str]:
    """转换单张图片到指定格式，返回生成的文件列表。

    - include_original：额外输出原始尺寸文件 {base}.{ext}
    - sizes 中的每个尺寸输出一个文件 {base}_{w}x{h}.{ext}（LANCZOS 精确缩放）
    - ICO：全部尺寸嵌入单个 {base}.ico（Pillow 按源图比例生成各帧）
    - 两者皆空时抛出 ValueError
    """
    if not HAS_PIL:
        raise RuntimeError("Pillow未安装，无法进行图片转换")
    image = Image.open(src_path)
    if image.mode not in ("RGBA", "P", "LA"):
        image = image.convert("RGBA")

    base_name = os.path.splitext(os.path.basename(src_path))[0]
    os.makedirs(output_dir, exist_ok=True)
    ext = _ext_of(fmt)

    try:
        if fmt == "ICO":
            out_path = os.path.join(output_dir, f"{base_name}.{ext}")
            frame_sizes = _ico_frame_sizes(image, sizes, include_original)
            image.save(out_path, format="ICO", sizes=frame_sizes)
            return [out_path]

        results = []
        if include_original:
            out_path = os.path.join(output_dir, f"{base_name}.{ext}")
            _save(image, out_path, fmt)
            results.append(out_path)
        for w, h in sizes:
            out_path = os.path.join(output_dir, f"{base_name}_{w}x{h}.{ext}")
            resized = image.resize((w, h), Image.LANCZOS)
            _save(resized, out_path, fmt)
            results.append(out_path)

        if not results:
            raise ValueError("未选择任何输出尺寸")
        return results
    finally:
        image.close()


def _ext_of(fmt: str) -> str:
    """PIL 格式对应的扩展名"""
    return "jpg" if fmt == "JPEG" else fmt.lower()


def _save(image: "Image.Image", out_path: str, fmt: str) -> None:
    """按格式保存：JPEG 去 Alpha 转 RGB，其余直存"""
    if fmt == "JPEG":
        image.convert("RGB").save(out_path, format="JPEG", quality=90)
        return
    image.save(out_path, format=fmt)


def _ico_frame_sizes(image: "Image.Image", sizes: List[Tuple[int, int]],
                     include_original: bool) -> List[Tuple[int, int]]:
    """计算 ICO 嵌入帧：过滤超源图/超 256 的请求，保证至少一帧"""
    max_w = min(image.width, ICO_MAX_SIDE)
    max_h = min(image.height, ICO_MAX_SIDE)
    candidates = list(sizes)
    if include_original:
        candidates.append(tuple(image.size))
    frame_sizes = []
    for s in candidates:
        if s[0] <= max_w and s[1] <= max_h and s not in frame_sizes:
            frame_sizes.append(s)
    return frame_sizes or [(max_w, max_h)]
