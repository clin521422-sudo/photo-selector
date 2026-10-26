"""
test_evaluate.py —— 评估脚本测试

用 samples/ 里 6 张图的**已知结果**造一份标注表，验证：
  1. evaluate.py 能跑通、退出码 0
  2. 标注完全正确时，准确率 = 100%
  3. 故意写错一条标注后，准确率下降且误判清单里出现该文件
  4. --scan 能给出阈值扫描结果并选出最优值
  5. --init 能生成模板（表头正确）

注意：这些"真值"就是我们用 samples 实测出来的系统结果，
      所以这里测的是**评估脚本的统计逻辑**，不是系统准确率。
"""

import csv
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import ROOT, SAMPLES  # noqa: E402

EVAL = ROOT / "tools" / "evaluate.py"

# samples/ 六张图的实测系统结论（见 README 第 5.2 节）
KNOWN = [
    ("normal.jpg", "建议保留", "清晰", "正常", "正常", "有"),
    ("blurred.jpg", "建议复核", "模糊", "正常", "正常", "有"),
    ("gray.jpg", "建议复核", "清晰", "正常", "平淡", "有"),
    ("over.jpg", "建议复核", "清晰", "过曝", "平淡", "有"),
    ("under.jpg", "建议淘汰", "模糊", "欠曝", "平淡", "有"),
    ("subject_dog.jpg", "建议复核", "清晰", "欠曝", "正常", "有"),
]

COLUMNS = ["文件名", "人工建议", "人工清晰度", "人工曝光", "人工色彩", "人工主体", "备注"]


def write_labels(path: pathlib.Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for r in rows:
            w.writerow(r)


def run_eval(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(EVAL), *args],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def run():
    # 注意：不用 tempfile.mkdtemp —— 它创建的目录权限在受限环境下会写不进去，
    # 这里直接在项目内用固定目录，测试结束删掉。
    tmp = ROOT / ".evtest"
    tmp.mkdir(exist_ok=True)
    try:
        # ---------- 1. 标注完全正确 ----------
        good = tmp / "good.csv"
        write_labels(good, [(n, s, b, e, c, sj, "") for n, s, b, e, c, sj in KNOWN])
        r1 = run_eval("--labels", str(good), "--images", str(SAMPLES))
        assert r1.returncode == 0, f"evaluate.py 退出码 {r1.returncode}\n{r1.stderr[-800:]}"
        out1 = r1.stdout + r1.stderr
        assert "总体准确率 100.0%" in out1, f"标注正确时应 100%，实际输出:\n{out1[-900:]}"
        print("  [OK] 标注全对 → 总体准确率 100%")

        assert "blur" in out1 and "exposure" in out1 and "color" in out1, "应有单模块准确率"
        print("  [OK] 单模块准确率也输出了（blur/exposure/color/subject）")

        # ---------- 2. 故意写错一条 ----------
        bad = tmp / "bad.csv"
        rows = [(n, s, b, e, c, sj, "") for n, s, b, e, c, sj in KNOWN]
        rows[1] = ("blurred.jpg", "建议保留", "模糊", "正常", "正常", "有", "故意标错")
        write_labels(bad, rows)
        r2 = run_eval("--labels", str(bad), "--images", str(SAMPLES))
        assert r2.returncode == 0
        out2 = r2.stdout + r2.stderr
        assert "总体准确率 100.0%" not in out2, "标错一条后准确率不该还是 100%"
        assert "83.3%" in out2 or "66.7%" in out2, f"6 张错 1 张应约 83.3%，输出:\n{out2[-600:]}"
        assert "误判清单" in out2 and "blurred.jpg" in out2, "误判清单应列出该文件"
        print("  [OK] 标错一条 → 准确率下降 + 误判清单列出该文件")

        # ---------- 3. 阈值扫描 ----------
        r3 = run_eval("--labels", str(good), "--images", str(SAMPLES), "--scan")
        out3 = r3.stdout + r3.stderr
        assert "阈值扫描" in out3, "应输出阈值扫描"
        assert "最优阈值" in out3, "应给出最优阈值"
        assert "最优阈值 40" in out3, f"本批样本最优应接近当前默认 40，输出:\n{out3[-700:]}"
        print("  [OK] --scan 阈值扫描正常，并选出最优阈值 40")

        # ---------- 4. --init 模板 ----------
        r4 = run_eval("--init")
        out4 = r4.stdout + r4.stderr
        template = ROOT / "data" / "labels.csv"
        assert r4.returncode == 0
        assert "labels.csv" in out4 or "已存在" in out4
        if template.exists():
            header = template.read_text(encoding="utf-8-sig").splitlines()[0]
            assert header.replace("\ufeff", "").startswith("文件名,人工建议"), f"表头不对: {header}"
        print("  [OK] --init 模板生成/已存在，表头正确")

        print("✅ evaluate 评估脚本测试通过")
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    run()
