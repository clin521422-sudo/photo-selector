"""
tools/init_dataset.py —— 初始化自定义训练数据集

一条命令搭好目录 + 类别表 + data.yaml，之后就能直接用标注工具打开。

用法：
    :: 1) 定义你的类别（顺序 = class_id，从 0 开始，逗号分隔）
    python tools\\init_dataset.py --names "person,pet,goods,food"

    :: 2) 把照片放进 datasets/mydata/images/train/
    :: 3) 标注（双击 数据标注.bat）
    :: 4) 标完后划分验证集（把 20% 挪到 val）
    python tools\\init_dataset.py --split 0.2

    :: 换别的位置/名字
    python tools\\init_dataset.py --root datasets/mypet --names "cat,dog"

产出目录结构：
    datasets/mydata/
    ├── classes.txt          ← 类别表（一行一个，顺序即 class_id）
    ├── data.yaml            ← 训练配置（自动生成，不用手写）
    ├── images/train/        ← 你的照片
    ├── images/val/          ← 自动从 train 里抽 20%
    ├── labels/train/        ← 标注生成的 txt
    └── labels/val/
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def build_yaml(dataset_root: Path, names: list[str]) -> str:
    lines = [
        "# auto generated. class order must match classes.txt (ASCII only for safety).",
        f"path: {dataset_root.as_posix()}",
        "train: images/train",
        "val: images/val",
        "",
        "names:",
    ]
    for i, n in enumerate(names):
        lines.append(f"  {i}: {n}")
    return "\n".join(lines) + "\n"


def do_split(dataset_root: Path, ratio: float, seed: int = 42) -> int:
    """把 images/train 里的一部分照片（连同已有标注）移到 val。"""
    src_img = dataset_root / "images" / "train"
    dst_img = dataset_root / "images" / "val"
    src_lbl = dataset_root / "labels" / "train"
    dst_lbl = dataset_root / "labels" / "val"
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src_img.glob("*") if p.suffix.lower() in IMG_EXTS)
    if not files:
        print(f"[!] {src_img} 里没有图片，无法划分")
        return 0
    random.seed(seed)
    random.shuffle(files)
    n_val = max(1, int(len(files) * ratio)) if len(files) > 1 else 0
    moved = 0
    for f in files[:n_val]:
        shutil.move(str(f), str(dst_img / f.name))
        lab = src_lbl / f"{f.stem}.txt"
        if lab.exists():
            shutil.move(str(lab), str(dst_lbl / lab.name))
        moved += 1
    print(f"[OK] 已把 {moved} 张照片从 train 移到 val（比例 {ratio:.0%}，随机种子固定可复现）")
    return moved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="", help="逗号分隔的类别名，如 person,pet,goods")
    ap.add_argument("--name", default="mydata", help="数据集名字（datasets/<name>）")
    ap.add_argument("--root", default="", help="直接指定完整目录（一般不用）")
    ap.add_argument("--split", type=float, default=0.0, help="把这么多比例的照片从 train 移到 val")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的 classes.txt")
    args = ap.parse_args()

    # 多数据集支持：默认建在 datasets/<name>，并设为"当前数据集"
    try:
        import datasets_util as du
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import datasets_util as du

    root = Path(args.root) if args.root else du.DATASETS_DIR / args.name
    if not args.root:          # 只有用 --name 建的数据集才设为当前（--root 用于测试）
        du.set_current(root.name)
    names = [n.strip() for n in args.names.replace("，", ",").split(",") if n.strip()]

    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (root / sub).mkdir(parents=True, exist_ok=True)

    classes_file = root / "classes.txt"
    if args.names:
        if classes_file.exists() and not args.force:
            print(f"[!] {classes_file} 已存在，未覆盖（要改类别请加 --force）")
            names = [l.strip() for l in classes_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        else:
            classes_file.write_text("\n".join(names) + "\n", encoding="utf-8")
            print(f"[OK] 已写入类别表: {classes_file}  （{len(names)} 类）")
    elif classes_file.exists():
        names = [l.strip() for l in classes_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    else:
        classes_file.write_text("person\npet\ngoods\n", encoding="utf-8")
        names = ["person", "pet", "goods"]
        print(f"[i] 没给 --names，已写入示例类别表（去改成你自己的）: {classes_file}")

    yaml_file = root / "data.yaml"
    yaml_file.write_text(build_yaml(root, names), encoding="utf-8")
    print(f"[OK] 已生成训练配置: {yaml_file}")

    if args.split > 0:
        print()
        do_split(root, args.split)

    n_train = len([p for p in (root / "images" / "train").glob("*") if p.suffix.lower() in IMG_EXTS])
    n_val = len([p for p in (root / "images" / "val").glob("*") if p.suffix.lower() in IMG_EXTS])

    print()
    print("=" * 58)
    print(f" 数据集: {root}")
    print(f" 类别({len(names)}): {', '.join(f'{i}={n}' for i, n in enumerate(names))}")
    print(f" 图片: train {n_train} 张, val {n_val} 张")
    print(f" 已设为当前数据集: {root.name}")
    print("=" * 58)
    print()
    print("下一步：")
    print(f"  1) 把照片放进 {root / 'images' / 'train'}")
    print("  2) 双击 数据标注.bat 开始画框")
    print("  3) 标完双击 整理数据.bat（自动划验证集 + 体检）")
    print("  4) 双击 训练模型.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
