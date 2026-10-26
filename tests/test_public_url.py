"""
test_public_url.py —— 公网隧道 URL 识别测试

背景：自检时发现正则把 cloudflared 日志里的 `https://api.trycloudflare.com`
（API 端点）误当成隧道地址，导致给出的公网链接是错的。
这个测试把那条 bug 锁死，防止回归。
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))

import public_demo  # noqa: E402


def run():
    good = [
        "https://anti-lane-bios-postings.trycloudflare.com",
        "https://specifically-herb-itunes-benchmark.trycloudflare.com",
        "https://fantastic-buyers-transition-wise.trycloudflare.com",
    ]
    bad = [
        "https://api.trycloudflare.com",          # 曾经被误认的 API 端点
        "https://www.trycloudflare.com",
        "https://update.trycloudflare.com",
        "https://abc.trycloudflare.com",          # 没有连字符，不像隧道名
        "https://example.com",
        "https://foo.trycloudflare.com.evil.com",
        "",
    ]

    for u in good:
        assert public_demo.is_tunnel_url(u) is True, f"应识别为隧道地址: {u}"
    for u in bad:
        assert public_demo.is_tunnel_url(u) is False, f"不应识别为隧道地址: {u}"

    print(f"  [OK] 正确识别 {len(good)} 个隧道地址")
    print(f"  [OK] 正确排除 {len(bad)} 个非隧道地址（含 api.trycloudflare.com 回归用例）")
    print("✅ public_url 测试通过")


if __name__ == "__main__":
    run()
