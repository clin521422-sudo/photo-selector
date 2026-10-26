"""
test_blur.py —— 模糊模块测试

验收标准（交模块时必须能跑通并打印 ✅）：
  1. 返回字典键齐全、类型正确
  2. 清晰图分数 > 模糊图分数
  3. 清晰图通过、模糊图不通过
"""

import pathlib
import sys

import cv2

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import SAMPLES  # noqa: E402

from config import DEFAULT_CONFIG  # noqa: E402
from modules.blur import analyze  # noqa: E402


def check_format(r):
    assert set(r.keys()) == {"module", "score", "label", "passed", "details"}, f"键不对: {r.keys()}"
    assert isinstance(r["score"], float), "score 必须是 float"
    assert isinstance(r["passed"], bool), "passed 必须是 bool"
    assert isinstance(r["details"], dict), "details 必须是 dict"
    assert "laplacian_var" in r["details"], "details 缺 laplacian_var"


def run():
    clear = cv2.imread(str(SAMPLES / "normal.jpg"))
    blurred = cv2.imread(str(SAMPLES / "blurred.jpg"))
    assert clear is not None and blurred is not None, "samples/ 里缺测试图片（先跑 tools/make_samples.py）"

    r1 = analyze(clear, DEFAULT_CONFIG)
    r2 = analyze(blurred, DEFAULT_CONFIG)

    check_format(r1)
    check_format(r2)

    assert r1["score"] > r2["score"], f"清晰图分数应高于模糊图: {r1['score']:.1f} vs {r2['score']:.1f}"
    assert r1["passed"] is True, f"清晰图应通过（方差 {r1['score']:.1f}，阈值 {r1['details']['threshold']}）"
    assert r2["passed"] is False, "模糊图应不通过"

    print(f"  清晰图 laplacian_var = {r1['details']['laplacian_var']:.1f} -> {r1['label']}")
    print(f"  模糊图 laplacian_var = {r2['details']['laplacian_var']:.1f} -> {r2['label']}")
    print("✅ blur 模块测试通过")


if __name__ == "__main__":
    run()
