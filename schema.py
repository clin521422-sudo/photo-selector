"""
schema.py —— 全组共用的接口契约（禁止修改）

所有分析模块都必须用 make_result() 构造返回值，且只能包含以下五个键：
    module / score / label / passed / details
"""

from __future__ import annotations


def make_result(
    module: str,
    score: float,
    label: str,
    passed: bool,
    details: dict | None = None,
) -> dict:
    """构造统一的模块返回值。"""
    assert isinstance(module, str) and module, "module 必须是非空字符串"
    assert isinstance(score, (int, float)), "score 必须是数字"
    assert isinstance(label, str) and label, "label 必须是非空字符串"
    assert isinstance(passed, bool), "passed 必须是 bool"
    assert details is None or isinstance(details, dict), "details 必须是 dict 或 None"

    return {
        "module": module,
        "score": float(score),
        "label": label,
        "passed": passed,
        "details": details or {},
    }


RESULT_KEYS = {"module", "score", "label", "passed", "details"}
