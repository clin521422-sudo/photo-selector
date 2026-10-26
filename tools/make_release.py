"""
tools/make_release.py —— 打发布包

生成一个可以**直接拷给别人**的 zip：
    photo-selector-YYYYMMDD.zip
解压后：双击 `1-安装环境.bat`（自动建 venv + 装依赖 + 跑测试）→ 双击 `启动.bat` 就能用。

包里包含：
    ✅ 全部源码、bat、文档、模型（12 MB）、样图
包里排除：
    ❌ .venv/（400 MB，且带本机绝对路径，拷过去必然坏）
    ❌ received/ output/ tools/bin/ __pycache__/ .tmp/（运行时产物 / 个人照片 / 大二进制）
    ❌ secret.txt（你的真实密码，不打包；改用一个默认密码模板）

用法：
    python tools/make_release.py              # 生成到 dist/
    python tools/make_release.py --list       # 只列出会打包哪些文件
    python tools/make_release.py -o <目录>    # 指定输出目录
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

# 整个目录跳过
EXCLUDE_DIRS = {
    ".venv", "venv", "__pycache__", ".tmp", ".git", ".idea", ".vscode",
    "received", "output", "dist", "runs", "data",
    "datasets",       # 训练数据集（含你的照片和标注，绝不外发）
    ".toolconfig",    # 标注工具的本地配置缓存（anylabeling 自动生成）
    str(pathlib.Path("tools") / "bin"),  # cloudflared 53MB，让用户自己下次
}

# 额外安全网：这些路径前缀一旦混进打包列表就报错（防止上面写错名字泄漏数据）
FORBIDDEN_PREFIXES = ("datasets/", "received/", ".toolconfig/", "runs/", "output/")

# 文件名模式跳过
EXCLUDE_SUFFIX = {".pyc", ".pyo", ".log", ".part", ".zip"}
EXCLUDE_NAMES = {"secret.txt", ".index.json", "streamlit_demo.log", "推送到GitHub.bat"}

# 包里额外写入的文件（不来自工作区）
EXTRA_FILES = {
    "secret.txt": (
        "# 公网访问密码（一行一个，注释行会被跳过）\n"
        "# 局域网内访问不需要密码；通过内网穿透/公网访问需要。\n"
        "changeme\n"
    ),
}


def should_skip(path: pathlib.Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    for d in EXCLUDE_DIRS:
        d_parts = pathlib.Path(d).parts
        if parts[: len(d_parts)] == d_parts:
            return True
    if path.name in EXCLUDE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIX:
        return True
    return False


def collect() -> list[pathlib.Path]:
    files = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        if should_skip(p):
            continue
        files.append(p)
    return files


def human(n: int) -> str:
    return f"{n / 1024 / 1024:.1f} MB"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(DIST), help="输出目录")
    ap.add_argument("--list", action="store_true", help="只列出文件，不打包")
    args = ap.parse_args()

    files = collect()
    # 安全网：绝不能把个人数据/隐私路径打进发布包
    leaked = [p for p in files
              if p.relative_to(ROOT).as_posix().startswith(FORBIDDEN_PREFIXES)]
    if leaked:
        print("[X] 打包列表里出现了不该外发的路径，已中止：")
        for p in leaked[:10]:
            print(f"    {p.relative_to(ROOT)}")
        return 2

    total = sum(p.stat().st_size for p in files)

    print(f"将打包 {len(files)} 个文件，约 {human(total)}（未压缩）")
    print("-" * 66)
    for p in files:
        rel = p.relative_to(ROOT)
        print(f"  {str(rel):<48}{human(p.stat().st_size):>10}")

    for name, content in EXTRA_FILES.items():
        print(f"  {name:<48}{'(generated)':>10}")

    if args.list:
        return 0

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d")
    zip_path = out_dir / f"photo-selector-{stamp}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in files:
            zf.write(p, p.relative_to(ROOT))
        for name, content in EXTRA_FILES.items():
            zf.writestr(name, content)

    size = zip_path.stat().st_size
    print("-" * 66)
    print(f"[OK] 已生成: {zip_path}")
    print(f"     文件数 {len(files) + len(EXTRA_FILES)}，压缩后 {human(size)}")
    print()
    print("发给别人的说明（可以直接复制）：")
    print("  1) 解压到任意目录（路径别带中文也行）")
    print("  2) 双击 1-安装环境.bat  （自动装环境 + 跑测试，约 2-3 分钟）")
    print("  3) 双击 启动.bat        （浏览器自动打开界面）")
    print()
    print("  说明：包里不含 .venv（虚拟环境要本机重建），不含你上传的照片。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
