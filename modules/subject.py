"""
主体分析模块 —— YOLOv8n ONNX + cv2.dnn（不需要 PyTorch）

为什么要用 YOLO 而不是 Haar / Saliency：
  * Haar 级联基本只认正面人脸，对光照、遮挡、姿态很敏感
  * Saliency 只能找出"视觉上突出的区域"，并不知道画面里到底有没有目标
  * YOLO 能同时给出"是什么"（类别）和"在哪里"（边界框），才是真正的主体判断

实现要点：
  * 模型用 cv2.dnn.readNetFromONNX 加载，纯 CPU 推理，单张 640x640 几十毫秒
  * 输入必须在模块内部做 letterbox（等比缩放 + 灰边填充），保持宽高比，
    后处理时再用 scale 和 (left, top) 把框映射回原图坐标
  * 输出张量格式 (1, 4 + num_classes, N)：前 4 行是 cx,cy,w,h，后面是各类别分数（无 objectness）
"""

from __future__ import annotations

import pathlib

import cv2
import numpy as np

from schema import make_result

ROOT = pathlib.Path(__file__).resolve().parent.parent

# COCO 80 类
COCO_NAMES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
]

_NET_CACHE: dict[str, cv2.dnn.Net] = {}


def load_class_names(model_path: pathlib.Path) -> list[str]:
    """
    读取模型的类别名。

    优先级：
      1. 模型旁边的同名 `.names.txt`（如 models/mydata.onnx → models/mydata.names.txt）
         —— 自己训练的模型用这个，训练脚本会自动生成，**不用改代码**
      2. 都没有就用 COCO 80 类（官方 yolov8n.onnx 就是这种）
    """
    sidecar = pathlib.Path(model_path).with_suffix(".names.txt")
    try:
        if sidecar.exists():
            names = [ln.strip() for ln in sidecar.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if names:
                return names
    except OSError:
        pass
    return COCO_NAMES


def _resolve_model_path(path: str) -> pathlib.Path:
    p = pathlib.Path(path)
    return p if p.is_absolute() else ROOT / p


def _load_net(path: pathlib.Path) -> cv2.dnn.Net:
    key = str(path)
    if key not in _NET_CACHE:
        net = cv2.dnn.readNetFromONNX(str(path))
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)  # pip 版 opencv 不支持 CUDA 后端
        _NET_CACHE[key] = net
    return _NET_CACHE[key]


