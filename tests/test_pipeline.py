"""
test_pipeline.py —— 集成链路测试（组长维护）

验收标准：
  1. 四个模块都能被调度、返回统一格式
  2. 单模块抛出异常时，其他三个模块结果不受影响（容错隔离）
  3. 假数据模式可用（联调 UI 用）
  4. 统一缩放生效：大图长边被缩到 <= target_long_side
"""

import pathlib
import sys

import cv2

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import SAMPLES  # noqa: E402

import pipeline  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402
from schema import RESULT_KEYS  # noqa: E402


def run():
    img_path = SAMPLES / "normal.jpg"
    assert img_path.exists(), "samples/ 缺测试图片"

    # ---- 1. 正常链路：参考图应该四维全通过 ----
    result = pipeline.analyze_image(str(img_path), DEFAULT_CONFIG)
    assert set(result["modules"]) == {"blur", "exposure", "color", "subject"}
    for name, r in result["modules"].items():
        assert set(r.keys()) == RESULT_KEYS, f"{name} 返回键不合约"
    assert result["overall"]["num_modules"] == 4
    assert result["overall"]["num_passed"] == 4, "参考图应该四维全部通过"
    assert result["overall"]["suggestion"] == "建议保留"
    print(f"  链路 OK，通过 {result['overall']['num_passed']}/4 -> {result['overall']['suggestion']}")

    # ---- 2. 容错：让 color 模块故意崩掉 ----
    original = pipeline.MODULES["color"]

    def boom(image, config):
        raise RuntimeError("故意抛出的测试异常")

    pipeline.MODULES["color"] = boom
    try:
        broken = pipeline.analyze_image(str(img_path), DEFAULT_CONFIG)
    finally:
        pipeline.MODULES["color"] = original

    assert broken["modules"]["color"]["passed"] is False
    assert broken["modules"]["color"]["label"] == "分析失败"
    assert broken["modules"]["blur"]["passed"] is True, "其他模块不应受影响"
    print("  容错 OK：单模块异常不会拖垮整体")

    # ---- 3. 假数据模式 ----
    fake = pipeline.analyze_image(str(img_path), DEFAULT_CONFIG, fake=True)
    assert fake["modules"]["blur"]["score"] == 183.2
    assert fake["overall"]["pass_ratio"] == 1.0
    print("  假数据模式 OK")

    # ---- 4. 统一缩放：造一张 3000x2000 的大图 ----
    big = cv2.resize(cv2.imread(str(img_path)), (3000, 2000))
    res = pipeline.analyze_image(big, DEFAULT_CONFIG, fake=True)
    pw, ph = res["meta"]["proc_size"]
    assert max(pw, ph) == DEFAULT_CONFIG["target_long_side"], f"长边应缩放到 1024，实际 {pw}x{ph}"
    assert res["meta"]["resized"] is True
    print(f"  缩放 OK：3000x2000 -> {pw}x{ph}")

    print("✅ pipeline 集成测试通过")


if __name__ == "__main__":
    run()
