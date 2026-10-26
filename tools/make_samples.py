"""
tools/make_samples.py —— 生成测试样图

从源照片生成一组"极端情况"样图，用于跑测试和演示：

    normal.jpg       清晰、曝光正常的参考图（花）—— 四维全通过的基准
    blurred.jpg      模糊图（高斯模糊 normal）
    over.jpg         过曝图（提亮 normal）
    under.jpg        欠曝图（压暗 normal）
    gray.jpg         去色图（低饱和度）
    subject_dog.jpg  有明确主体的照片（狗）—— 主体模块测试用

源图放在 photo-selector/sources/ 下：
    sources/sample_dog.jpg
    sources/sample_flower.jpg
（本项目已自动从 ../yolo/images 复制过一份）

用法：
    python tools/make_samples.py
"""

from __future__ import annotations

import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
SOURCES = ROOT / "sources"

SOURCE_DIRS = [SOURCES, ROOT.parent / "yolo" / "images"]


def find_source(name: str) -> pathlib.Path | None:
    for d in SOURCE_DIRS:
        p = d / name
        if p.exists():
            return p
    return None


def resize_long(image: np.ndarray, long_side: int = 1024) -> np.ndarray:
    h, w = image.shape[:2]
    s = long_side / max(h, w)
    if s >= 1:
        return image
    return cv2.resize(image, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)


def main():
    SAMPLES.mkdir(exist_ok=True)
    SOURCES.mkdir(exist_ok=True)

    dog_path = find_source("sample_dog.jpg")
    flower_path = find_source("sample_flower.jpg")
    if dog_path is None or flower_path is None:
        print("找不到源图。请把两张照片放进 photo-selector/sources/：")
        print("  sources/sample_dog.jpg     （有明确主体的照片）")
        print("  sources/sample_flower.jpg  （色彩丰富、纹理多的照片）")
        return 1

    dog = resize_long(cv2.imread(str(dog_path)))
    flower = resize_long(cv2.imread(str(flower_path)))

    normal = flower
    blurred = cv2.GaussianBlur(normal, (21, 21), 0)
    over = cv2.convertScaleAbs(normal, alpha=1.0, beta=95)
    under = cv2.convertScaleAbs(normal, alpha=0.22, beta=0)
    gray_img = cv2.cvtColor(cv2.cvtColor(normal, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

    out = {
        "normal.jpg": normal,
        "blurred.jpg": blurred,
        "over.jpg": over,
        "under.jpg": under,
        "gray.jpg": gray_img,
        "subject_dog.jpg": dog,
    }
    for name, img in out.items():
        ok = cv2.imwrite(str(SAMPLES / name), img)
        print(f"  {'OK ' if ok else 'FAIL'} {name}  {img.shape[1]}x{img.shape[0]}")
    print(f"\n样图已生成到: {SAMPLES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
