"""
test_auth.py —— 访问控制逻辑测试（纯函数，不需要浏览器）

验收标准：
  1. 局域网私网 IP 直连 → 免密码
  2. 出现任何代理/穿透转发头 → 必须密码（即使伪造私网 IP 也绕不过）
  3. 公网 IP 直连 → 必须密码
  4. 拿不到 IP（本机/测试环境）→ 免密码
  5. 密码读取：环境变量 > secret.txt > 默认值
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import ROOT  # noqa: E402

import auth  # noqa: E402
import config  # noqa: E402


def run():
    # ---------- 1. 局域网直连：全部免密码 ----------
    lan_cases = [
        "192.168.1.23",
        "192.168.1.23",
        "172.20.5.6",
        "127.0.0.1",
        "::1",
    ]
    for ip in lan_cases:
        r = auth.evaluate_access(ip, {})
        assert r["needs_password"] is False, f"局域网 {ip} 应该免密码，实际要求密码"
        assert r["proxied"] is False
    print(f"  [OK] 局域网直连免密码: {', '.join(lan_cases)}")

    # ---------- 2. 公网直连：必须密码 ----------
    for ip in ("1.1.1.1", "8.8.8.8", "120.229.33.7"):
        r = auth.evaluate_access(ip, {})
        assert r["needs_password"] is True, f"公网 {ip} 必须要密码"
    print("  [OK] 公网直连需要密码")

    # ---------- 3. 穿透/代理：只要出现转发头就要密码 ----------
    tunnel_cases = [
        {"x-forwarded-for": "1.1.1.1"},
        {"x-real-ip": "120.1.2.3"},
        {"cf-connecting-ip": "1.2.3.4"},
        {"forwarded": "for=1.2.3.4"},
    ]
    for h in tunnel_cases:
        r = auth.evaluate_access("127.0.0.1", h)
        assert r["needs_password"] is True, f"转发头 {h} 应该要求密码"
        assert r["proxied"] is True
    print("  [OK] 穿透访问（有转发头）需要密码")

    # ---------- 4. 关键安全点：伪造私网 IP 的转发头也绕不过 ----------
    r = auth.evaluate_access("127.0.0.1", {"x-forwarded-for": "192.168.1.99"})
    assert r["needs_password"] is True, "伪造私网 X-Forwarded-For 不能绕过密码！"
    print("  [OK] 伪造私网 X-Forwarded-For 绕不过密码（安全）")

    # ---------- 5. 无 IP（本机/测试环境）：免密码 ----------
    r = auth.evaluate_access("", {})
    assert r["needs_password"] is False
    assert r["ip"] == ""
    print("  [OK] 无客户端 IP 时按本机处理，免密码")

    # ---------- 5b. IP 不是合法地址（测试框架占位值）：免密码，但伪造头仍要密码 ----------
    r = auth.evaluate_access("testclient", {})
    assert r["needs_password"] is False, "非法 IP 占位值应按内部访问处理"
    r = auth.evaluate_access("testclient", {"x-forwarded-for": "8.8.8.8"})
    assert r["needs_password"] is True, "非法 IP + 转发头 仍然必须密码"
    print("  [OK] IP 无法解析时按内部处理（有转发头则仍要密码）")

    # ---------- 6. 密码读取优先级 ----------
    import os

    os.environ.pop("PHOTO_APP_PASSWORD", None)
    pwd_file = config.APP_PASSWORD_SECRET_FILE
    backup = pwd_file.read_text(encoding="utf-8") if pwd_file.exists() else None
    try:
        # 关键：secret.txt 里带注释/空行时，也要能正确取出密码（不能把注释当密码）
        pwd_file.write_text(
            "# 这是注释\n\nphoto-real-pwd\n# 尾部注释\n", encoding="utf-8"
        )
        assert config.get_app_password() == "photo-real-pwd", "应跳过注释行取出密码"

        os.environ["PHOTO_APP_PASSWORD"] = "env-pwd"
        assert config.get_app_password() == "env-pwd", "环境变量优先级应最高"

        os.environ.pop("PHOTO_APP_PASSWORD")
        pwd_file.unlink()
        assert config.get_app_password() == config.APP_PASSWORD_DEFAULT, "应回退到默认值"
    finally:
        os.environ.pop("PHOTO_APP_PASSWORD", None)
        if backup is not None:
            pwd_file.write_text(backup, encoding="utf-8")
        elif pwd_file.exists():
            pwd_file.unlink()
    print("  [OK] 密码优先级：环境变量 > secret.txt > 默认值")

    # ---------- 7. 暴力尝试限制 ----------
    auth.reset_fails("9.9.9.9")
    for _ in range(auth.MAX_FAILS):
        assert auth._recent_fails("9.9.9.9") < auth.MAX_FAILS
        auth._record_fail("9.9.9.9")
    assert auth._recent_fails("9.9.9.9") == auth.MAX_FAILS, "失败计数应达到上限"
    auth.reset_fails("9.9.9.9")
    assert auth._recent_fails("9.9.9.9") == 0, "reset 后应清零"
    print(f"  [OK] 暴力尝试限制：{auth.MAX_FAILS} 次 / {auth.FAIL_WINDOW_SEC // 60} 分钟")

    print("✅ auth 模块测试通过")


if __name__ == "__main__":
    run()
