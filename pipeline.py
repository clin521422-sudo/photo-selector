"""
pipeline.py —— 调度层（唯一知道所有模块存在的地方）

职责：
  1. 图像加载 + 统一缩放（保证四个模块吃同一张图、分数可比）
  2. 依次调用四个分析模块，每个用 try/except 隔离（单模块失败不拖垮整体）
  3. 汇总通过率，给出综合建议

这个文件由组长维护，组员不需要改它。
"""

from __future__ import annotations

from config import DEFAULT_CONFIG, OVERALL_SUGGEST
from schema import make_result
from utils import load_and_resize

# 真实模块
from modules import blur, color, exposure, subject

# 假数据模块（用于"先把界面跑通"阶段，或某个模块崩了时临时替换）
import pipeline_fakes

MODULES = {
    "blur": blur.analyze,
    "exposure": exposure.analyze,
    "color": color.analyze,
    "subject": subject.analyze,
}

FAKE_MODULES = {
    "blur": pipeline_fakes.fake_blur,
    "exposure": pipeline_fakes.fake_exposure,
    "color": pipeline_fakes.fake_color,
    "subject": pipeline_fakes.fake_subject,
}

# 中文名，UI 直接用
MODULE_TITLES = {
    "blur": "清晰度",
    "exposure": "曝光",
    "color": "色彩",
    "subject": "主体",
}


def aggregate(results: dict) -> dict:
    """把四个模块的 passed 汇总成综合建议。"""
    total = len(results)
    passed_flags = [r["passed"] for r in results.values()]
    num_passed = sum(passed_flags)
    ratio = num_passed / total if total else 0.0

    if ratio >= OVERALL_SUGGEST["keep"]:
        suggestion = "建议保留"
    elif ratio >= OVERALL_SUGGEST["review"]:
        suggestion = "建议复核"
    else:
        suggestion = "建议淘汰"

    return {
        "pass_ratio": ratio,
        "num_passed": num_passed,
        "num_modules": total,
        "suggestion": suggestion,
        "failed_modules": [name for name, r in results.items() if not r["passed"]],
    }


def analyze_image(src, config: dict | None = None, fake: bool = False) -> dict:
    """
    分析一张图片。

    参数:
        src    : 图片路径 / bytes / 已解码的 BGR ndarray
        config : 阈值覆盖（会和 DEFAULT_CONFIG 合并）
        fake   : True 时用假数据模块（用于联调 UI）

    返回:
        {
          "modules": {name: 统一结果字典},
          "overall": {...综合建议...},
          "image"  : 统一缩放后的 BGR 图（UI 画框用，和模块坐标一致）,
          "meta"   : {原始尺寸, 处理尺寸, 是否缩放, 耗时}
        }
    """
    import time

    cfg = {**DEFAULT_CONFIG, **(config or {})}
    t0 = time.perf_counter()

    image, origin_size, proc_size, resized = load_and_resize(
        src, int(cfg["target_long_side"])
    )

    registry = FAKE_MODULES if fake else MODULES
    results: dict = {}
    for name, fn in registry.items():
        try:
            results[name] = fn(image, cfg)
        except Exception as e:  # 关键：一个模块崩了，不能拖垮整个系统
            results[name] = make_result(
                name,
                0.0,
                "分析失败",
                False,
                {"error": f"{type(e).__name__}: {e}", "fail_reason": ["模块内部异常"]},
            )

    return {
        "modules": results,
        "overall": aggregate(results),
        "image": image,
        "meta": {
            "origin_size": origin_size,
            "proc_size": proc_size,
            "resized": resized,
            "elapsed_ms": (time.perf_counter() - t0) * 1000,
        },
    }
