"""
test_subject.py —— 主体模块测试（YOLOv8n ONNX + cv2.dnn）

验收标准：
  1. 返回字典键齐全、类型正确
  2. 对有明确主体的照片（狗），能检出 >=1 个目标且判定通过
  3. 对纯色/无主体图，不误报为"主体突出"
"""

import pathlib
import sys

import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import SAMPLES  # noqa: E402

from config import DEFAULT_CONFIG  # noqa: E402
from modules.subject import analyze  # noqa: E402


def check_format(r):
    assert set(r.keys()) == {"module", "score", "label", "passed", "details"}
    assert isinstance(r["score"], float)
    assert isinstance(r["passed"], bool)
    for key in ("max_area_ratio", "center_offset", "num_objects", "boxes"):
        assert key in r["details"], f"details 缺 {key}"


def run():
    dog = cv2.imread(str(SAMPLES / "subject_dog.jpg"))
    assert dog is not None, "samples/ 缺测试图片（先跑 tools/make_samples.py）"

    r1 = analyze(dog, DEFAULT_CONFIG)
    check_format(r1)
    assert r1["details"]["num_objects"] >= 1, f"狗的照片应该检出目标，实际 {r1['details']['num_objects']} 个"
    assert r1["passed"] is True, f"主体应通过，实际 {r1['label']}"
    assert r1["details"]["max_area_ratio"] > 0.05, "主体占比应大于阈值"
    assert r1["details"]["top_class"] == "dog", f"应该识别为 dog，实际 {r1['details']['top_class']}"
    print(f"  狗照片: {r1['details']['num_objects']} 个目标, "
          f"最大主体 {r1['details']['max_area_ratio']:.1%} "
          f"({r1['details']['top_class']}) -> {r1['label']}")

    # 纯灰图：不应该检测到任何 COCO 目标
    blank = np.full((480, 640, 3), 128, dtype=np.uint8)
    r2 = analyze(blank, DEFAULT_CONFIG)
    check_format(r2)
    assert r2["details"]["num_objects"] == 0, "纯色图不应检出目标"
    assert r2["passed"] is False, "纯色图应不通过"
    print(f"  纯色图: {r2['details']['num_objects']} 个目标 -> {r2['label']}")

    print("✅ subject 模块测试通过")


if __name__ == "__main__":
    run()
