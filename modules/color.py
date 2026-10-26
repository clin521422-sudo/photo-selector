"""
色彩分析模块 —— HSV 统计 + 色相熵 + K-Means 主色

三个核心指标：
  * 平均饱和度 : HSV 的 S 通道均值（0~255），过低 -> 画面灰暗平淡
  * 对比度     : 灰度图标准差，过低 -> 画面发灰、层次不清
  * 色彩丰富度 : H 通道直方图归一化熵（0~1），过低 -> 单调，过高 -> 杂乱

主色提取：在缩小图上对 (H, S) 做 K-Means，取各簇中心色相和占比。
注意 OpenCV 的 H 范围是 0~179（不是 0~360），K-Means 固定初始化保证可复现。

设计取舍：
  色相"和谐度"暂不放进 passed 判断——互补色配色（如橙+蓝）是经典审美，
  但圆形统计会判它"色相分散"，容易误杀。这里只作为 details 参考信息。
"""

from __future__ import annotations

import cv2
import numpy as np

from schema import make_result

# 圆形色相集中度：0 = 色相分布很散，1 = 色相高度集中
def _hue_concentration(hues: list[float], weights: list[float]) -> float:
    if not hues:
        return 0.0
    angles = np.deg2rad(np.asarray(hues, dtype=np.float64) * 2.0)  # H:0~179 -> 0~360
    w = np.asarray(weights, dtype=np.float64)
    if w.sum() <= 0:
        return 0.0
    w = w / w.sum()
    vec = np.sum(w * np.exp(1j * angles))
    return float(np.abs(vec))


def _main_colors(image: np.ndarray, k: int) -> tuple[list[float], list[float]]:
    """K-Means 提取主色相。返回 (主色相列表, 各主色占比列表)。"""
    small = cv2.resize(image, (160, 160), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    # 只暴露给低饱和像素一点点权重：用 (H, S) 当特征
    feats = hsv.reshape(-1, 2).astype(np.float32)

    k = max(1, min(int(k), feats.shape[0]))
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    cv2.setRNGSeed(42)  # 固定随机种子，保证同一张图结果可复现
    _, labels, centers = cv2.kmeans(
        feats, k, None, criteria, 5, cv2.KMEANS_PP_CENTERS
    )

    labels = labels.flatten()
    counts = np.bincount(labels, minlength=k).astype(np.float64)
    weights = counts / counts.sum()

    order = np.argsort(centers[:, 0])  # 按色相排序，展示更直观
    hues = [float(centers[i, 0]) for i in order]
    ws = [float(weights[i]) for i in order]
    return hues, ws


def analyze(image: np.ndarray, config: dict) -> dict:
    sat_min = float(config.get("color_sat_min", 40.0))
    contrast_min = float(config.get("color_contrast_min", 30.0))
    rich_min = float(config.get("color_richness_min", 0.35))
    rich_max = float(config.get("color_richness_max", 0.95))
    k = int(config.get("color_kmeans_k", 4))

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_chan, s_chan, _ = cv2.split(hsv)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    sat_mean = float(s_chan.mean())
    contrast = float(gray.std())

    # 色相直方图熵（36 个 bin，归一到 0~1）
    hist = cv2.calcHist([h_chan], [0], None, [36], [0, 180]).flatten()
    total = float(hist.sum())
    prob = hist / total if total > 0 else hist
    nz = prob[prob > 0]
    entropy = float(-(nz * np.log2(nz)).sum()) if nz.size else 0.0
    richness = max(0.0, float(entropy / np.log2(36)))  # 避免出现 -0.0

    main_hues, main_weights = _main_colors(image, k)
    harmony = _hue_concentration(main_hues, main_weights)

    sat_ok = sat_mean >= sat_min
    contrast_ok = contrast >= contrast_min
    richness_ok = rich_min <= richness <= rich_max
    passed = sat_ok and contrast_ok and richness_ok

    fail_reason: list[str] = []
    if not sat_ok:
        fail_reason.append(f"平均饱和度 {sat_mean:.1f} 偏低，画面灰暗")
    if not contrast_ok:
        fail_reason.append(f"对比度 {contrast:.1f} 偏低，层次不清")
    if richness < rich_min:
        fail_reason.append(f"色彩丰富度 {richness:.2f} 偏低，色彩单调")
    elif richness > rich_max:
        fail_reason.append(f"色彩丰富度 {richness:.2f} 偏高，色彩杂乱")

    if passed:
        label = "色彩正常"
    elif not sat_ok or not contrast_ok:
        label = "色彩平淡"
    else:
        label = "色彩杂乱"

    # 综合分 0~100（只在 UI 展示用，不影响 passed 判定逻辑）
    sat_score = min(1.0, sat_mean / sat_min) if sat_min > 0 else 1.0
    contrast_score = min(1.0, contrast / contrast_min) if contrast_min > 0 else 1.0
    if richness < rich_min:
        rich_score = richness / rich_min if rich_min > 0 else 0.0
    elif richness > rich_max:
        rich_score = max(0.0, 1.0 - (richness - rich_max))
    else:
        rich_score = 1.0
    score = float(np.clip(100.0 * (0.4 * sat_score + 0.35 * contrast_score + 0.25 * rich_score), 0.0, 100.0))

    return make_result(
        "color",
        score=score,
        label=label,
        passed=passed,
        details={
            "sat_mean": sat_mean,
            "contrast": contrast,
            "richness": richness,
            "harmony": harmony,
            "main_hues": main_hues,
            "main_weights": main_weights,
            "fail_reason": fail_reason,
        },
    )
