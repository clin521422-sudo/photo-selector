"""
tools/finalize_dataset.py —— 标注完成后的一步处理（给"整理数据.bat"调用）

做三件事：
  1. 如果 val 里还没有照片 → 自动把 20% 从 train 挪过去（已挪过就不重复挪）
  2. 跑数据集体检（格式 / class_id / 坐标 / 孤儿 / 未标注 / 类别框数）
  3. 通过后提示下一步去训练

用法：
    python tools\\finalize_dataset.py                # 当前数据集
    python tools\\finalize_dataset.py --dataset food
    python tools\\finalize_dataset.py --split 0.15
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datasets_util as du  # noqa: E402
import init_dataset  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="", help="数据集名字（默认当前数据集）")
    ap.add_argument("--split", type=float, default=0.2, help="验证集比例，默认 0.2")
    args = ap.parse_args()

    root = du.resolve_root(args.dataset)
    if not root.exists() or not (root / "classes.txt").exists():
        print(f"[X] 数据集不存在: {root}")
        print("    先双击 数据标注.bat（会自动创建），或运行 init_dataset.py")
        return 1

    du.set_current(root.name)
    n_train = du.count_images(root, "train")
    n_val = du.count_images(root, "val")
    print(f"数据集: {root}")
    print(f"照片: train {n_train} 张, val {n_val} 张")

    if n_train == 0:
        print()
        print("[X] train 里没有照片。先把照片放进:")
        print(f"    {root / 'images' / 'train'}")
        return 1

    # ---------- 1. 划分验证集（幂等：val 非空就不再拆） ----------
    if n_val == 0:
        print()
        print(f"[1/2] val 是空的，自动把 {args.split:.0%} 的照片挪到 val ...")
        init_dataset.do_split(root, args.split)
    else:
        print()
        print("[1/2] val 里已经有照片，跳过划分")

    # ---------- 2. 体检 ----------
    print()
    print("[2/2] 数据集体检 ...")
    print("-" * 60)
    r = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__).resolve().parent / "check_dataset.py"),
         "--dataset", root.name],
        cwd=str(du.ROOT),
    )
    if r.returncode != 0:
        print()
        print("=" * 60)
        print(" 数据还没准备好，按上面的红色提示补齐后再双击一次本文件")
        print(" 常见：还有照片没画框 / val 为空 / 某类框太少")
        print("=" * 60)
        return 1

    print()
    print("=" * 60)
    print(" 数据准备完成 ✅  下一步：双击 训练模型.bat")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
