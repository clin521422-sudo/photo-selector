"""
test_exposure.py —— 曝光模块测试

验收标准：
  1. 返回字典键齐全、类型正确
  2. 人为提亮的图，过曝比例变大且判定不通过
  3. 人为压暗的图，欠曝比例变大且判定不通过
"""

import pathlib
import sys

import cv2

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import SAMPLES  # noqa: E402

from config import DEFAULT_CONFIG  # noqa: E402
from modules.exposure import analyze  # noqa: E402


def check_format(r):
    assert set(r.keys()) == {"module", "score", "label", "passed", "details"}
    assert isinstance(r["score"], float)
    assert isinstance(r["passed"], bool)
    for key in ("over_ratio", "under_ratio", "mean_brightness", "dynamic_range"):
        assert key in r["details"], f"details 缺 {key}"


def run():
    img = cv2.imread(str(SAMPLES / "normal.jpg"))
    assert img is not None, "samples/ 缺测试图片（先跑 tools/make_samples.py）"

    bright = cv2.convertScaleAbs(img, alpha=1.0, beta=90)   # 提亮 -> 应过曝
    dark = cv2.convertScaleAbs(img, alpha=0.25, beta=0)     # 压暗 -> 应欠曝

    r0 = analyze(img, DEFAULT_CONFIG)
    r1 = analyze(bright, DEFAULT_CONFIG)
    r2 = analyze(dark, DEFAULT_CONFIG)

    for r in (r0, r1, r2):
        check_format(r)

    assert r0["passed"] is True, f"正常曝光的参考图应通过，实际 {r0['label']}"
    assert r1["details"]["over_ratio"] > r0["details"]["over_ratio"], "提亮后过曝比例应升高"
    assert r2["details"]["under_ratio"] > r0["details"]["under_ratio"], "压暗后欠曝比例应升高"
    assert r1["passed"] is False, "明显过曝的图应不通过"
    assert r2["passed"] is False, "明显欠曝的图应不通过"

    print(f"  原图   over={r0['details']['over_ratio']:.1%} under={r0['details']['under_ratio']:.1%} -> {r0['label']}")
    print(f"  提亮   over={r1['details']['over_ratio']:.1%} under={r1['details']['under_ratio']:.1%} -> {r1['label']}")
    print(f"  压暗   over={r2['details']['over_ratio']:.1%} under={r2['details']['under_ratio']:.1%} -> {r2['label']}")
    print("✅ exposure 模块测试通过")


if __name__ == "__main__":
    run()
