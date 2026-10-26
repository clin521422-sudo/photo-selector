"""
storage.py —— 上传照片的分类归档（NAS 式）

手机上打开 Web 界面上传照片后，照片会自动保存到电脑上的分类文件夹：

    received/
        建议保留/
        建议复核/
        建议回避/     <- 界面上叫"建议淘汰"，文件夹为了语义柔和叫"建议回避"
        manifest.csv  <- 归档清单（时间/文件名/分类/各项分数/路径）
        .index.json   <- 去重索引（MD5 -> 路径）

为什么要去重：
    Streamlit 每次交互（比如拖动阈值滑块）都会重新执行整个脚本，
    上传的文件会被再次"保存"。用 MD5 索引判断，同一张图只归档一次。
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parent
RECEIVED = ROOT / "received"
INDEX_FILE = RECEIVED / ".index.json"
MANIFEST_FILE = RECEIVED / "manifest.csv"

# 综合建议 -> 归档文件夹名（"建议淘汰"对用户太硬，文件夹用"建议回避"）
CATEGORY_DIRS = {
    "建议保留": "建议保留",
    "建议复核": "建议复核",
    "建议淘汰": "建议回避",
}

MANIFEST_HEADER = [
    "时间", "原文件名", "分类", "通过率",
    "清晰度分数", "清晰度标签",
    "曝光分数", "曝光标签",
    "色彩分数", "色彩标签",
    "主体分数", "主体标签",
    "主体类别", "未通过原因", "保存路径", "MD5",
]


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _load_index() -> dict:
    try:
        if INDEX_FILE.exists():
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_index(index: dict) -> None:
    try:
        RECEIVED.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def _safe_name(name: str) -> str:
    """只取文件名部分，去掉 Windows 非法字符，防止路径穿越。"""
    name = pathlib.Path(str(name).replace("\\", "/")).name
    for ch in '<>:"|?*':
        name = name.replace(ch, "_")
    name = name.strip().strip(".")
    return name or "photo.jpg"


def _append_manifest(row: dict, saved_relpath: str) -> None:
    RECEIVED.mkdir(parents=True, exist_ok=True)
    is_new = not MANIFEST_FILE.exists() or MANIFEST_FILE.stat().st_size == 0
    mod = row["modules"]
    fail_text = "；".join(
        f"{k}:{v}" for k, v in (row.get("fail_text") or {}).items() if v
    )
    record = [
        time.strftime("%Y-%m-%d %H:%M:%S"),
        row["name"],
        row["suggestion"],
        f"{row['pass_ratio']:.2f}",
        f"{mod['blur']['score']:.1f}", mod["blur"]["label"],
        f"{mod['exposure']['score']:.1f}", mod["exposure"]["label"],
        f"{mod['color']['score']:.1f}", mod["color"]["label"],
        f"{mod['subject']['score']:.1f}", mod["subject"]["label"],
        mod["subject"]["details"].get("top_class", ""),
        fail_text,
        saved_relpath,
        row["md5"],
    ]
    # 用 utf-8-sig，Excel 直接双击打开不会乱码
    with MANIFEST_FILE.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(MANIFEST_HEADER)
        w.writerow(record)


def save_photo(data: bytes, filename: str, row: dict) -> dict:
    """
    归档一张照片。

    row 是界面里的单张结果字典：
        {"name", "md5", "suggestion", "pass_ratio", "modules", "fail_text"}

    返回 {"saved": bool, "deduped": bool, "path": str}
    """
    h = row["md5"]
    index = _load_index()

    if h in index:
        return {"saved": True, "deduped": True, "path": index[h]}

    folder = RECEIVED / CATEGORY_DIRS.get(row["suggestion"], "建议复核")
    folder.mkdir(parents=True, exist_ok=True)

    name = _safe_name(filename)
    target = folder / name
    if target.exists():  # 同名但内容不同（MD5 不同），加哈希前缀避免覆盖
        target = folder / f"{h[:8]}_{name}"

    try:
        target.write_bytes(data)
    except OSError as e:
        return {"saved": False, "deduped": False, "path": "", "error": str(e)}

    rel = str(target.relative_to(RECEIVED))
    index[h] = rel
    _save_index(index)
    try:
        _append_manifest(row, rel)
    except OSError:
        pass

    return {"saved": True, "deduped": False, "path": rel}


def stats() -> dict:
    """统计已归档数量（按分类）。"""
    out = {}
    for cat, dirname in CATEGORY_DIRS.items():
        d = RECEIVED / dirname
        out[cat] = len([p for p in d.glob("*") if p.is_file()]) if d.exists() else 0
    out["总计"] = sum(v for k, v in out.items() if k != "总计")
    return out
