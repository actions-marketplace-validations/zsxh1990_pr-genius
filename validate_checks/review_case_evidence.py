"""Check 9: review-case evidence gate (issue #41, 2026-10-01).

`review-cases/*.json` 是结构化 PR 记录、没有 frontmatter, 而 check 4 的
`--enforce-evidence` 路径只走带 `rounds` 的 markdown case study —— 302 条 JSON
从来没被门看过, 于是 `--enforce-evidence` 在 0/302 证据覆盖下照样 exit 0 (假绿)。

本 check 给 JSON 记录补上与 v0.7.0 case-level 同款的证据契约, 每条必须含:

- `verified_at`: ISO-8601 时间字符串
- `evidence_urls`: 非空的 http(s) URL 列表, 指向真实 PR/issue

行为:

- 默认 / `--strict`: 查找结果进 warnings —— 存量是已声明债务 (方案 G1
  "新增记录强制带上; 存量分期补"), 只警告, 不挡 `--strict`
- `--enforce-evidence`: 查找结果进 errors → exit 1。缺失就是缺失, 门必须
  在覆盖不全时读红, 否则还是假绿
- 每次运行都打印 `evidence coverage: N/M (P%)`, 供每周补录看趋势

绝不为了凑覆盖率伪造字段 (方案 §五.2)。URL 只做形状校验
(`^https?://`), 不做存活探测 —— 本 check 不联网, 不冒充"已验证真实存在"。
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

# 与 check_rounds_schema 的 EVIDENCE_URL_RE 同一形状契约
EVIDENCE_URL_RE = re.compile(r"^https?://")

# ISO-8601 形状: 日期, 或日期+时间(可选秒/小数/时区)
_ISO_SHAPE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}"
    r"(?:[Tt ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:[Zz]|[+-]\d{2}:?\d{2})?)?$"
)


def _is_iso8601(value) -> bool:
    """True iff value is an ISO-8601 date or date-time string.

    Python 3.9 兼容: `datetime.fromisoformat` 在 3.9 不吃 'Z' 尾巴,
    先换成 '+00:00'; 无冒号偏移 '+0800' 也补上冒号。
    """
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not _ISO_SHAPE_RE.match(s):
        return False
    normalized = s.replace("Z", "+00:00").replace("z", "+00:00")
    m = re.search(r"([+-])(\d{2})(\d{2})$", normalized)
    if m:
        normalized = normalized[: m.start()] + f"{m.group(1)}{m.group(2)}:{m.group(3)}"
    try:
        datetime.fromisoformat(normalized)
        return True
    except ValueError:
        return False


def _urls_ok(value) -> bool:
    """True iff value is a non-empty list of http(s) URL strings."""
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(u, str) and EVIDENCE_URL_RE.match(u) for u in value)


def check_review_case_evidence(
    root: Path,
    warnings: list[str],
    errors: list[str],
    enforce_evidence: bool = False,
) -> dict:
    """Check 9: review-cases/*.json 必须携带 verified_at + evidence_urls.

    enforce_evidence=False → findings 进 warnings (不挡 --strict)
    enforce_evidence=True  → findings 进 errors   (exit 1)

    Returns: {"total": int, "complete": int, "coverage_pct": float | None}
    """
    print(
        "[Check 9] Review-case evidence (review-cases/*.json)"
        f" enforce_evidence={enforce_evidence}"
    )
    cases_dir = root / "review-cases"
    if not cases_dir.is_dir():
        print("   (no review-cases/ dir, skip)")
        return {"total": 0, "complete": 0, "coverage_pct": None}

    files = sorted(cases_dir.glob("*.json"))
    target = errors if enforce_evidence else warnings
    complete = 0

    for f in files:
        rel = f.relative_to(root)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            target.append(f"{rel}: [evidence-gate] unreadable JSON: {e}")
            continue
        if not isinstance(data, dict):
            target.append(f"{rel}: [evidence-gate] record must be a JSON object")
            continue

        problems: list[str] = []
        va = data.get("verified_at")
        if va is None or va == "":
            problems.append("missing `verified_at` (need ISO-8601 string)")
        elif not _is_iso8601(va):
            problems.append(f"invalid `verified_at` (need ISO-8601 string): {va!r}")

        eu = data.get("evidence_urls")
        if eu is None or eu == []:
            problems.append("missing `evidence_urls` (need non-empty http(s) URL list)")
        elif not _urls_ok(eu):
            problems.append(f"invalid `evidence_urls` (need http(s) URL list): {eu!r}")

        if problems:
            for p in problems:
                target.append(f"{rel}: [evidence-gate] {p}")
        else:
            complete += 1

    total = len(files)
    pct = (100.0 * complete / total) if total else 100.0
    print(
        f"   evidence coverage: {complete}/{total} ({pct:.1f}%) "
        "records have verified_at + evidence_urls"
    )
    return {"total": total, "complete": complete, "coverage_pct": pct}
