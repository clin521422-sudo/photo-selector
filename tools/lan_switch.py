"""
tools/lan_switch.py —— 一键开关「局域网访问」（防火墙入站规则）

解决什么问题：
    Windows 默认会拦掉外部设备访问本机端口。手机连不上电脑上的 8501，
    99% 是防火墙拦了，尤其是 WiFi 被识别成"公用网络"的时候。

怎么用：
    双击 局域网访问开关.bat（会自动请求管理员权限）
    或命令行：python tools/lan_switch.py [on|off|status]

规则说明：
    - 只放行 TCP 8501（就是本项目的 Streamlit 端口），不开整个程序
    - profile=any：不管当前 WiFi 被判成"专用"还是"公用"都生效
    - 用完可以随时点"关闭"，只影响手机/其它设备访问，本机 localhost 始终可用

输出约定：只用 [OK] [X] [!] [i] 这类 ASCII 标记，不用 emoji。
    原因：这个脚本可能在不同代码页（GBK/UTF-8）的窗口里跑，
          emoji（如 U+2705）在 GBK 控制台会直接抛 UnicodeEncodeError。
"""

from __future__ import annotations

import ctypes
import socket
import subprocess
import sys

# 兜底：万一编码不是 UTF-8（比如提权后的新窗口没继承 PYTHONUTF8），
# 也不要因为个别字符编码不了就崩掉，用 ? 替换即可。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

RULE_NAME = "PhotoSelector 8501"
PORT = 8501


# ---------------------------------------------------------------- 基础工具
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _decode(b: bytes) -> str:
    for enc in ("utf-8", "mbcs", "gbk", "cp936"):
        try:
            return b.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("utf-8", "replace")


def run(cmd: list[str]) -> tuple[int, str]:
    """执行命令，返回 (退出码, 输出)。"""
    try:
        p = subprocess.run(cmd, capture_output=True, shell=False)
        return p.returncode, _decode(p.stdout) + _decode(p.stderr)
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def _needs_elevation(out: str) -> bool:
    low = out.lower()
    return ("elevation" in low) or ("access is denied" in low) or ("拒绝访问" in out)


def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def port_listening(port: int = PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except Exception:
        return False


def rule_state() -> str:
    """
    查规则状态，返回 "on" / "off" / "unknown"。

    注意：Windows 上查询防火墙规则同样需要管理员权限，
    非管理员时 netsh 会报错，这时必须返回 "unknown"，不能谎报成"未开启"。
    """
    code, out = run(["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"])
    if code != 0 or _needs_elevation(out):
        return "unknown"
    return "on" if RULE_NAME in out else "off"


def rule_exists() -> bool:
    """仅在已有管理员权限时用于确认结果（查询需要提权）。"""
    return rule_state() == "on"


def network_profile() -> str:
    """当前网络类型（公用/专用），只用于展示；查询需要管理员权限。"""
    code, out = run(["netsh", "advfirewall", "show", "currentprofile"])
    if code != 0 or _needs_elevation(out):
        return "需管理员权限才能读取"
    text = out.strip()
    for line in text.splitlines():
        if any(k in line for k in ("配置文件", "Profile", "设置", "Settings")):
            return line.strip()
    return text.splitlines()[0] if text else "未知"


def need_admin_msg() -> None:
    print("[X] 需要管理员权限。请双击 局域网访问开关.bat（会自动请求提权），")
    print("    或者用「以管理员身份运行」打开命令行再执行本脚本。")


# ---------------------------------------------------------------- 操作
def enable() -> bool:
    if not is_admin():
        need_admin_msg()
        return False

    # 先删同名旧规则，避免重复添加
    if rule_exists():
        print("[i] 检测到已有规则，先删除旧的…")
        run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME}"])

    code, out = run([
        "netsh", "advfirewall", "firewall", "add", "rule",
        f"name={RULE_NAME}",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        f"localport={PORT}",
        "profile=any",
        "enable=yes",
        f"description=Photo Selector LAN access (port {PORT})",
    ])

    if rule_exists():
        print(f"[OK] 已放行 TCP {PORT}，局域网内其它设备现在可以访问了")
        print(f"     手机访问地址: http://{get_lan_ip()}:{PORT}")
        if not port_listening():
            print("     [!] 但 8501 端口当前没有监听 —— 请先双击 启动.bat 把服务开起来")
        print("     用完想关掉：再双击本开关，选 [2]")
        return True

    print("[X] 添加规则失败，netsh 输出：")
    print(out.strip()[:800])
    print("\n可以手动执行（管理员命令行）：")
    print(f'  netsh advfirewall firewall add rule name="{RULE_NAME}" dir=in action=allow '
          f'protocol=TCP localport={PORT} profile=any enable=yes')
    return False


def disable() -> bool:
    if not is_admin():
        need_admin_msg()
        return False

    if not rule_exists():
        print("[i] 当前没有这条规则（本来就没放行）")
        return True

    code, out = run(["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME}"])
    if not rule_exists():
        print(f"[OK] 已关闭局域网访问（删除规则 {RULE_NAME}）")
        print("     本机 http://localhost:8501 仍然可以正常使用")
        return True

    print("[X] 删除失败，netsh 输出：")
    print(out.strip()[:800])
    return False


def status() -> None:
    admin = is_admin()
    state = rule_state()
    listening = port_listening()

    print("当前状态")
    print("-" * 60)
    print(f"  管理员权限 : {'[OK] 是' if admin else '[X] 否（双击 局域网访问开关.bat 会自动提权）'}")
    if state == "on":
        print("  防火墙规则 : [OK] 已开启（局域网内可访问）")
    elif state == "off":
        print("  防火墙规则 : [X] 未开启")
    else:
        print("  防火墙规则 : [!] 无法读取（查询防火墙规则需要管理员权限）")
    print(f"  {PORT} 监听  : {'[OK] 服务在运行' if listening else '[X] 服务未启动（先双击 启动.bat）'}")
    print(f"  本机局域网 : http://{get_lan_ip()}:{PORT}")
    print(f"  当前网络   : {network_profile()}")
    print("-" * 60)

    if state == "unknown":
        print("请以管理员身份运行（双击 局域网访问开关.bat），或选 [1] 直接开启。")
    elif state == "off":
        print("手机连不上？选 [1] 开启局域网访问。")
    elif not listening:
        print("规则已开启，但服务没启动 → 先双击 启动.bat。")
    else:
        print("一切正常。手机连同一 WiFi，访问上面的地址即可。")
        print("如果还是打不开，可能是 WiFi 开了「AP 隔离」（设备互相不可见），")
        print("换手机热点/电脑热点再试。")


def menu() -> int:
    while True:
        print()
        print("=" * 60)
        print(" 照片选片系统 · 局域网访问开关（端口 8501）")
        print("=" * 60)
        status()
        print()
        print("  [1] 开启局域网访问（手机可访问）")
        print("  [2] 关闭局域网访问")
        print("  [3] 刷新状态")
        print("  [0] 退出")
        print()
        try:
            choice = input("请选择 1/2/3/0: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if choice == "1":
            enable()
        elif choice == "2":
            disable()
        elif choice == "3":
            continue
        elif choice in ("0", "q", "Q"):
            return 0
        else:
            print("无效输入，请重新选择")


def main() -> int:
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "on":
            return 0 if enable() else 1
        if action == "off":
            return 0 if disable() else 1
        if action == "status":
            status()
            return 0
        print(f"未知参数 {action}，可用：on / off / status")
        return 2
    return menu()


if __name__ == "__main__":
    sys.exit(main())
