"""
utils.py —— 公共工具：图像加载与统一缩放

缩放策略（重要）：
  * 只缩不放：长边 <= target 的图原样返回，放大不会增加真实细节，只会引入插值伪影
  * 保留宽高比：绝不强制拉伸成固定尺寸（会引入各向异性插值伪影，污染拉普拉斯/直方图）
  * 缩小时统一用 INTER_AREA（抗混叠，比 INTER_LINEAR 更稳定）
"""

from __future__ import annotations

import pathlib

import cv2
import numpy as np

TARGET_LONG_SIDE = 1024


def imread_unicode(path) -> np.ndarray:
    """读取图片，兼容 Windows 中文路径（cv2.imread 对中文路径会失败）。"""
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"图像加载失败（路径或格式有问题）: {path}")
    return img


def imread_bytes(data: bytes) -> np.ndarray:
    """从 bytes 读取图片（Streamlit file_uploader 用）。"""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("图像解码失败（不是有效的图片文件）")
    return img


def load_image(src) -> np.ndarray:
    """统一入口：支持 路径 / bytes / 已解码的 ndarray，返回 BGR ndarray。"""
    if isinstance(src, np.ndarray):
        return src
    if isinstance(src, (bytes, bytearray)):
        return imread_bytes(bytes(src))
    if isinstance(src, pathlib.Path):
        return imread_unicode(src)
    if isinstance(src, str):
        return imread_unicode(src)
    raise TypeError(f"不支持的图像输入类型: {type(src)}")


def resize_long_side(
    image: np.ndarray, target_long_side: int = TARGET_LONG_SIDE
) -> tuple[np.ndarray, bool]:
    """长边等比缩放到 target_long_side（只缩不放）。返回 (图像, 是否缩放)。"""
    h, w = image.shape[:2]
    long_side = max(h, w)
    if long_side <= target_long_side:
        return image, False

    scale = target_long_side / long_side
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, True


def load_and_resize(src, target_long_side: int = TARGET_LONG_SIDE):
    """加载 + 统一缩放。返回 (BGR 图像, 原始尺寸(w,h), 缩放后尺寸(w,h), 是否缩放)。"""
    img = load_image(src)
    oh, ow = img.shape[:2]
    out, resized = resize_long_side(img, target_long_side)
    th, tw = out.shape[:2]
    return out, (ow, oh), (tw, th), resized
