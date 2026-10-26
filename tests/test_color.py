"""
test_color.py —— 色彩模块测试

验收标准：
  1. 返回字典键齐全、类型正确
  2. 去色（灰度）后平均饱和度必须显著低于彩色原图
  3. 去色图应被判为不通过
  4. 同一张图跑两次，K-Means 主色必须一致（可复现）
"""

import pathlib
import sys

import cv2

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import SAMPLES  # noqa: E402

from config import DEFAULT_CONFIG  # noqa: E402
from modules.color import analyze  # noqa: E402


def check_format(r):
    assert set(r.keys()) == {"module", "score", "label", "passed", "details"}
    assert isinstance(r["score"], float)
    assert isinstance(r["passed"], bool)
    for key in ("sat_mean", "contrast", "richness", "main_hues"):
        assert key in r["details"], f"details 缺 {key}"
    assert isinstance(r["details"]["main_hues"], list)


def run():
    colorful = cv2.imread(str(SAMPLES / "normal.jpg"))
    gray_img = cv2.imread(str(SAMPLES / "gray.jpg"))
    assert colorful is not None and gray_img is not None, "samples/ 缺测试图片"

    r1 = analyze(colorful, DEFAULT_CONFIG)
    r2 = analyze(gray_img, DEFAULT_CONFIG)

    check_format(r1)
    check_format(r2)

    assert r1["passed"] is True, f"正常彩色图应通过，实际 {r1['label']}"
    assert r2["details"]["sat_mean"] < r1["details"]["sat_mean"], "去色图饱和度应更低"
    assert r2["passed"] is False, "去色图应不通过（饱和度不足）"

    # 可复现性：同一张图跑两次，主色必须一致（K-Means 固定了种子）
    r3 = analyze(colorful, DEFAULT_CONFIG)
    assert r3["details"]["main_hues"] == r1["details"]["main_hues"], "K-Means 结果不可复现！"

    print(f"  彩色图 sat_mean={r1['details']['sat_mean']:.1f} richness={r1['details']['richness']:.2f} -> {r1['label']}")
    print(f"  去色图 sat_mean={r2['details']['sat_mean']:.1f} richness={r2['details']['richness']:.2f} -> {r2['label']}")
    print("✅ color 模块测试通过")


if __name__ == "__main__":
    run()
