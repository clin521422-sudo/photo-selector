"""
config.py —— 所有阈值集中在这里（禁止在模块里硬编码数字）

阈值命名规范：<模块名>_<指标>_<min|max|threshold>
这些默认值是起点，请用自己的样本集（3 号收集的 data/labels.csv）校准后覆盖。
"""

from __future__ import annotations

import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent

# ============================================================
# 公网访问保护
# ============================================================
# 局域网内直接访问（同一 WiFi 打开电脑 IP）不需要密码；
# 通过内网穿透 / 公网服务器访问时需要密码。判断逻辑见 auth.py。
#
# 密码优先级：环境变量 PHOTO_APP_PASSWORD > secret.txt > 下面的默认值
# 强烈建议：自己建一个 secret.txt 写密码（已 gitignore），别用默认值。
APP_PASSWORD_DEFAULT = "changeme"
APP_PASSWORD_SECRET_FILE = ROOT / "secret.txt"


def _parse_password_file(text: str) -> str:
    """从 secret.txt 里取密码：跳过空行和 # 注释，取第一行有效内容。"""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return ""


def get_app_password() -> str:
    """读取访问密码：环境变量 > secret.txt > 默认值。"""
    env = os.environ.get("PHOTO_APP_PASSWORD", "").strip()
    if env:
        return env
    try:
        if APP_PASSWORD_SECRET_FILE.exists():
            v = _parse_password_file(APP_PASSWORD_SECRET_FILE.read_text(encoding="utf-8"))
            if v:
                return v
    except OSError:
        pass
    return APP_PASSWORD_DEFAULT


DEFAULT_CONFIG: dict = {
    # ---------- 图像预处理 ----------
    "target_long_side": 1024,  # 统一缩放长边，只缩不放

    # ---------- 模糊度（拉普拉斯方差） ----------
    # 40 是用本项目样图实测校准的结果：清晰图 51~124，模糊图 2.7。
    # 网上流传的经验值 100 并不通用（平滑棚拍的人像只有 50 左右会被误判）。
    # 换自己的数据集后，请用 tools/calibrate.py 重新定这个值。
    "blur_threshold": 40.0,    # 方差 >= 该值视为清晰

    # ---------- 曝光 ----------
    "exposure_over_thr": 245,      # 灰度 >= 该值算高光溢出
    "exposure_under_thr": 10,      # 灰度 <= 该值算暗部死黑
    "exposure_over_max": 0.05,     # 过曝像素占比上限
    "exposure_under_max": 0.05,    # 欠曝像素占比上限
    "exposure_mean_min": 60,       # 平均亮度下限
    "exposure_mean_max": 190,      # 平均亮度上限
    "exposure_dynamic_range_min": 80,  # P99 - P1 下限

    # ---------- 色彩 ----------
    "color_sat_min": 40.0,         # 平均饱和度下限（0~255）
    "color_contrast_min": 30.0,    # 灰度标准差下限
    "color_richness_min": 0.35,    # 色相熵归一化下限
    "color_richness_max": 0.95,    # 色相熵归一化上限
    "color_kmeans_k": 4,           # 主色个数

    # ---------- 主体（YOLO） ----------
    "subject_model_path": "models/yolov8n.onnx",
    "subject_conf_threshold": 0.25,
    "subject_iou_threshold": 0.45,
    "subject_min_area_ratio": 0.05,   # 最大主体面积占比下限
    "subject_max_center_offset": 0.35,  # 中心偏移上限（仅作提示）
    "subject_input_size": 640,
    "subject_max_objects": 20,      # 最多保留的检测框数
}

# 综合建议阈值：通过率 -> 建议
OVERALL_SUGGEST = {
    "keep": 1.0,     # 全通过 -> 建议保留
    "review": 0.5,   # >= 0.5 -> 建议复核
}
