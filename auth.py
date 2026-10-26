"""
auth.py —— 访问来源判断 + 公网密码门禁

设计目标：
    * 局域网直接访问（手机/电脑在同一 WiFi，直连电脑 IP）→ 免密码，随手就能用
    * 通过内网穿透 / 公网服务器访问 → 必须输入密码

判断依据（为什么不只看 IP）：
    走 ngrok / cpolar / Cloudflare Tunnel 这类穿透时，请求是"本机代理"转进来的，
    Streamlit 看到的客户端 IP 往往就是 127.0.0.1；真正的访客 IP 在转发头里。
    所以规则是：

        1. 只要发现任何代理转发头（x-forwarded-for / x-real-ip / cf-connecting-ip / forwarded）
           → 一律视为"公网访问"，要求密码。
           （这样即使有人伪造 x-forwarded-for: 192.168.1.1 想蒙混过关，
             结果也只是"更严格"，永远不会被绕开）
        2. 没有任何转发头 + 客户端 IP 是私网地址（10./172.16-31./192.168./127./::1）
           → 局域网直连，免密码
        3. 没有任何转发头 + 客户端是公网 IP
           → 公网直连（比如路由器端口映射进来的），要求密码
        4. 完全拿不到 IP（本地脚本 / 单元测试环境）
           → 按本机处理，免密码

密码来源（优先级从高到低）：
    1. 环境变量 PHOTO_APP_PASSWORD
    2. 项目根目录的 secret.txt（已 gitignore，适合放自己的密码）
    3. config.py 里的 APP_PASSWORD_DEFAULT（默认值，记得改）
"""

from __future__ import annotations

import hmac
import ipaddress
import time

import streamlit as st

import config

# 这些头一旦出现，就说明请求经过了代理/穿透，必须密码
PROXY_HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "cf-connecting-ip",
    "forwarded",
    "x-forwarded-host",
    "x-forwarded-proto",
)

# 暴力尝试限制：同一来源 IP，5 分钟内最多失败 5 次
MAX_FAILS = 5
FAIL_WINDOW_SEC = 300
_fails: dict[str, list[float]] = {}


# ---------------------------------------------------------------- 纯逻辑（可单测）
def evaluate_access(direct_ip: str, headers: dict) -> dict:
    """
    纯函数：根据客户端 IP 和请求头，判断是否需要密码。

    返回 {"needs_password": bool, "ip": 有效客户端IP, "reason": 中文说明, "proxied": bool}
    """
    h = {str(k).lower(): str(v) for k, v in (headers or {}).items()}

    proxied = any(k in h for k in PROXY_HEADERS)

    # 取转发头里的真实来源（多个代理会串成 "a, b, c"，取最后一个）
    fwd = ""
    for key in ("cf-connecting-ip", "x-real-ip", "x-forwarded-for"):
        v = h.get(key, "").strip()
        if v:
            fwd = v.split(",")[-1].strip()
            break

    effective_ip = fwd or (direct_ip or "")

    if proxied:
        return {
            "needs_password": True,
            "ip": effective_ip,
            "reason": "检测到代理/穿透转发头 → 视为公网访问",
            "proxied": True,
        }

    if not (direct_ip or "").strip():
        return {
            "needs_password": False,
            "ip": "",
            "reason": "未取得客户端 IP（本机运行）→ 视为内部访问",
            "proxied": False,
        }

    try:
        addr = ipaddress.ip_address(direct_ip.strip())
    except ValueError:
        # 拿到的不是合法 IP（测试框架如 Starlette TestClient 会给 "testclient"
        # 这类占位值）。真实浏览器访问时一定是合法 IP，所以这里按"无法判断"处理。
        # 注意：伪造请求头想绕过密码的路径已经在上面被 proxied 分支拦住了。
        return {
            "needs_password": False,
            "ip": "",
            "reason": f"客户端 IP 不是合法地址（{direct_ip.strip()[:32]}）→ 按内部访问处理",
            "proxied": False,
        }

    if addr.is_private:
        return {
            "needs_password": False,
            "ip": direct_ip,
            "reason": f"局域网直连（{direct_ip}）→ 免密码",
            "proxied": False,
        }

    return {
        "needs_password": True,
        "ip": direct_ip,
        "reason": f"公网直连（{direct_ip}）→ 需要密码",
        "proxied": False,
    }


