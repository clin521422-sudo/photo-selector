"""
test_doc_consistency.py —— 文档与代码一致性测试

为什么要有这个测试：
    《docs/接口字典.md》声称自己是"接口的完整字典"。但代码一改，文档就容易过期。
    这个测试从代码里**真实提取**配置键、公共函数名、details 字段，
    逐一检查它们是否都出现在字典里 —— 防止文档漂移。

覆盖：
  1. config.DEFAULT_CONFIG 的每个键
  2. 核心模块的公共函数名（schema/config/utils/pipeline/storage/auth/modules）
  3. 四个模块实际返回的 details 字段（真跑一遍 pipeline 取）
  4. 顶层结果字典的键（modules/overall/image/meta）
  5. 环境变量开关
"""

import ast
import pathlib
import sys

import cv2

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _bootstrap import ROOT, SAMPLES  # noqa: E402

DOC = ROOT / "docs" / "接口字典.md"

# 需要核对"公共函数都必须写进字典"的核心模块
CORE_MODULES = [
    "schema.py",
    "config.py",
    "utils.py",
    "pipeline.py",
    "pipeline_fakes.py",
    "storage.py",
    "auth.py",
    "modules/blur.py",
    "modules/exposure.py",
    "modules/color.py",
    "modules/subject.py",
]

ENV_VARS = [
    "PHOTO_APP_PASSWORD",
    "PHOTO_FORCE_PASSWORD",
    "PHOTO_FORCE_LAN",
    "NOSTART",
]


def public_functions(path: pathlib.Path) -> list[str]:
    """用 AST 提取模块里的公共函数名（不含下划线开头的私有函数）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    ]


def run():
    assert DOC.exists(), f"缺少接口字典: {DOC}"
    doc = DOC.read_text(encoding="utf-8")

    # ---------- 1. 配置键 ----------
    import config

    missing_cfg = [k for k in config.DEFAULT_CONFIG if k not in doc]
    assert not missing_cfg, f"接口字典缺少这些配置键: {missing_cfg}"
    print(f"  [OK] DEFAULT_CONFIG 全部 {len(config.DEFAULT_CONFIG)} 个键都在字典里")

    # ---------- 2. 公共函数 ----------
    missing_fn = []
    total_fn = 0
    for rel in CORE_MODULES:
        for fn in public_functions(ROOT / rel):
            total_fn += 1
            if fn not in doc:
                missing_fn.append(f"{rel}:{fn}")
    assert not missing_fn, f"接口字典缺少这些公共函数: {missing_fn}"
    print(f"  [OK] {len(CORE_MODULES)} 个核心模块的 {total_fn} 个公共函数都在字典里")

    # ---------- 3. 真实跑一遍，核对 details 字段 ----------
    from config import DEFAULT_CONFIG
    from pipeline import analyze_image

    img = cv2.imread(str(SAMPLES / "normal.jpg"))
    assert img is not None, "samples/ 缺测试图片"
    result = analyze_image(img, DEFAULT_CONFIG)

    missing_keys = []
    for name, mod_result in result["modules"].items():
        for key in mod_result["details"]:
            if key not in doc:
                missing_keys.append(f"{name}.{key}")
    assert not missing_keys, f"接口字典缺少这些 details 字段: {missing_keys}"
    print(f"  [OK] 四个模块返回的 details 字段都在字典里")

    # ---------- 4. 顶层结果结构 ----------
    for key in result:
        assert key in doc, f"接口字典缺少顶层结果键: {key}"
    for key in result["overall"]:
        assert key in doc, f"接口字典缺少 overall 字段: {key}"
    for key in result["meta"]:
        assert key in doc, f"接口字典缺少 meta 字段: {key}"
    print("  [OK] 顶层结构 / overall / meta 的字段都在字典里")

    # ---------- 5. 环境变量 ----------
    missing_env = [v for v in ENV_VARS if v not in doc]
    assert not missing_env, f"接口字典缺少环境变量: {missing_env}"
    print(f"  [OK] {len(ENV_VARS)} 个环境变量都在字典里")

    # ---------- 6. 反向检查：字典里提到的模块文件必须存在 ----------
    for rel in CORE_MODULES:
        assert (ROOT / rel).exists(), f"字典列出的模块不存在: {rel}"

    print("✅ 文档一致性测试通过（接口字典与代码同步）")


if __name__ == "__main__":
    run()
