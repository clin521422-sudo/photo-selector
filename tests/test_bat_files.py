"""
test_bat_files.py —— 批处理文件规范测试

已经踩过两次的坑，用测试锁死：
  1. bat 里**不能有非 ASCII 字符**（中文也不行，连 echo 中文文件名都不行）
     cmd.exe 按系统代码页（中文 Windows = GBK/936）逐行解析 bat，
     UTF-8 中文的多字节序列会"吃掉"后面的英文字符，
     例：activate → tivate、goto → oto、install → nstall
  2. bat 必须用 **CRLF** 换行（纯 LF 会让 goto / 括号块解析出错）

顺带检查：每个 bat 都非空、都能被读到。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

BATS = sorted(p for p in ROOT.glob("*.bat"))


def run():
    assert BATS, "项目根目录没有找到任何 .bat 文件"
    problems = []

    for bat in BATS:
        data = bat.read_bytes()

        # 1. 非 ASCII 检查
        bad = [b for b in data if b > 127]
        if bad:
            where = []
            for i, line in enumerate(data.split(b"\n"), start=1):
                if any(b > 127 for b in line):
                    where.append(i)
            problems.append(f"{bat.name}: 含 {len(bad)} 个非 ASCII 字节（行 {where[:5]}）")

        # 2. 换行符检查
        text = data.decode("ascii", errors="replace")
        crlf = text.count("\r\n")
        lf_only = len([m for m in text.split("\n") if True]) - 1 - crlf
        if crlf == 0:
            problems.append(f"{bat.name}: 没有任何 CRLF（纯 LF 换行，cmd 解析不稳）")
        elif lf_only > 0:
            problems.append(f"{bat.name}: 混用换行（CRLF={crlf}, 纯LF={lf_only}）")

        # 3. 非空
        if len(data) < 20:
            problems.append(f"{bat.name}: 文件过小（{len(data)} 字节）")

    if problems:
        for p in problems:
            print(f"  [X] {p}")
        raise AssertionError(f"{len(problems)} 个 bat 文件不合规")

    print(f"  [OK] {len(BATS)} 个 bat 全部：纯 ASCII + CRLF 换行 + 非空")
    for bat in BATS:
        size = bat.stat().st_size
        print(f"       {bat.name:<24} {size:>5} 字节")


if __name__ == "__main__":
    run()
    print("✅ bat 文件规范测试通过")
