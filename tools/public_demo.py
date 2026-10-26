"""
tools/public_demo.py —— 一键公网演示编排脚本

做四件事：
  1. 检查/启动本地 Streamlit 服务（8501）
  2. 启动 Cloudflare Quick Tunnel（免费、无需账号、自动 HTTPS）
  3. 自动抓出公网 URL + 生成二维码 + 验证公网真的能访问
  4. 等你按回车，然后自动关闭隧道（并停掉它自己启动的服务）

为什么强制 --protocol http2：
    很多国内网络下 Cloudflare 的 QUIC(UDP 7844) 不通，默认协议会直接失败
    （表现为 HTTP 530 + cloudflared 退出）。HTTP/2 走 TCP 443，最稳。

用法：
    双击 公网演示.bat
    或 python tools/public_demo.py
    自检模式（自动起、验证、关，不需要人守着）：python tools/public_demo.py --selftest
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOUDFLARED = ROOT / "tools" / "bin" / "cloudflared.exe"
PORT = 8501
LOCAL_URL = f"http://127.0.0.1:{PORT}"
URL_RE = re.compile(r"https://([a-z0-9-]+)\.trycloudflare\.com")

# cloudflared 日志里会出现一些基础设施域名（比如 api.trycloudflare.com），
# 它们不是隧道地址，必须排除。真正的 quick tunnel 名字是几个随机单词用连字符拼的。
RESERVED_SUBDOMAINS = {
    "api",
    "www",
    "update",
    "h3",
    "quic",
    "region1",
    "region2",
    "cloudflare",
    "trycloudflare",
}


def is_tunnel_url(url: str) -> bool:
    """判断是不是真正的 quick tunnel 地址（排除 api.* 这类基础设置域名）。"""
    m = URL_RE.match(url)
    if not m:
        return False
    sub = m.group(1)
    if sub in RESERVED_SUBDOMAINS:
        return False
    return sub.count("-") >= 1  # 随机隧道名至少是"词-词"形式


# ---------------------------------------------------------------- 基础工具
def port_open(port: int = PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except Exception:
        return False


def http_ok(url: str, timeout: float = 10) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait_until(cond, timeout: float, interval: float = 1.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(interval)
    return False


def banner(text: str) -> None:
    print()
    print("=" * 64)
    print(f" {text}")
    print("=" * 64)


# ---------------------------------------------------------------- 服务
def ensure_server():
    """返回 (进程对象或None, 是否由本脚本启动)。"""
    if port_open():
        print(f"[i] 检测到 {PORT} 已在监听，复用已有服务")
        return None, False

    if not http_ok(f"{LOCAL_URL}/_stcore/health", timeout=2) and port_open():
        print("[!] 端口被占用但健康检查失败，仍尝试继续")

    print(f"[..] 启动本地服务 {LOCAL_URL}")
    tmp = ROOT / ".tmp"
    tmp.mkdir(exist_ok=True)
    log = open(tmp / "streamlit_demo.log", "w", encoding="utf-8", errors="replace")

    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.headless", "true", "--server.port", str(PORT),
         "--browser.gatherUsageStats", "false"],
        cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        env=env, creationflags=flags,
    )

    if not wait_until(lambda: http_ok(f"{LOCAL_URL}/_stcore/health"), timeout=90):
        proc.terminate()
        print("[X] 本地服务启动超时，日志尾部：")
        try:
            print((tmp / "streamlit_demo.log").read_text(encoding="utf-8", errors="replace")[-1200:])
        except OSError:
            pass
        return None, False

    print("[OK] 本地服务已启动")
    return proc, True


def start_tunnel():
    """启动 cloudflared，返回 (进程, 公网URL)。"""
    print("[..] 建立 Cloudflare 隧道（http2 协议）…")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        [str(CLOUDFLARED), "tunnel", "--url", LOCAL_URL,
         "--protocol", "http2", "--no-autoupdate"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
        bufsize=1, creationflags=flags,
    )

    state = {"url": None, "lines": []}
    lock = threading.Lock()

    def reader():
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                with lock:
                    state["lines"].append(line.rstrip())
                    if len(state["lines"]) > 400:
                        del state["lines"][:200]
                    for m in URL_RE.finditer(line):
                        url = m.group(0)
                        # 只认真正的隧道域名，别被日志里的 api.trycloudflare.com 骗了
                        if is_tunnel_url(url) and not state["url"]:
                            state["url"] = url
        except Exception:
            pass

    threading.Thread(target=reader, daemon=True).start()

    end = time.time() + 150
    while time.time() < end:
        if state["url"]:
            return proc, state["url"]
        if proc.poll() is not None:
            print("[X] cloudflared 已退出，输出尾部：")
            with lock:
                for line in state["lines"][-15:]:
                    print("   ", line)
            return None, None
        time.sleep(0.5)

    print("[X] 等待隧道 URL 超时，输出尾部：")
    with lock:
        for line in state["lines"][-15:]:
            print("   ", line)
    return None, None


def show_qr(url: str, open_image: bool = True) -> None:
    try:
        import qrcode

        out_dir = ROOT / "output"
        out_dir.mkdir(exist_ok=True)
        png = out_dir / "public_demo_qr.png"
        qrcode.make(url).save(png)
        print(f"[OK] 二维码已生成: {png}")
        if open_image:
            try:
                os.startfile(str(png))  # type: ignore[attr-defined]
            except Exception:
                pass
    except Exception as e:
        print(f"[i] 二维码生成跳过（{type(e).__name__}）")


def password_hint() -> str:
    try:
        sys.path.insert(0, str(ROOT))
        import config

        return config.get_app_password()
    except Exception:
        return "（见 secret.txt）"


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="自动验证后立刻关闭，不需要人工按键")
    args = ap.parse_args()

    banner("照片选片系统 · 公网演示（Cloudflare Tunnel）")

    if not CLOUDFLARED.exists():
        print(f"[X] 找不到 {CLOUDFLARED}")
        print("    先运行：python tools\\get_cloudflared.py")
        return 2

    server_proc, server_started_by_us = ensure_server()
    if server_proc is None and not http_ok(f"{LOCAL_URL}/_stcore/health"):
        print("[X] 本地服务不可用，退出")
        return 1

    # Cloudflare 免费隧道偶尔会分到一条连不通的（表现为公网一直 530）。
    # 所以最多尝试两次：第一次不通就丢掉重开一条。
    tunnel_proc = None
    url = ""
    reachable = False
    for attempt in (1, 2):
        tunnel_proc, url = start_tunnel()
        if not tunnel_proc or not url:
            if server_started_by_us and server_proc:
                server_proc.terminate()
            return 1

        print(f"[..] 等待公网地址生效（第 {attempt}/2 次，通常十几秒）…")
        reachable = wait_until(lambda: http_ok(f"{url}/_stcore/health", timeout=8), timeout=90)
        if reachable:
            print("[OK] 公网访问验证通过（HTTP 200）")
            break

        print("[!] 这条隧道暂时连不通（Cloudflare 侧问题），换一条重试…")
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=10)
        except Exception:
            try:
                tunnel_proc.kill()
            except Exception:
                pass
        tunnel_proc = None

    if not reachable:
        print("[!] 两条隧道都没连通。可能是网络环境限制（比如出口被封），")
        print("    可以稍后重试，或改用 cpolar / ngrok 等其他穿透服务。")

    banner("公网地址已就绪")
    print(f"  公网地址 : {url}")
    print(f"  本机地址 : {LOCAL_URL}")
    print(f"  访问密码 : {password_hint()}   （公网访问需要，局域网免密码）")
    print()
    print("  手机用 4G/5G 打开上面的公网地址即可验证（会要求输密码）。")
    print("  提示：这个地址是公开的，演示完请务必关闭隧道。")
    print()
    show_qr(url, open_image=not args.selftest)

    if args.selftest:
        print("\n[SELFTEST] 自检模式：立即关闭隧道")
        tunnel_proc.terminate()
        if server_started_by_us and server_proc:
            server_proc.terminate()
        time.sleep(3)
        alive = tunnel_proc.poll() is None
        print(f"[SELFTEST] 隧道已关闭: {not alive}")
        print(f"[SELFTEST] URL 曾为: {url}")
        return 0 if reachable else 3

    print()
    try:
        input(">>> 演示结束后按【回车】关闭隧道…")
    except (EOFError, KeyboardInterrupt):
        print()

    print("[..] 正在关闭隧道…")
    try:
        tunnel_proc.terminate()
        tunnel_proc.wait(timeout=15)
    except Exception:
        try:
            tunnel_proc.kill()
        except Exception:
            pass

    if server_started_by_us and server_proc:
        try:
            server_proc.terminate()
            server_proc.wait(timeout=10)
        except Exception:
            pass
        print("[OK] 隧道和本地服务都已关闭")
    else:
        print("[OK] 隧道已关闭（本地服务是复用的，保持运行）")

    print(f"[i] 公网地址已失效: {url}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except KeyboardInterrupt:
        print("\n[i] 已中断")
        code = 130
    sys.stdout.flush()
    sys.exit(code)
