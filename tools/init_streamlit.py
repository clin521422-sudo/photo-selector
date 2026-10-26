"""
tools/init_streamlit.py —— 启动前的小初始化

作用：确保 Streamlit 的 credentials 文件存在，从而跳过首次运行时的
      "Welcome to Streamlit! Email:" 提示（那个提示会让人以为程序卡住了）。

Streamlit 自己也会写这个文件，内容就是：
    [general]
    email = ""
不存在或为空时才写，已存在则不动。写不进去也不报错，只是首次运行会提示一次。
"""

from __future__ import annotations

import os
import pathlib


def main() -> int:
    home = pathlib.Path(os.path.expanduser("~"))
    conf_dir = home / ".streamlit"
    cred = conf_dir / "credentials.toml"

    try:
        conf_dir.mkdir(parents=True, exist_ok=True)
        if not cred.exists() or cred.stat().st_size == 0:
            cred.write_text('[general]\nemail = ""\n', encoding="utf-8")
            print(f"[init] 已写入 Streamlit 凭据文件: {cred}")
        else:
            print(f"[init] Streamlit 凭据文件已存在: {cred}")
        return 0
    except Exception as e:  # 写不了也不阻断启动
        print(f"[init] 警告：无法写入 {cred}（{type(e).__name__}: {e}）")
        print("[init] 首次运行若提示输入 Email，直接按回车跳过即可。")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
