"""
tools/json2yolo.py —— 把标注工具存的 JSON 自动转成 YOLO txt

为什么需要这一步：
    X-AnyLabeling 保存的是它自己的 `.json` 格式（绝对像素坐标），
    而 YOLO 训练读的是 `.txt`（归一化的 class x_center y_center w h）。
    手动在 GUI 里点导出很麻烦，所以"整理数据.bat"会自动调用本脚本转换。

规则：
    * 矩形/多边形/旋转框 → 一律取外接矩形（bbox）
    * 坐标用 json 里的 imageWidth/imageHeight 归一化到 0~1
    * label 必须在 classes.txt 里（大小写不敏感）；不在的会跳过并提示
    * 没有 shapes 的图 → 写一个空 txt（YOLO 用它当"背景负样本"）
    * json 保留不删（随时能回去改）

用法：
    python tools\\json2yolo.py                 # 当前数据集
    python tools\\json2yolo.py --dataset food
    python tools\\json2yolo.py --quiet         # 少打印
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datasets_util as du  # noqa: E402


def load_classes(root: pathlib.Path) -> list[str]:
    f = root / "classes.txt"
    if not f.exists():
        return []
    return [ln.strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]


def shape_to_bbox(shape: dict) -> tuple[float, float, float, float] | None:
    """各种形状统一取外接矩形。"""
    pts = shape.get("points") or []
    if not pts:
        return None
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def convert_one(json_path: pathlib.Path, out_txt: pathlib.Path,
                classes: list[str], extra_dirs: list[pathlib.Path],
                unknown: dict[str, int]) -> tuple[int, int]:
    """返回 (写入的框数, 跳过的框数)。"""
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        unknown[f"<坏文件 {json_path.name}>"] = 1
        return 0, 0

    w = float(data.get("imageWidth") or 0)
    h = float(data.get("imageHeight") or 0)

    # 没有尺寸信息就去图里问（用 PIL，streamlit 已带 pillow）
    if w <= 0 or h <= 0:
        stem = json_path.stem
        for d in extra_dirs:
            for ext in (".jpg", ".jpeg", ".png", ".JPG", ".bmp", ".webp"):
                cand = d / f"{stem}{ext}"
                if cand.exists():
                    try:
                        from PIL import Image
                        with Image.open(cand) as im:
                            w, h = im.size
                    except Exception:
                        pass
                    break
            if w > 0:
                break
    if w <= 0 or h <= 0:
        unknown[f"<无法确定尺寸 {json_path.name}>"] = 1
        return 0, 0

    lower = {c.lower(): i for i, c in enumerate(classes)}
    lines: list[str] = []
    kept = skipped = 0
    for shape in data.get("shapes") or []:
        label = str(shape.get("label", "")).strip()
        bbox = shape_to_bbox(shape)
        if bbox is None:
            continue
        cid = lower.get(label.lower())
        if cid is None:
            unknown[label or "<空标签>"] = unknown.get(label or "<空标签>", 0) + 1
            skipped += 1
            continue
        x1, y1, x2, y2 = bbox
        x1, x2 = max(0.0, min(x1, x2)), min(w, max(x1, x2))
        y1, y2 = max(0.0, min(y1, y2)), min(h, max(y1, y2))
        bw, bh = x2 - x1, y2 - y1
        if bw <= 1 or bh <= 1:
            skipped += 1
            continue
        cx = (x1 + x2) / 2.0 / w
        cy = (y1 + y2) / 2.0 / h
        lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw / w:.6f} {bh / h:.6f}")
        kept += 1

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return kept, skipped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="", help="数据集名字（默认当前数据集）")
    ap.add_argument("--root", default="", help="直接指定完整目录（测试/特殊场景用）")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    root = pathlib.Path(args.root) if args.root else du.resolve_root(args.dataset)
    if not root.exists():
        print(f"[X] 数据集不存在: {root}")
        return 1
    classes = load_classes(root)
    if not classes:
        print(f"[X] {root / 'classes.txt'} 不存在或为空")
        return 1

    if not args.quiet:
        print(f"数据集: {root.name}   类别: {', '.join(classes)}")
        print("把标注工具存的 .json 转成 YOLO .txt ...")

    total_files = total_boxes = total_skipped = 0
    unknown: dict[str, int] = {}
    per_split = {}

    for split in ("train", "val"):
        img_dir, lbl_dir = du.split_dir(root, split)
        if not lbl_dir.exists():
            continue
        jsons = sorted(lbl_dir.glob("*.json"))
        if not jsons:
            continue
        n_files = n_boxes = n_skip = 0
        for jp in jsons:
            txt = jp.with_suffix(".txt")
            kept, skipped = convert_one(jp, txt, classes, [img_dir], unknown)
            n_boxes += kept
            n_skip += skipped
            if jp.exists():
                n_files += 1
        per_split[split] = (n_files, n_boxes, n_skip)
        total_files += n_files
        total_boxes += n_boxes
        total_skipped += n_skip

    if total_files == 0:
        print("[i] 没找到 .json 标注文件（还没开始画？或已经转换过了）")
        return 0

    if not args.quiet:
        for split, (f, b, s) in per_split.items():
            print(f"  [{split}] {f} 个 json -> {b} 个框" + (f"，跳过 {s} 个框" if s else ""))

    if unknown:
        print()
        print("[!] 这些标签不在 classes.txt 里，对应的框被跳过了：")
        for name, cnt in sorted(unknown.items(), key=lambda x: -x[1]):
            print(f"      {name}  ({cnt} 个)")
        print("    处理办法：把标签加进 classes.txt（顺序不能变），")
        print(f"      或者用 init_dataset.py --force --names \"...\" 重写类别表后重新转换")
        print("    （注意：改类别表后，已有的 txt 里的 class_id 含义会跟着变）")

    if total_skipped and not unknown:
        print(f"[!] 有 {total_skipped} 个框因为尺寸过小被跳过")

    print(f"[OK] 转换完成：{total_files} 个标注文件，共 {total_boxes} 个框 "
          f"-> {root / 'labels'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
