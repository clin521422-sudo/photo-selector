"""
tools/get_cloudflared.py —— 下载 cloudflared（公网穿透用）

GitHub releases 在国内经常连不上，所以默认走 gh-proxy 镜像下载。
下完直接放在 tools/bin/cloudflared.exe。

用法：
    python tools/get_cloudflared.py
    python tools/get_cloudflared.py --mirror https://github.com   （直连试试）
"""

from __future__ import annotations

import argparse
import pathlib
import ssl
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BIN_DIR = ROOT / "tools" / "bin"
TARGET = BIN_DIR / "cloudflared.exe"

GH_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
MIRRORS = [
    "https://gh-proxy.com/" + GH_URL,
    "https://ghproxy.net/" + GH_URL,
    GH_URL,
]


def download(url: str, timeout: int = 300) -> int:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    tmp = TARGET.with_suffix(".exe.part")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
            if total:
                print(f"\r  {n / 1024 / 1024:6.1f} / {total / 1024 / 1024:.1f} MB", end="", flush=True)
    tmp.replace(TARGET)
    print(f"\r  下载完成 {TARGET.stat().st_size / 1024 / 1024:.1f} MB，用时 {time.time() - t0:.0f} 秒")
    return TARGET.stat().st_size


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", default=None, help="只用指定镜像/直连地址")
    args = ap.parse_args()

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET.exists() and TARGET.stat().st_size > 10_000_000:
        print(f"[i] 已存在: {TARGET} ({TARGET.stat().st_size / 1024 / 1024:.1f} MB)")
        print("    要重新下载就先删掉它")
        return 0

    urls = [args.mirror] if args.mirror else MIRRORS
    for url in urls:
        print(f"[..] 尝试: {url[:70]}{'...' if len(url) > 70 else ''}")
        try:
            size = download(url)
            if size > 10_000_000:
                print("[OK] cloudflared 下载成功，现在可以双击 公网演示.bat 了")
                return 0
            print("[!] 大小不对，换下一个源")
        except Exception as e:
            print(f"[X] 失败: {type(e).__name__}: {str(e)[:80]}")

    print("\n[X] 所有源都失败了。可以手动下载后放到:")
    print(f"    {TARGET}")
    print(f"    下载地址: {GH_URL}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
