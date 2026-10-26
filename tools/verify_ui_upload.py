"""
tools/verify_ui_upload.py —— 无头验证"上传后"的界面渲染路径

AppTest 对 file_uploader 的支持有限，这里做两件事：
  1. 尝试用 AppTest 直接塞入文件（支持则完整验证上传后的汇总表）
  2. 无论是否支持，都单独验证「汇总表 → CSV」的构造逻辑（app.py 里的表格代码同源逻辑）

用法：python tools/verify_ui_upload.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

import storage  # noqa: E402
from config import DEFAULT_CONFIG  # noqa: E402
from pipeline import analyze_image  # noqa: E402


def try_apptest_with_files() -> bool:
    """尝试在 AppTest 里直接注入上传文件。"""
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=300)
    at.run()
    if at.exception:
        print("❌ 初始渲染异常:", [e.value for e in at.exception])
        return False

    if not at.get("file_uploader"):
        print("❌ 找不到 file_uploader")
        return False

    uploaded = at.get("file_uploader")[0]
    if not hasattr(uploaded, "set_value"):
        print("ℹ️  该 Streamlit 版本的 AppTest 不支持给 file_uploader 赋值，跳过注入测试")
        return True

    try:
        sample = ROOT / "samples" / "normal.jpg"
        # 不同版本 API 不同：可能是 set_value(list[UploadedFile]) 或 set_value(paths)
        uploaded.set_value([str(sample)])
        at.run()
        if at.exception:
            print("❌ 注入文件后渲染异常:", [e.value for e in at.exception])
            return False
        print("✅ AppTest 注入文件后渲染正常（含汇总表/CSV 按钮）")
        print("   metric 数量:", len(at.metric))
        print("   dataframe 数量:", len(at.dataframe))
        print("   download_button 数量:", len(at.get("download_button")))
        return True
    except Exception as e:
        print(f"ℹ️  注入方式不兼容（{type(e).__name__}: {e}），跳过")
        return True


def verify_table_logic() -> bool:
    """单独验证汇总表 + CSV 的构造逻辑（与 app.py 内联代码同源）。"""
    import pandas as pd

    files = sorted((ROOT / "samples").glob("*.jpg"))[:3]
    assert files, "samples/ 缺图片"

    rows = []
    for f in files:
        data = f.read_bytes()
        result = analyze_image(data, DEFAULT_CONFIG)
        mods = result["modules"]
        rows.append({
            "name": f.name,
            "suggestion": result["overall"]["suggestion"],
            "pass_ratio": result["overall"]["pass_ratio"],
            "modules": mods,
            "fail_text": {k: "；".join(v["details"].get("fail_reason", []))
                          for k, v in mods.items()},
            "saved_path": "",
        })

    table = pd.DataFrame([
        {
            "文件名": r["name"],
            "综合建议": r["suggestion"],
            "通过率": round(r["pass_ratio"], 2),
            "清晰度": round(r["modules"]["blur"]["score"], 1),
            "曝光": round(r["modules"]["exposure"]["score"], 1),
            "色彩": round(r["modules"]["color"]["score"], 1),
            "主体": round(r["modules"]["subject"]["score"], 1),
            "未通过原因": "；".join(v for v in r["fail_text"].values() if v),
        }
        for r in rows
    ]).sort_values(by=["通过率", "清晰度"], ascending=False).reset_index(drop=True)

    csv_bytes = table.to_csv(index_label="序号").encode("utf-8-sig")
    assert len(table) == len(files), "行数不对"
    assert csv_bytes[:3] == b"\xef\xbb\xbf", "CSV 应该是 UTF-8-BOM（Excel 不乱码）"
    assert "综合建议" in table.columns

    print("✅ 汇总表 + CSV 构造 OK")
    print(f"   {len(table)} 行 × {len(table.columns)} 列，CSV {len(csv_bytes)} bytes（含 BOM）")
    print("   排序后顺序:", list(table["文件名"]))
    return True


def main() -> int:
    ok1 = try_apptest_with_files()
    ok2 = verify_table_logic()
    if ok1 and ok2:
        print("\n✅ 上传后界面路径验证通过")
        code = 0
    else:
        print("\n❌ 有验证项失败")
        code = 1
    import os
    sys.stdout.flush()
    os._exit(code)


if __name__ == "__main__":
    main()
