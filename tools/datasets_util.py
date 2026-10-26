"""
tools/datasets_util.py —— 多数据集支持（给其它脚本共用）

设计：
    datasets/
      mydata/            ← 一个数据集 = 一个子目录（含 classes.txt）
      food/              ← 另一个数据集
      .current           ← 记录"当前数据集"的名字（一行文本）

所有工具（标注/体检/训练）默认都操作"当前数据集"，
也可以用 --dataset 名字 显式指定，互不干扰 —— 这样你可以随时切换做很多个数据集。
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets"
CURRENT_FILE = DATASETS_DIR / ".current"
DEFAULT_NAME = "mydata"


def list_datasets() -> list[str]:
    """列出所有数据集（子目录里有 classes.txt 才算）。"""
    if not DATASETS_DIR.exists():
        return []
    out = []
    for d in sorted(DATASETS_DIR.iterdir()):
        if d.is_dir() and (d / "classes.txt").exists():
            out.append(d.name)
    return out


def current_name() -> str:
    """读当前数据集名；文件不存在或指向无效目录时回退。"""
    names = list_datasets()
    try:
        if CURRENT_FILE.exists():
            name = CURRENT_FILE.read_text(encoding="utf-8-sig").strip()
            if name and (DATASETS_DIR / name).is_dir():
                return name
    except OSError:
        pass
    if names:
        set_current(names[0])
        return names[0]
    return DEFAULT_NAME


def set_current(name: str) -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CURRENT_FILE.write_text(f"{name}\n", encoding="utf-8")
    except OSError:
        pass


def resolve_root(dataset: str | None = None) -> pathlib.Path:
    """返回 dataset 目录的绝对路径（dataset=None 表示用当前数据集）。"""
    name = (dataset or "").strip() or current_name()
    return DATASETS_DIR / name


def split_dir(root: pathlib.Path, split: str) -> tuple[pathlib.Path, pathlib.Path]:
    return root / "images" / split, root / "labels" / split


def count_images(root: pathlib.Path, split: str) -> int:
    d = root / "images" / split
    if not d.exists():
        return 0
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return len([p for p in d.glob("*") if p.suffix.lower() in exts])