# ---------------------------------------------------------------- 读取真实请求信息
def _request_meta() -> tuple[str, dict]:
    """从 Streamlit 上下文里取客户端 IP 和请求头；取不到就返回空。"""
    ip, headers = "", {}
    try:
        ctx = st.context
    except Exception:
        return ip, headers

    try:
        ip = ctx.ip_address or ""
    except Exception:
        ip = ""

    try:
        raw = ctx.headers
        try:
            headers = dict(raw.to_dict())
        except Exception:
            headers = dict(raw)
    except Exception:
        headers = {}

    return str(ip), {str(k).lower(): str(v) for k, v in headers.items()}


def access_info() -> dict:
    """
    当前这次访问的判定结果。

    两个调试用环境变量（方便你在本机验证登录框，而不用真去搞穿透）：
        PHOTO_FORCE_PASSWORD=1  强制要求密码
        PHOTO_FORCE_LAN=1       强制免密码
    """
    import os

    if os.environ.get("PHOTO_FORCE_PASSWORD") == "1":
        return {
            "needs_password": True,
            "ip": "强制测试模式",
            "reason": "环境变量 PHOTO_FORCE_PASSWORD=1 强制要求密码",
            "proxied": False,
        }
    if os.environ.get("PHOTO_FORCE_LAN") == "1":
        return {
            "needs_password": False,
            "ip": "",
            "reason": "环境变量 PHOTO_FORCE_LAN=1 强制免密码",
            "proxied": False,
        }

    ip, headers = _request_meta()
    return evaluate_access(ip, headers)


# ---------------------------------------------------------------- 密码
def get_password() -> str:
    return config.get_app_password()


# ---------------------------------------------------------------- 暴力尝试限制
def _recent_fails(ip: str) -> int:
    now = time.time()
    lst = [t for t in _fails.get(ip, []) if now - t < FAIL_WINDOW_SEC]
    _fails[ip] = lst
    return len(lst)


def _record_fail(ip: str) -> None:
    _fails.setdefault(ip, []).append(time.time())


def reset_fails(ip: str) -> None:
    _fails.pop(ip, None)


# ---------------------------------------------------------------- 门禁 UI
def login_gate(access: dict) -> None:
    """
    在 app 最开头调用。需要密码且未登录时，只渲染登录框并 st.stop()。
    """
    if not access["needs_password"]:
        return
    if st.session_state.get("_authed"):
        return

    ip = access["ip"] or "未知来源"

    st.title("🔒 照片选片辅助系统")
    st.caption(f"公网访问已开启密码保护 · 来源 {ip}")
    st.info(
        "局域网内直接访问（同一 WiFi 打开电脑 IP）是**免密码**的；"
        "通过公网/穿透访问才需要密码。"
    )

    if _recent_fails(ip) >= MAX_FAILS:
        st.error(f"密码错误次数过多，请 {FAIL_WINDOW_SEC // 60} 分钟后再试。")
        st.stop()

    with st.form("login_form", clear_on_submit=False):
        pwd = st.text_input("访问密码", type="password", placeholder="请输入密码后回车")
        submitted = st.form_submit_button("进入系统", use_container_width=True)

    if submitted:
        if hmac.compare_digest(pwd.strip(), get_password()):
            reset_fails(ip)
            st.session_state["_authed"] = True
            st.rerun()
        else:
            _record_fail(ip)
            left = MAX_FAILS - _recent_fails(ip)
            st.error(f"密码错误，还可以尝试 {max(left, 0)} 次。")

    st.stop()


def logout_button() -> None:
    """在侧边栏放一个退出登录按钮（仅公网访问且有密码时显示）。"""
    if st.session_state.get("_authed"):
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state["_authed"] = False
            st.rerun()
