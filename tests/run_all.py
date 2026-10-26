"""
tests/run_all.py —— 一键跑全部测试

用法：
    python tests/run_all.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = [
    "test_blur",
    "test_exposure",
    "test_color",
    "test_subject",
    "test_pipeline",
    "test_auth",
    "test_public_url",
    "test_doc_consistency",
    "test_bat_files",
    "test_evaluate",
    "test_dataset_tools",
]


def main() -> int:
    failed = []
    for name in TESTS:
        print(f"\n{'=' * 60}\n>>> {name}\n{'=' * 60}", flush=True)
        r = subprocess.run(
            [sys.executable, str(ROOT / "tests" / f"{name}.py")],
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            failed.append(name)

    print(f"\n{'=' * 60}", flush=True)
    if failed:
        print(f"❌ 有 {len(failed)} 个测试失败: {', '.join(failed)}", flush=True)
        return 1
    print(f"✅ 全部 {len(TESTS)} 个测试通过", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
