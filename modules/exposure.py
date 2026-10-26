"""
曝光分析模块 —— 直方图统计 + 3x3 中心加权分区

指标：
  * 过曝比例：灰度 >= 245 的像素占比（高光溢出、细节丢失）
  * 欠曝比例：灰度 <= 10 的像素占比（暗部死黑、细节丢失）
  * 平均亮度：整体偏暗/偏亮
  * 动态范围：P99 - P1，太小白画面发灰、层次不足

为什么做分区加权：
  全局统计有个漏洞——"天空大面积过曝、人脸其实正常"的照片会被整体判为过曝。
  用 3x3 分块、中心 4 块权重加倍后，边缘过曝对结论的影响被削弱，
  中心（通常主体所在）的曝光质量更被重视。
"""

from __future__ import annotations

import cv2
import numpy as np

from schema import make_result

# 3x3 权重：中心行/列权重加倍
_ZONE_WEIGHTS = np.array([[1, 1, 1], [1, 2, 1], [1, 1, 1]], dtype=np.float32)


def _weighted_ratios(gray: np.ndarray, over_thr: int, under_thr: int):
    """按 3x3 分区、中心加权，统计过曝/欠曝比例。"""
    h, w = gray.shape[:2]
    over = 0.0
    under = 0.0
    wsum = float(_ZONE_WEIGHTS.sum())

    for i in range(3):
        for j in range(3):
            block = gray[i * h // 3 : (i + 1) * h // 3, j * w // 3 : (j + 1) * w // 3]
            if block.size == 0:
                continue
            wt = float(_ZONE_WEIGHTS[i, j])
            over += wt * float((block >= over_thr).mean())
            under += wt * float((block <= under_thr).mean())

    return over / wsum, under / wsum


def analyze(image: np.ndarray, config: dict) -> dict:
    over_thr = int(config.get("exposure_over_thr", 245))
    under_thr = int(config.get("exposure_under_thr", 10))
    over_max = float(config.get("exposure_over_max", 0.05))
    under_max = float(config.get("exposure_under_max", 0.05))
    mean_min = float(config.get("exposure_mean_min", 60))
    mean_max = float(config.get("exposure_mean_max", 190))
    dr_min = float(config.get("exposure_dynamic_range_min", 80))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    over_ratio, under_ratio = _weighted_ratios(gray, over_thr, under_thr)
    # 同时给出全局比例，方便对比展示
    over_ratio_global = float((gray >= over_thr).mean())
    under_ratio_global = float((gray <= under_thr).mean())

    mean_b = float(gray.mean())
    p1, p99 = np.percentile(gray, (1, 99))
    dynamic_range = float(p99 - p1)

    over_ok = over_ratio <= over_max
    under_ok = under_ratio <= under_max
    mean_ok = mean_min <= mean_b <= mean_max
    dr_ok = dynamic_range >= dr_min

    passed = over_ok and under_ok and mean_ok

    fail_reason: list[str] = []
    if not over_ok:
        fail_reason.append(f"高光溢出比例 {over_ratio:.1%} 过高")
    if not under_ok:
        fail_reason.append(f"暗部死黑比例 {under_ratio:.1%} 过高")
    if not mean_ok:
        fail_reason.append(
            "整体偏暗" if mean_b < mean_min else "整体偏亮"
        )
    if not dr_ok:
        fail_reason.append(f"动态范围 {dynamic_range:.0f} 偏小（画面发灰）")

    if over_ok and under_ok and mean_ok:
        label = "曝光正常"
    elif not over_ok and under_ok:
        label = "过曝"
    elif not under_ok and over_ok:
        label = "欠曝"
    else:
        label = "曝光异常"

    # score 定义为"曝光合格度" 0~100：溢出像素越少分越高
    score = float(np.clip(100.0 * (1.0 - over_ratio - under_ratio), 0.0, 100.0))

    return make_result(
        "exposure",
        score=score,
        label=label,
        passed=passed,
        details={
            "over_ratio": over_ratio,
            "under_ratio": under_ratio,
            "over_ratio_global": over_ratio_global,
            "under_ratio_global": under_ratio_global,
            "mean_brightness": mean_b,
            "dynamic_range": dynamic_range,
            "fail_reason": fail_reason,
        },
    )
