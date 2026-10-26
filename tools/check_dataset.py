"""
tools/check_dataset.py —— 训练数据集体检

**训练前必跑**。标错一个 class_id 或坐标超出 0~1，训练会白跑几小时才发现。

检查项：
  1. classes.txt / data.yaml 是否存在且一致
  2. 图片与标注是否配对（图片没 txt = 还没标；txt 没图片 = 脏数据）
  3. 每行格式：5 个字段、class_id 在范围内、坐标都在 0~1
  4. 各 split 的图片数、空标注数
  5. 每个类别的框数量（有没有某个类一个框都没有）

用法：
    python tools\\check_dataset.py
    python tools\\check_dataset.py --root datasets/mypet
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_classes(root: Path) -> list[str]:
    f = root / "classes.txt"
    if not f.exists():
        return []
    return [l.strip() for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def check_split(root: Path, split: str, n_classes: int) -> dict:
    img_dir = root / "images" / split
    lbl_dir = root / "labels" / split
    result = {
        "images": [], "unlabeled": 0, "empty_labels": 0,
        "orphan_labels": [], "bad_lines": [], "class_counts": Counter(),
        "errors": [], "warnings": [],
    }
    images = sorted(p for p in img_dir.glob("*") if p.suffix.lower() in IMG_EXTS) if img_dir.exists() else []
    result["images"] = images

    labeled = set()
    for img in images:
        txt = lbl_dir / f"{img.stem}.txt"
        if not txt.exists():
            result["unlabeled"] += 1
            continue
        labeled.add(txt.name)
        lines = [l.strip() for l in txt.read_text(encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            result["empty_labels"] += 1
            continue
        for lineno, line in enumerate(lines, start=1):
            parts = line.split()
            if len(parts) != 5:
                result["bad_lines"].append(f"{txt.name}:{lineno} 字段数={len(parts)}（应为 5）")
                continue
            try:
                cid = int(float(parts[0]))
                coords = [float(x) for x in parts[1:]]
            except ValueError:
                result["bad_lines"].append(f"{txt.name}:{lineno} 有非数字: {line[:40]}")
                continue
            if not (0 <= cid < n_classes):
                result["bad_lines"].append(
                    f"{txt.name}:{lineno} class_id={cid} 超出范围 0~{n_classes - 1}")
                continue
            if any(c < 0 or c > 1 for c in coords):
                result["bad_lines"].append(
                    f"{txt.name}:{lineno} 坐标不在 0~1: {[round(c, 3) for c in coords]}")
                continue
            if coords[2] <= 0 or coords[3] <= 0:
                result["bad_lines"].append(f"{txt.name}:{lineno} 宽或高为 0")
                continue
            result["class_counts"][cid] += 1

    if lbl_dir.exists():
        for txt in lbl_dir.glob("*.txt"):
            if txt.name not in labeled and not any(
                    (img_dir / f"{txt.stem}{ext}").exists() for ext in IMG_EXTS):
                result["orphan_labels"].append(txt.name)

    if result["bad_lines"]:
        result["errors"].extend(result["bad_lines"])
    if result["orphan_labels"]:
        result["errors"].append(f"{len(result['orphan_labels'])} 个标注文件没有对应图片")
    if result["unlabeled"]:
        result["warnings"].append(f"{result['unlabeled']} 张图片还没有标注（没画框的话也要建空 txt）")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="", help="数据集名字（默认当前数据集）")
    ap.add_argument("--root", default="", help="直接指定完整目录（一般不用）")
    ap.add_argument("--min-per-class", type=int, default=30,
                    help="每个类最少多少个框（低于此值会提示）")
    args = ap.parse_args()

    try:
        import datasets_util as du
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import datasets_util as du

    root = Path(args.root) if args.root else du.resolve_root(args.dataset)
    print(f"数据集目录: {root}")
    if not root.exists():
        print("[X] 目录不存在。先运行: python tools\\init_dataset.py --names \"person,pet\"")
        return 1

    classes = load_classes(root)
    if not classes:
        print("[X] 找不到 classes.txt 或内容为空")
        return 1
    print(f"类别 {len(classes)} 个: " + ", ".join(f"{i}={n}" for i, n in enumerate(classes)))

    yaml_file = root / "data.yaml"
    print(f"data.yaml : {'存在' if yaml_file.exists() else '[X] 缺失（重新跑 init_dataset.py）'}")
    if yaml_file.exists():
        text = yaml_file.read_text(encoding="utf-8")
        missing = [n for n in classes if f": {n}" not in text and f":{n}" not in text]
        if missing:
            print(f"[X] data.yaml 里缺这些类别: {missing}（可能被手改坏了）")
            print("    修复: python tools\\init_dataset.py --force --names \"...\"")
            return 1

    total_boxes = Counter()
    total_imgs = 0
    total_unlabeled = 0
    split_imgs = {}
    errors: list[str] = []
    warnings: list[str] = []

    for split in ("train", "val"):
        r = check_split(root, split, len(classes))
        n = len(r["images"])
        split_imgs[split] = n
        total_imgs += n
        total_unlabeled += r["unlabeled"]
        total_boxes.update(r["class_counts"])

        print()
        print(f"[{split}] 图片 {n} 张" + (f"，其中 {r['empty_labels']} 张是空标注（背景图）"
                                          if r["empty_labels"] else ""))
        if n == 0:
            warnings.append(f"{split} 没有任何图片")
        for cid, cnt in sorted(r["class_counts"].items()):
            print(f"    {classes[cid]:<16} {cnt} 个框")
        if r["unlabeled"]:
            print(f"    [!] {r['unlabeled']} 张图片没有对应 txt")
        if r["orphan_labels"]:
            print(f"    [X] {len(r['orphan_labels'])} 个孤儿标注，例如: {r['orphan_labels'][:3]}")
        if r["bad_lines"]:
            print(f"    [X] {len(r['bad_lines'])} 行格式错，例如:")
            for b in r["bad_lines"][:5]:
                print(f"        {b}")
        errors.extend([f"[{split}] {e}" for e in r["errors"]])
        warnings.extend([f"[{split}] {w}" for w in r["warnings"]])

    print()
    print("=" * 60)
    print(f" 总计：图片 {total_imgs} 张，框 {sum(total_boxes.values())} 个，"
          f"未标注 {total_unlabeled} 张")
    print("=" * 60)

    # ---------- 训练前的硬性条件 ----------
    if split_imgs.get("train", 0) == 0:
        errors.append("train 没有图片，无法训练")
    if split_imgs.get("val", 0) == 0:
        errors.append("val 没有图片：先运行 python tools\\init_dataset.py --split 0.2")
    if total_unlabeled > 0:
        errors.append(
            f"{total_unlabeled} 张图片还没有标注 —— 用 数据标注.bat 画框，"
            f"或对'画面里没有目标'的图手动建同名空 txt")

    if total_boxes:
        print("\n各类框数量（训练建议每类 ≥300）：")
        for cid, name in enumerate(classes):
            cnt = total_boxes.get(cid, 0)
            flag = "  [!] 偏少" if cnt < args.min_per_class else ""
            print(f"  {cid} {name:<16} {cnt:>5}{flag}")
        for cid, name in enumerate(classes):
            if total_boxes.get(cid, 0) == 0:
                errors.append(f"类别 {name} 一个框都没有（训练时会被忽略）")
            elif total_boxes.get(cid, 0) < args.min_per_class:
                warnings.append(f"类别 {name} 只有 {total_boxes.get(cid)} 个框，建议补到 300+")

    if errors:
        print("\n[X] 发现 %d 个错误（必须修好再训练）：" % len(errors))
        for e in errors[:20]:
            print(f"    {e}")
    if warnings:
        print("\n[!] %d 个提醒：" % len(warnings))
        for w in warnings[:10]:
            print(f"    {w}")

    print()
    if errors:
        print("❌ 数据集还有问题，先修完再训练")
        return 1
    print("✅ 数据集检查通过，可以训练了：双击 训练模型.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
