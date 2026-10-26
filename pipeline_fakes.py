"""
pipeline_fakes.py —— 假数据模块（桩函数）

用途：在真实模块还没写好的时候，先把 UI 和集成链路跑通。
返回格式必须和真模块完全一致，这样替换时 UI 一行都不用改。

切换方式：pipeline.analyze_image(src, fake=True)
"""

from __future__ import annotations

from schema import make_result


def fake_blur(image, config):
    return make_result(
        "blur", 183.2, "清晰", True,
        {"laplacian_var": 183.2, "threshold": 100.0, "fail_reason": []},
    )


def fake_exposure(image, config):
    return make_result(
        "exposure", 97.0, "曝光正常", True,
        {"over_ratio": 0.02, "under_ratio": 0.01, "mean_brightness": 128.0,
         "dynamic_range": 120.0, "fail_reason": []},
    )


def fake_color(image, config):
    return make_result(
        "color", 88.0, "色彩正常", True,
        {"sat_mean": 95.0, "contrast": 42.0, "richness": 0.60,
         "main_hues": [10, 30, 90, 150], "fail_reason": []},
    )


def fake_subject(image, config):
    return make_result(
        "subject", 35.0, "主体突出", True,
        {"max_area_ratio": 0.35, "center_offset": 0.08, "num_objects": 1,
         "boxes": [], "fail_reason": []},
    )
