"""
模糊度分析模块 —— 拉普拉斯方差法

原理：
  清晰图像的边缘锐利，灰度变化剧烈；模糊图像边缘弥散、灰度变化平缓。
  拉普拉斯算子能放大这种灰度突变，方差衡量突变的整体强度。
  因此：方差越大越清晰，越小越模糊。

注意：
  * 用 cv2.CV_64F 保存拉普拉斯结果，防止 8 位溢出/截断导致方差失真
  * 方差与分辨率强相关，所以必须由 pipeline 统一缩放到同一长边后再计算
"""

from __future__ import annotations

import cv2
import numpy as np

from schema import make_result


def analyze(image: np.ndarray, config: dict) -> dict:
    threshold = float(config.get("blur_threshold", 100.0))

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 轻微降噪，避免高 ISO 噪点被当成"边缘"抬高分数
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    var = float(lap.var())

    passed = var >= threshold
    label = "清晰" if passed else "疑似模糊"
    fail_reason = [] if passed else [f"拉普拉斯方差 {var:.1f} 低于阈值 {threshold:.1f}"]

    return make_result(
        "blur",
        score=var,
        label=label,
        passed=passed,
        details={
            "laplacian_var": var,
            "threshold": threshold,
            "fail_reason": fail_reason,
        },
    )
