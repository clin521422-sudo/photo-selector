"""
tools/calibrate.py —— 阈值校准小工具

把一批照片跑一遍，打印每个模块的原始指标，方便你据此定 config.py 里的阈值
（不要直接套网上的经验值，用自己样本的分布来定）。

用法：
    python tools/calibrate.py            # 跑 samples/ 目录
    python tools/calibrate.py data/imgs  # 跑指定目录
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from config import DEFAULT_CONFIG  # noqa: E402
from modules import blur, color, exposure, subject  # noqa: E402
from utils import load_and_resize  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "samples"
    files = sorted(p for p in target.rglob("*") if p.suffix.lower() in EXTS)
    if not files:
        print(f"{target} 里没有图片")
        return 1

    print(f"{'文件':<18}{'blur_var':>10}{'over':>8}{'under':>8}{'mean':>7}"
          f"{'sat':>7}{'contrast':>9}{'rich':>7}{'主体数':>7}{'主体占比':>9}")
    print("-" * 92)

    rows = []
    for f in files:
        try:
            img, _, _, _ = load_and_resize(str(f), DEFAULT_CONFIG["target_long_side"])
        except Exception as e:
            print(f"{f.name:<18} 加载失败: {e}")
            continue

        b = blur.analyze(img, DEFAULT_CONFIG)
        e_ = exposure.analyze(img, DEFAULT_CONFIG)
        c = color.analyze(img, DEFAULT_CONFIG)
        s = subject.analyze(img, DEFAULT_CONFIG)

        d_b, d_e, d_c, d_s = b["details"], e_["details"], c["details"], s["details"]
        rows.append((f.name, d_b["laplacian_var"], d_e["over_ratio"], d_e["under_ratio"],
                     d_e["mean_brightness"], d_c["sat_mean"], d_c["contrast"],
                     d_c["richness"], d_s["num_objects"], d_s["max_area_ratio"]))

        print(f"{f.name:<18}{d_b['laplacian_var']:>10.1f}{d_e['over_ratio']:>8.1%}"
              f"{d_e['under_ratio']:>8.1%}{d_e['mean_brightness']:>7.0f}"
              f"{d_c['sat_mean']:>7.1f}{d_c['contrast']:>9.1f}{d_c['richness']:>7.2f}"
              f"{d_s['num_objects']:>7d}{d_s['max_area_ratio']:>9.1%}")

    if rows:
        import statistics

        def rng(i):
            vals = [r[i] for r in rows]
            return f"{min(vals):.2f} ~ {max(vals):.2f}（中位 {statistics.median(vals):.2f}）"

        print("\n各指标分布（用于定阈值）：")
        print("  模糊度 laplacian_var :", rng(1))
        print("  过曝比例             :", rng(2))
        print("  欠曝比例             :", rng(3))
        print("  平均亮度             :", rng(4))
        print("  饱和度               :", rng(5))
        print("  对比度               :", rng(6))
        print("  色彩丰富度           :", rng(7))
        print("  主体占比             :", rng(9))
    return 0


if __name__ == "__main__":
    sys.exit(main())
