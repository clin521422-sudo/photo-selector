"""
tools/train_custom.py —— 训练自己的 YOLO 模型并导出 ONNX 给本系统用

⚠️ 这个脚本要在 **yolo 环境**（装了 torch + ultralytics 的那个）里运行，
   不是 photo-selector 的轻量环境。最简单的方式：双击 `训练模型.bat`。

它做四件事：
  1. 读 datasets/*/classes.txt，确认类别数
  2. 用 ultralytics 训练（默认从官方 yolov8n.pt 迁移学习）
  3. 把 best.pt 导出成 ONNX（opset 12，cv2.dnn 能读）
  4. 把 onnx 复制到 photo-selector/models/，并写一个同名 .names.txt（类别名）
     —— 系统会自动读这个 .names.txt，所以**不用改代码**

用法：
    训练模型.bat                        :: 默认 100 epochs
    训练模型.bat --epochs 200 --imgsz 800
    python tools\\train_custom.py --help
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # photo-selector/
PHOTO_MODELS = ROOT / "models"


def read_classes(data_yaml: Path) -> list[str]:
    """优先读同目录的 classes.txt；没有就从 data.yaml 里解析 names。"""
    classes_txt = data_yaml.parent / "classes.txt"
    if classes_txt.exists():
        names = [l.strip() for l in classes_txt.read_text(encoding="utf-8").splitlines() if l.strip()]
        if names:
            return names
    text = data_yaml.read_text(encoding="utf-8")
    names = []
    in_names = False
    for line in text.splitlines():
        if line.strip().startswith("names:"):
            in_names = True
            continue
        if in_names:
            if not line.strip():
                continue
            if ":" in line and line.startswith((" ", "\t")):
                names.append(line.split(":", 1)[1].strip())
            else:
                break
    return names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="", help="数据集名字（默认当前数据集）")
    ap.add_argument("--data", default="", help="直接指定 data.yaml 路径（一般不用）")
    ap.add_argument("--base", default="", help="基础模型 .pt（默认自动找 yolov8n.pt / yolo11n.pt）")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--name", default="", help="产出模型名（默认=数据集名）")
    ap.add_argument("--export-only", action="store_true", help="跳过训练，只导出上次的 best.pt")
    args = ap.parse_args()

    # 多数据集：默认用"当前数据集"
    try:
        import datasets_util as du
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import datasets_util as du

    if args.data:
        data_yaml = Path(args.data)
        ds_name = args.name or data_yaml.parent.name
    else:
        ds_root = du.resolve_root(args.dataset)
        data_yaml = ds_root / "data.yaml"
        ds_name = args.name or ds_root.name
    if not args.name:
        args.name = ds_name

    # ---------- 0. 环境与数据检查 ----------
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[X] 当前 Python 没有 ultralytics。")
        print("    请在 yolo 环境里运行本脚本，或直接双击 训练模型.bat")
        return 2

    if not data_yaml.exists():
        print(f"[X] 找不到 {data_yaml}")
        print("    先双击 数据标注.bat（会自动建数据集），或运行 init_dataset.py")
        return 1

    names = read_classes(data_yaml)
    if not names:
        print(f"[X] 无法从 {data_yaml.parent / 'classes.txt'} 读到类别")
        return 1
    print(f"数据集: {data_yaml}")
    print(f"类别({len(names)}): {', '.join(names)}")
    print()

    # 训练数据统计（快速确认 val 不是空的）
    ds_root = data_yaml.parent
    for split in ("train", "val"):
        d = ds_root / "images" / split
        n = len([p for p in d.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}]) if d.exists() else 0
        print(f"  {split}: {n} 张")
        if n == 0:
            print(f"[X] {split} 没有图片，无法训练（先双击 整理数据.bat）")
            return 1
    print()

    # ---------- 1. 选基础模型 ----------
    base = args.base
    if not base:
        for cand in (ROOT / "weights" / "yolov8n.pt",
                     ROOT.parent / "yolo" / "weights" / "yolov8n.pt",
                     ROOT.parent / "yolo" / "weights" / "yolo11n.pt"):
            if cand.exists():
                base = str(cand)
                break
    if not base or not Path(base).exists():
        base = "yolov8n.pt"  # 让 ultralytics 自动下载
    print(f"基础模型: {base}")
    print()

    best_pt = None
    if not args.export_only:
        # ---------- 2. 训练 ----------
        print("=" * 60)
        print(f" 开始训练：epochs={args.epochs}, imgsz={args.imgsz}, batch={args.batch}")
        print("=" * 60)
        model = YOLO(base)
        results = model.train(
            data=str(data_yaml),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            project=str(ROOT / "runs" / "train"),
            name=args.name,
            exist_ok=True,
            pretrained=True,
        )
        save_dir = Path(getattr(results, "save_dir", ROOT / "runs" / "train" / args.name))
        best_pt = save_dir / "weights" / "best.pt"
    else:
        cand = ROOT / "runs" / "train" / args.name / "weights" / "best.pt"
        if cand.exists():
            best_pt = cand
    if not best_pt or not best_pt.exists():
        print(f"[X] 找不到训练好的 best.pt（预期在 runs/train/{args.name}/weights/）")
        return 1

    # ---------- 3. 导出 ONNX ----------
    print()
    print("=" * 60)
    print(" 导出 ONNX（opset 12，cv2.dnn 可读）")
    print("=" * 60)
    export_model = YOLO(str(best_pt))
    onnx_path = Path(export_model.export(format="onnx", imgsz=args.imgsz, opset=12, simplify=False))
    print(f"[OK] ONNX: {onnx_path}")

    # ---------- 4. 复制进项目 + 写类别名 ----------
    PHOTO_MODELS.mkdir(parents=True, exist_ok=True)
    dst_onnx = PHOTO_MODELS / f"{args.name}.onnx"
    shutil.copy2(onnx_path, dst_onnx)
    names_file = dst_onnx.with_suffix(".names.txt")
    names_file.write_text("\n".join(names) + "\n", encoding="utf-8")

    print()
    print("=" * 60)
    print(" 完成！文件已就位")
    print("=" * 60)
    print(f"  模型:   {dst_onnx}")
    print(f"  类别名: {names_file}   （系统会自动读取，不用改代码）")
    print()
    print("接下来两步：")
    print(f"  1) 改 config.py 的 subject_model_path 为： \"models/{args.name}.onnx\"")
    print("  2) 验证：双击 跑测试.bat")
    print()
    print("注意：")
    print("  · tests/test_subject.py 里断言了 top_class == \"dog\"，换模型后这个测试会红，")
    print("    把断言改成你新模型的某个类别名即可（或者标一张带该类的样例图）。")
    print("  · 训练结果曲线、混淆矩阵在 runs/train/%s/ 下，答辩可以用。" % args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
