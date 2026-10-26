"""
tools/verify_login.py —— 无头验证「公网密码门禁」界面

验证三件事：
  1. 强制密码模式下：只显示登录框，不显示上传框（未登录进不了系统）
  2. 输入正确密码后：进入系统，上传框出现
  3. 输入错误密码：提示错误，仍然停在登录框

用环境变量 PHOTO_FORCE_PASSWORD=1 在本机模拟"公网访问"，不用真去搞穿透。

用法：python tools/verify_login.py
"""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["PHOTO_FORCE_PASSWORD"] = "1"

from streamlit.testing.v1 import AppTest  # noqa: E402

import config  # noqa: E402


def new_app() -> AppTest:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    at.run()
    return at


def main() -> int:
    password = config.get_app_password()
    print(f"测试密码: {password}\n")

    # ---------- 1. 未登录：只有登录框 ----------
    at = new_app()
    if at.exception:
        print("[X] 渲染异常:", [e.value for e in at.exception])
        return 1
    assert len(at.text_input) >= 1, "未登录时应该有密码输入框"
    assert len(at.get("file_uploader")) == 0, "未登录时不应该出现上传框！"
    titles = " ".join(t.value for t in at.title)
    assert "🔒" in titles, "未登录时应显示带锁的标题"
    print("[OK] 未登录：只显示登录框，上传功能不可见")

    # ---------- 2. 错误密码 ----------
    at.text_input[0].set_value("wrong-password-xxx")
    at.button[0].click()
    at.run()
    if at.exception:
        print("[X] 错误密码时渲染异常:", [e.value for e in at.exception])
        return 1
    assert len(at.get("file_uploader")) == 0, "错误密码不应该进入系统！"
    errors = " ".join(e.value for e in at.error)
    assert "密码错误" in errors, f"应该提示密码错误，实际: {errors}"
    print("[OK] 错误密码：被拒绝，仍停在登录框")

    # ---------- 3. 正确密码 ----------
    at.text_input[0].set_value(password)
    at.button[0].click()
    at.run()
    if at.exception:
        print("[X] 正确密码后渲染异常:", [e.value for e in at.exception])
        return 1
    assert len(at.get("file_uploader")) == 1, "正确密码后应该进入系统（出现上传框）"
    print("[OK] 正确密码：进入系统，上传功能出现")

    # ---------- 4. 局域网模式不应有密码框 ----------
    os.environ.pop("PHOTO_FORCE_PASSWORD", None)
    at2 = new_app()
    assert len(at2.get("file_uploader")) == 1, "局域网模式下应直接可用"
    assert len(at2.text_input) == 0, "局域网模式不应该有密码框"
    print("[OK] 局域网模式：无需密码，直接可用")

    print("\n✅ 密码门禁验证通过")
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
