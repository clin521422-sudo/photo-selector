"""
tools/evaluate.py —— 用人工标注评估系统准确率

这是"答辩量化评估"那一页的数据来源。

用法：
    python tools\\evaluate.py --init          # 生成 data/labels.csv 模板 + data/imgs 目录
    python tools\\evaluate.py                 # 跑评估（默认 data/labels.csv + data/imgs/）
    python tools\\evaluate.py --scan          # 额外做阈值扫描，找最优 blur_threshold
    python tools\\evaluate.py --labels x.csv --images x/imgs

labels.csv 的列（只有"文件名"和"人工建议"是必填）：
    文件名, 人工建议, 人工清晰度, 人工曝光, 人工色彩, 人工主体, 备注
    - 人工建议: 建议保留 / 建议复核 / 建议淘汰
    - 人工清晰度: 清晰 / 模糊
    - 人工曝光: 正常 / 过曝 / 欠曝
    - 人工色彩: 正常 / 平淡 / 杂乱
    - 人工主体: 有 / 无
    留空 = 该项不参与评估（拿不准就留空，别瞎标）

输出：
    - 控制台摘要
    - output/eval_report_YYYYMMDD_HHMM.md（可直接贴进答辩 PPT）
"""

from __future__ import annotations

import argparse
import csv
import datetime
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG  # noqa: E402
from modules import blur as blur_module  # noqa: E402
from pipeline import analyze_image  # noqa: E402
from utils import load_and_resize  # noqa: E402

COLUMNS = ["文件名", "人工建议", "人工清晰度", "人工曝光", "人工色彩", "人工主体", "备注"]

SUGGEST_ORDER = ["建议保留", "建议复核", "建议淘汰"]
TRUTH_BLUR = {"清晰", "模糊"}
TRUTH_EXPO = {"正常", "过曝", "欠曝"}
TRUTH_COLOR = {"正常", "平淡", "杂乱"}
TRUTH_SUBJ = {"有", "无"}

SYS_BLUR = {"清晰": "清晰", "疑似模糊": "模糊"}
SYS_EXPO = {"曝光正常": "正常", "过曝": "过曝", "欠曝": "欠曝", "曝光异常": "异常"}
SYS_COLOR = {"色彩正常": "正常", "色彩平淡": "平淡", "色彩杂乱": "杂乱"}
SYS_SUBJ = {"主体突出": "有", "主体偏小": "有", "未检测到主体": "无", "模型缺失": "无"}

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


# ---------------------------------------------------------------- 初始化
def init_template(data_dir: pathlib.Path) -> int:
    img_dir = data_dir / "imgs"
    img_dir.mkdir(parents=True, exist_ok=True)
    labels = data_dir / "labels.csv"
    if labels.exists():
        print(f"[i] 已存在，未覆盖: {labels}")
        return 0
    with labels.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerow(["样例_正常.jpg", "建议保留", "清晰", "正常", "正常", "有", "这是示例，删掉即可"])
        w.writerow(["样例_模糊.jpg", "建议淘汰", "模糊", "", "", "", "拿不准的项留空"])
        w.writerow(["样例_过曝.jpg", "建议复核", "", "过曝", "", "无", ""])
    print(f"[OK] 已生成标注模板: {labels}")
    print(f"[OK] 照片目录:      {img_dir}")
    print()
    print("下一步：")
    print(f"  1) 把 60~100 张照片放进 {img_dir}")
    print(f"  2) 用 Excel 打开 {labels}，填 文件名 + 人工建议（其余列可选）")
    print("  3) 运行: python tools\\evaluate.py")
    return 0


# ---------------------------------------------------------------- 读标注
def load_labels(path: pathlib.Path) -> list[dict]:
    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            if item.get("文件名"):
                rows.append(item)
    return rows


def norm(value: str, allowed: set[str]) -> str:
    """只接受合法取值，其他（含空）视为"不评估"。"""
    v = (value or "").strip()
    return v if v in allowed else ""