def letterbox(image: np.ndarray, new_size: int = 640, color=(114, 114, 114)):
    """等比缩放 + 灰边填充，返回 (图, scale, pad_left, pad_top)。"""
    h, w = image.shape[:2]
    scale = min(new_size / h, new_size / w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

    canvas = np.full((new_size, new_size, 3), color, dtype=np.uint8)
    left = (new_size - nw) // 2
    top = (new_size - nh) // 2
    canvas[top : top + nh, left : left + nw] = resized
    return canvas, scale, left, top


def _postprocess(out: np.ndarray, image_shape, scale: float, pad_left: int, pad_top: int,
                 conf_thr: float, iou_thr: float, max_objects: int,
                 names: list[str] | None = None):
    """解析 (1, 4+nc, N) 输出 -> 原图坐标下的框。"""
    pred = out[0]
    if pred.ndim != 2:
        pred = np.squeeze(pred)
    # 统一成 (N, 4+nc)
    if pred.shape[0] < pred.shape[1]:
        pred = pred.T

    h0, w0 = image_shape[:2]
    boxes_xywh: list[list[float]] = []
    boxes_xyxy: list[list[float]] = []
    scores: list[float] = []
    class_ids: list[int] = []

    for row in pred:
        cls_scores = row[4:]
        cid = int(np.argmax(cls_scores))
        conf = float(cls_scores[cid])
        if conf < conf_thr:
            continue

        cx, cy, bw, bh = (float(v) for v in row[:4])
        # letterbox 坐标 -> 原图坐标
        x1 = (cx - bw / 2 - pad_left) / scale
        y1 = (cy - bh / 2 - pad_top) / scale
        x2 = (cx + bw / 2 - pad_left) / scale
        y2 = (cy + bh / 2 - pad_top) / scale
        x1, y1 = max(0.0, x1), max(0.0, y1)
        x2, y2 = min(float(w0 - 1), x2), min(float(h0 - 1), y2)
        if x2 <= x1 or y2 <= y1:
            continue

        boxes_xywh.append([x1, y1, x2 - x1, y2 - y1])
        boxes_xyxy.append([x1, y1, x2, y2])
        scores.append(conf)
        class_ids.append(cid)

    if not boxes_xywh:
        return [], [], []

    idxs = cv2.dnn.NMSBoxes(boxes_xywh, scores, conf_thr, iou_thr)
    if isinstance(idxs, tuple):  # 某些 OpenCV 版本返回 (indices, scores)
        idxs = idxs[0]
    idxs = np.array(idxs, dtype=np.int64).reshape(-1) if len(idxs) else np.array([], dtype=np.int64)

    picked = []
    names = names or COCO_NAMES
    for i in idxs[:max_objects]:
        cid = int(class_ids[int(i)])
        picked.append(
            {
                "xyxy": [round(v, 1) for v in boxes_xyxy[int(i)]],
                "conf": round(scores[int(i)], 3),
                "cls_id": cid,
                "cls_name": names[cid] if cid < len(names) else str(cid),
            }
        )
    picked.sort(key=lambda d: (d["xyxy"][2] - d["xyxy"][0]) * (d["xyxy"][3] - d["xyxy"][1]), reverse=True)
    return picked, scores, class_ids


def analyze(image: np.ndarray, config: dict) -> dict:
    model_path = _resolve_model_path(str(config.get("subject_model_path", "models/yolov8n.onnx")))
    if not model_path.exists():
        return make_result(
            "subject", 0.0, "模型缺失", False,
            {"error": f"找不到模型文件: {model_path}", "fail_reason": ["YOLO 模型文件缺失"]},
        )

    conf_thr = float(config.get("subject_conf_threshold", 0.25))
    iou_thr = float(config.get("subject_iou_threshold", 0.45))
    min_ratio = float(config.get("subject_min_area_ratio", 0.05))
    max_offset = float(config.get("subject_max_center_offset", 0.35))
    in_size = int(config.get("subject_input_size", 640))
    max_objects = int(config.get("subject_max_objects", 20))

    net = _load_net(model_path)

    lb, scale, pad_left, pad_top = letterbox(image, in_size)
    blob = cv2.dnn.blobFromImage(
        lb, 1.0 / 255.0, (in_size, in_size), swapRB=True, crop=False
    )
    net.setInput(blob)
    out = net.forward()

    boxes, _, _ = _postprocess(
        out, image.shape, scale, pad_left, pad_top, conf_thr, iou_thr, max_objects,
        names=load_class_names(model_path),
    )

    h0, w0 = image.shape[:2]
    img_area = float(w0 * h0)
    num_objects = len(boxes)

    max_area_ratio = 0.0
    center_offset = 1.0
    top_class = ""
    if num_objects > 0:
        main = boxes[0]  # 已经按面积降序
        x1, y1, x2, y2 = main["xyxy"]
        max_area_ratio = float((x2 - x1) * (y2 - y1) / img_area)
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        # 归一化中心偏移：0 = 正中，1 = 贴边
        dx = abs(cx - w0 / 2.0) / max(w0 / 2.0, 1e-6)
        dy = abs(cy - h0 / 2.0) / max(h0 / 2.0, 1e-6)
        center_offset = float(min(1.0, max(dx, dy)))
        top_class = main["cls_name"]

    passed = bool(num_objects > 0 and max_area_ratio >= min_ratio)

    fail_reason: list[str] = []
    notes: list[str] = []
    if num_objects == 0:
        label = "未检测到主体"
        fail_reason.append("未检测到 COCO 预定义类别（人/车/动物等）的目标")
    elif not passed:
        label = "主体偏小"
        fail_reason.append(f"最大主体面积占比 {max_area_ratio:.1%}，低于 {min_ratio:.0%}")
    else:
        label = "主体突出"
        if center_offset > max_offset:
            notes.append(f"主体偏离中心 {center_offset:.2f}（构图提示，不影响通过）")

    score = float(np.clip(100.0 * max_area_ratio, 0.0, 100.0))

    return make_result(
        "subject",
        score=score,
        label=label,
        passed=passed,
        details={
            "max_area_ratio": max_area_ratio,
            "center_offset": center_offset,
            "num_objects": num_objects,
            "top_class": top_class,
            "boxes": boxes,
            "fail_reason": fail_reason,
            "notes": notes,
        },
    )
