"""
tools/run_demo.py —— 命令行版演示（不需要开浏览器，答辩备用）

对 samples/ 里的图片跑一遍完整流程，打印每个维度的分数和综合建议，
并把带检测框的结果图保存到 output/。

用法：
    python tools/run_demo.py
    python tools/run_demo.py 你的照片目录
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from config import DEFAULT_CONFIG  # noqa: E402
from pipeline import MODULE_TITLES, analyze_image  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def draw_boxes(image, boxes):
    vis = image.copy()
    for b in boxes:
        x1, y1, x2, y2 = (int(v) for v in b["xyxy"])
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 200, 0), 2)
        text = f"{b['cls_name']} {b['conf']:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(vis, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), (0, 200, 0), -1)
        cv2.putText(vis, text, (x1 + 2, max(12, y1 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return vis


def main():
    target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "samples"
    files = sorted(p for p in target.rglob("*") if p.suffix.lower() in EXTS)
    if not files:
        print(f"{target} 里没有图片")
        return 1

    out_dir = ROOT / "output"
    out_dir.mkdir(exist_ok=True)

    print("=" * 96)
    print(f"照片选片辅助系统 · 命令行演示    共 {len(files)} 张   分析分辨率长边 {DEFAULT_CONFIG['target_long_side']}")
    print("=" * 96)
    print(f"{'文件':<20}{'清晰度':>10}{'曝光':>10}{'色彩':>10}{'主体':>10}   {'综合建议':<8}{'耗时':>7}")
    print("-" * 96)

    for f in files:
        try:
            res = analyze_image(str(f), DEFAULT_CONFIG)
        except Exception as e:
            print(f"{f.name:<20} 失败: {type(e).__name__}: {e}")
            continue

        m = res["modules"]
        cells = []
        for name in ("blur", "exposure", "color", "subject"):
            r = m[name]
            mark = "✓" if r["passed"] else "✗"
            cells.append(f"{r['score']:.0f}{mark}")
        ov = res["overall"]
        print(f"{f.name:<20}{cells[0]:>10}{cells[1]:>10}{cells[2]:>10}{cells[3]:>10}"
              f"   {ov['suggestion']:<8}{res['meta']['elapsed_ms']:>6.0f}ms")

        boxes = m["subject"]["details"].get("boxes", [])
        vis = draw_boxes(res["image"], boxes) if boxes else res["image"]
        cv2.imwrite(str(out_dir / f"anno_{f.stem}.jpg"), vis)

    print("-" * 96)
    print("图例: ✓=通过  ✗=未通过；分数含义见各模块 details 说明")
    print(f"带检测框的结果图已保存到: {out_dir}")
    print("\n各维度未通过原因（逐张）：")
    has_any = False
    for f in files:
        try:
            res = analyze_image(str(f), DEFAULT_CONFIG)
        except Exception:
            continue
        fails = []
        for name, r in res["modules"].items():
            for reason in r["details"].get("fail_reason", []):
                fails.append(f"{MODULE_TITLES.get(name, name)}: {reason}")
        if fails:
            has_any = True
            print(f"  {f.name}")
            for x in fails:
                print(f"    · {x}")
    if not has_any:
        print("  （全部通过）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