# ---------------------------------------------------------------- 统计工具
def confusion_matrix(pairs: list[tuple[str, str]], labels: list[str]) -> list[list[int]]:
    idx = {lab: i for i, lab in enumerate(labels)}
    m = [[0] * len(labels) for _ in labels]
    for truth, pred in pairs:
        if truth in idx and pred in idx:
            m[idx[truth]][idx[pred]] += 1
    return m


def per_class_metrics(matrix: list[list[int]], labels: list[str]) -> list[dict]:
    out = []
    total = sum(sum(r) for r in matrix)
    for i, lab in enumerate(labels):
        tp = matrix[i][i]
        row_sum = sum(matrix[i])
        col_sum = sum(matrix[r][i] for r in range(len(labels)))
        precision = tp / col_sum if col_sum else 0.0
        recall = tp / row_sum if row_sum else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        support = row_sum
        out.append({"label": lab, "precision": precision, "recall": recall,
                    "f1": f1, "support": support})
    acc = sum(matrix[i][i] for i in range(len(labels))) / total if total else 0.0
    return out, acc, total


def fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(ROOT / "data" / "labels.csv"))
    ap.add_argument("--images", default=str(ROOT / "data" / "imgs"))
    ap.add_argument("--init", action="store_true", help="生成标注模板")
    ap.add_argument("--scan", action="store_true", help="额外做 blur 阈值扫描")
    ap.add_argument("--limit", type=int, default=0, help="只评估前 N 张（调试用）")
    args = ap.parse_args()

    data_dir = ROOT / "data"
    if args.init:
        return init_template(data_dir)

    labels_path = pathlib.Path(args.labels)
    images_dir = pathlib.Path(args.images)

    if not labels_path.exists():
        print(f"[X] 找不到标注文件: {labels_path}")
        print("    先运行: python tools\\evaluate.py --init")
        return 1
    if not images_dir.exists():
        print(f"[X] 找不到图片目录: {images_dir}")
        return 1

    rows = load_labels(labels_path)
    if args.limit:
        rows = rows[: args.limit]
    print(f"标注文件: {labels_path}  （{len(rows)} 行）")
    print(f"图片目录: {images_dir}")
    print(f"阈值配置: blur_threshold={DEFAULT_CONFIG['blur_threshold']}, "
          f"exposure_over_max={DEFAULT_CONFIG['exposure_over_max']}, "
          f"subject_min_area_ratio={DEFAULT_CONFIG['subject_min_area_ratio']}")
    print()

    suggest_pairs: list[tuple[str, str]] = []
    module_pairs: dict[str, list[tuple[str, str]]] = {"blur": [], "exposure": [], "color": [], "subject": []}
    mismatches: list[dict] = []
    blur_points: list[tuple[float, str]] = []  # (方差, 真值) 供阈值扫描
    skipped = {"空白": 0, "文件缺失": 0, "无法解码": 0, "非图片": 0}

    for i, row in enumerate(rows, start=1):
        name = row["文件名"]
        truth_suggest = norm(row.get("人工建议", ""), set(SUGGEST_ORDER))
        if not truth_suggest and not any(row.get(k) for k in
                                         ("人工清晰度", "人工曝光", "人工色彩", "人工主体")):
            skipped["空白"] += 1
            continue

        img_path = images_dir / name
        if img_path.suffix.lower() not in IMG_EXTS:
            skipped["非图片"] += 1
            continue
        if not img_path.exists():
            skipped["文件缺失"] += 1
            print(f"  [!] 找不到图片，跳过: {name}")
            continue

        try:
            result = analyze_image(str(img_path), DEFAULT_CONFIG)
        except Exception as e:
            skipped["无法解码"] += 1
            print(f"  [!] 分析失败，跳过: {name} ({type(e).__name__})")
            continue

        mods = result["modules"]
        pred_suggest = result["overall"]["suggestion"]

        # 综合建议
        if truth_suggest:
            suggest_pairs.append((truth_suggest, pred_suggest))
            if truth_suggest != pred_suggest:
                reasons = []
                for mn, mr in mods.items():
                    for r in mr["details"].get("fail_reason", []):
                        reasons.append(f"{mn}: {r}")
                mismatches.append({
                    "name": name, "truth": truth_suggest, "pred": pred_suggest,
                    "ratio": result["overall"]["pass_ratio"],
                    "reason": "；".join(reasons) or "-",
                })

        # 单模块
        t = norm(row.get("人工清晰度", ""), TRUTH_BLUR)
        if t:
            p = SYS_BLUR.get(mods["blur"]["label"], "")
            if p:
                module_pairs["blur"].append((t, p))
                blur_points.append((mods["blur"]["details"]["laplacian_var"], t))

        t = norm(row.get("人工曝光", ""), TRUTH_EXPO)
        if t:
            p = SYS_EXPO.get(mods["exposure"]["label"], "")
            if p:
                module_pairs["exposure"].append((t, p))

        t = norm(row.get("人工色彩", ""), TRUTH_COLOR)
        if t:
            p = SYS_COLOR.get(mods["color"]["label"], "")
            if p:
                module_pairs["color"].append((t, p))

        t = norm(row.get("人工主体", ""), TRUTH_SUBJ)
        if t:
            p = SYS_SUBJ.get(mods["subject"]["label"], "")
            if p:
                module_pairs["subject"].append((t, p))

        if i % 20 == 0:
            print(f"  ... 已处理 {i}/{len(rows)}")

    if not suggest_pairs and not any(module_pairs.values()):
        print("\n[X] 没有任何可用标注（所有行都是空的？）")
        print("    至少填 文件名 + 人工建议 两列")
        return 1

    # ---------- 综合建议 ----------
    print()
    print("=" * 62)
    print(" 综合建议评估")
    print("=" * 62)
    matrix = confusion_matrix(suggest_pairs, SUGGEST_ORDER)
    metrics, acc, total = per_class_metrics(matrix, SUGGEST_ORDER)
    print(f"样本数 {total}    总体准确率 {fmt_pct(acc)}")
    print()
    print(f"{'':<16}" + "".join(f"{'系统' + lab:>12}" for lab in SUGGEST_ORDER))
    for i, lab in enumerate(SUGGEST_ORDER):
        print(f"{'人工' + lab:<16}" + "".join(f"{v:>12}" for v in matrix[i]))
    print()
    for m in metrics:
        print(f"  {m['label']:<8} precision {fmt_pct(m['precision']):>7}  "
              f"recall {fmt_pct(m['recall']):>7}  F1 {fmt_pct(m['f1']):>7}  "
              f"支持数 {m['support']}")

    # ---------- 单模块 ----------
    module_report = {}
    labels_map = {"blur": ("清晰", "模糊"), "exposure": ("正常", "过曝", "欠曝"),
                  "color": ("正常", "平淡", "杂乱"), "subject": ("有", "无")}
    print()
    print("=" * 62)
    print(" 单模块准确率")
    print("=" * 62)
    for key, pairs in module_pairs.items():
        if not pairs:
            continue
        labs = list(labels_map[key])
        m2 = confusion_matrix(pairs, labs)
        _m, a2, t2 = per_class_metrics(m2, labs)
        module_report[key] = {"acc": a2, "n": t2, "matrix": m2, "labels": labs}
        print(f"  {key:<9} 准确率 {fmt_pct(a2):>7}   ({t2} 个样本)")

    # ---------- 阈值扫描 ----------
    scan_lines = []
    if args.scan and blur_points:
        print()
        print("=" * 62)
        print(" blur_threshold 阈值扫描（找最优值）")
        print("=" * 62)
        print(f"  {'阈值':>8}   {'清晰度准确率':>12}   样本 {len(blur_points)}")
        results = []
        for thr in [10, 20, 30, 40, 50, 60, 70, 80, 100, 120]:
            hit = sum(1 for var, truth in blur_points
                      if ("清晰" if var >= thr else "模糊") == truth)
            a = hit / len(blur_points)
            results.append((thr, a))

        best_acc = max(a for _, a in results)
        # 并列最优时，取最接近当前配置的那个（更符合"微调"的直觉）
        best_thr = min((t for t, a in results if abs(a - best_acc) < 1e-9),
                       key=lambda t: abs(t - DEFAULT_CONFIG["blur_threshold"]))
        for thr, a in results:
            mark = "  <<< 最优" if thr == best_thr else ""
            print(f"  {thr:>8}   {fmt_pct(a):>12}{mark}")
            scan_lines.append((thr, a))
        print()
        print(f"  最优阈值 {best_thr}（准确率 {fmt_pct(best_acc)}）；"
              f"当前配置是 {DEFAULT_CONFIG['blur_threshold']}")
        print("  把这个值填到 config.py 的 blur_threshold 即可")

    # ---------- 不一致清单 ----------
    if mismatches:
        print()
        print("=" * 62)
        print(f" 误判清单（共 {len(mismatches)} 张，最多显示 15 张）")
        print("=" * 62)
        for m in mismatches[:15]:
            print(f"  {m['name']:<24} 人工={m['truth']}  系统={m['pred']}  "
                  f"通过率={m['ratio']:.2f}")
            print(f"      原因: {m['reason'][:110]}")

    # ---------- 写报告 ----------
    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    report = out_dir / f"eval_report_{stamp}.md"

    lines = [
        "# 照片选片系统 · 评估报告",
        "",
        f"- 生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
        f"- 标注文件：`{labels_path.name}`（{len(rows)} 行）",
        f"- 图片目录：`{images_dir}`",
        f"- 阈值：blur_threshold={DEFAULT_CONFIG['blur_threshold']}, "
        f"exposure_over_max={DEFAULT_CONFIG['exposure_over_max']}, "
        f"subject_min_area_ratio={DEFAULT_CONFIG['subject_min_area_ratio']}",
        f"- 跳过：空白 {skipped['空白']}，文件缺失 {skipped['文件缺失']}，"
        f"无法解码 {skipped['无法解码']}，非图片 {skipped['非图片']}",
        "",
        "## 1. 综合建议准确率",
        "",
        f"**样本数 {total}，总体准确率 {fmt_pct(acc)}**",
        "",
        "| 人工 \\ 系统 | " + " | ".join(SUGGEST_ORDER) + " | 召回率 |",
        "|---|---|---|---|---|",
    ]
    for i, lab in enumerate(SUGGEST_ORDER):
        cells = " | ".join(str(v) for v in matrix[i])
        lines.append(f"| **{lab}** | {cells} | {fmt_pct(metrics[i]['recall'])} |")
    lines += ["", "| 类别 | Precision | Recall | F1 | 支持数 |", "|---|---|---|---|---|"]
    for m in metrics:
        lines.append(f"| {m['label']} | {fmt_pct(m['precision'])} | "
                     f"{fmt_pct(m['recall'])} | {fmt_pct(m['f1'])} | {m['support']} |")

    lines += ["", "## 2. 单模块准确率", ""]
    if module_report:
        lines += ["| 模块 | 准确率 | 样本数 |", "|---|---|---|"]
        for key, rep in module_report.items():
            lines.append(f"| {key} | {fmt_pct(rep['acc'])} | {rep['n']} |")
    else:
        lines.append("（未填单模块真值，跳过）")

    if scan_lines:
        lines += ["", "## 3. blur_threshold 阈值扫描", "",
                  "| 阈值 | 清晰度准确率 |", "|---|---|"]
        for thr, a in scan_lines:
            lines.append(f"| {thr} | {fmt_pct(a)} |")
        lines += ["", "说明：阈值不是拍脑袋定的，而是用标注样本扫描得到的。"
                      f"当前配置 {DEFAULT_CONFIG['blur_threshold']}。"]

    if mismatches:
        lines += ["", "## 4. 误判样例", "", "| 文件名 | 人工 | 系统 | 通过率 | 原因 |",
                  "|---|---|---|---|---|"]
        for m in mismatches[:20]:
            lines.append(f"| {m['name']} | {m['truth']} | {m['pred']} | "
                         f"{m['ratio']:.2f} | {m['reason'][:80]} |")

    lines += ["", "---", "", "> 由 `tools/evaluate.py` 自动生成"]
    report.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(f"[OK] 报告已保存: {report}")
    print("     可以直接贴进答辩 PPT 的「测试与评估」页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
