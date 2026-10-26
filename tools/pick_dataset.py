"""
tools/pick_dataset.py —— 让用户选一个数据集（给 bat 调用）

行为：
  * 没有任何数据集 → 提示并自动创建默认数据集，然后输出它的名字
  * 只有一个 → 直接输出它（不提问）
  * 多个 → 打印菜单（到 stderr，所以不会污染 stdout），让用户输入编号，
           选完把它写进 datasets/.current，最后把名字输出到 stdout

bat 里这样用：
    for /f "delims=" %%D in ('"%PYEXE%" "%~dp0tools\\pick_dataset.py"') do set "DSNAME=%%D"
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datasets_util as du  # noqa: E402
import init_dataset  # noqa: E402


def ensure_default() -> str:
    """一个数据集都没有时，自动建一个默认的（3 个示例类别）。"""
    root = du.DATASETS_DIR / du.DEFAULT_NAME
    root.mkdir(parents=True, exist_ok=True)
    (root / "classes.txt").write_text("person\npet\ngoods\n", encoding="utf-8")
    (root / "data.yaml").write_text(init_dataset.build_yaml(root, ["person", "pet", "goods"]),
                                    encoding="utf-8")
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    du.set_current(du.DEFAULT_NAME)
    print(f"[i] 没有数据集，已自动创建默认数据集: {du.DEFAULT_NAME}", file=sys.stderr)
    print("[i] 类别是示例值（person/pet/goods），可以随时用 init_dataset.py 改", file=sys.stderr)
    return du.DEFAULT_NAME


def pick() -> str:
    names = du.list_datasets()
    if not names:
        return ensure_default()
    if len(names) == 1:
        du.set_current(names[0])
        return names[0]

    current = du.current_name()
    print("", file=sys.stderr)
    print("可用数据集：", file=sys.stderr)
    for i, n in enumerate(names, start=1):
        img = du.count_images(du.DATASETS_DIR / n, "train")
        mark = "  <- 当前" if n == current else ""
        print(f"  [{i}] {n}   （{img} 张照片）{mark}", file=sys.stderr)
    print("", file=sys.stderr)
    while True:
        try:
            raw = input(f"选哪个数据集 1-{len(names)}（直接回车用当前）: ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        if not raw:
            du.set_current(current)
            return current
        if raw.isdigit() and 1 <= int(raw) <= len(names):
            chosen = names[int(raw) - 1]
            du.set_current(chosen)
            print(f"[i] 当前数据集已切换为: {chosen}", file=sys.stderr)
            return chosen
        print("  输入无效，请重新输入编号", file=sys.stderr)


if __name__ == "__main__":
    print(pick())
