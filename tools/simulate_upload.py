"""
tools/simulate_upload.py —— 模拟"手机上传"整条链路（不开浏览器）

作用：把 samples/ 里的照片当成手机上传的文件，走一遍
      分析 → 归档 的完整流程，用来验证：
        1. 分类文件夹是否正确创建
        2. manifest.csv 是否正确追加
        3. 重复上传是否被去重（同一张图不会存两遍）

跑两次就能看到去重效果：
    python tools/simulate_upload.py
    python tools/simulate_upload.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DEFAULT_CONFIG  # noqa: E402
from pipeline import analyze_image  # noqa: E402
import storage  # noqa: E402

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main() -> int:
    files = sorted(p for p in (ROOT / "samples").glob("*") if p.suffix.lower() in EXTS)
    if not files:
        print("samples/ 里没有图片，先跑 tools/make_samples.py")
        return 1

    print(f"模拟上传 {len(files)} 张照片\n")
    print(f"{'文件':<20}{'综合建议':<10}{'归档结果':<12}{'路径'}")
    print("-" * 88)

    new = dup = 0
    for f in files:
        data = f.read_bytes()
        result = analyze_image(data, DEFAULT_CONFIG)
        mods = result["modules"]
        row = {
            "name": f.name,
            "data": data,
            "md5": storage.md5_bytes(data),
            "result": result,
            "suggestion": result["overall"]["suggestion"],
            "pass_ratio": result["overall"]["pass_ratio"],
            "modules": mods,
            "fail_text": {k: "；".join(v["details"].get("fail_reason", []))
                          for k, v in mods.items()},
        }
        info = storage.save_photo(data, f.name, row)
        if not info["saved"]:
            status = "失败"
        elif info["deduped"]:
            status = "重复跳过"
            dup += 1
        else:
            status = "新增"
            new += 1
        print(f"{f.name:<20}{result['overall']['suggestion']:<10}{status:<12}{info['path']}")

    print("-" * 88)
    print(f"新增 {new} 张，重复跳过 {dup} 张")
    s = storage.stats()
    print(f"累计归档：保留 {s['建议保留']} ｜ 复核 {s['建议复核']} ｜ 回避 {s['建议淘汰']} ｜ 总计 {s['总计']}")

    print("\n目录结构：")
    for cat in storage.CATEGORY_DIRS.values():
        d = storage.RECEIVED / cat
        names = sorted(p.name for p in d.glob("*") if p.is_file()) if d.exists() else []
        print(f"  received/{cat}/  ({len(names)} 个)  {names}")

    if storage.MANIFEST_FILE.exists():
        lines = storage.MANIFEST_FILE.read_text(encoding="utf-8-sig").splitlines()
        print(f"\nmanifest.csv: {len(lines) - 1} 条记录，表头 {len(lines[0].split(','))} 列")
        print(f"  最新一条: {lines[-1][:150]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
