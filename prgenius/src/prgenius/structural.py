"""PR 结构性检查 (issue #45) — 纯静态启发式，绝不执行 PR 中的代码。

覆盖两条结构性反模式（表层关键词命中不了的缺陷形状）：

- fabricated-evidence-in-claim：代码块里贴出的输出与命令的必然输出不一致
  - 强启发式 print_output_mismatch：输出带 ``SUCCESS:`` 类前缀，但命令只是
    ``print(某表达式)`` 且命令文本里不含该标记 → 必然输出不可能带这个前缀
    （severity=critical → 阻塞）
  - 弱启发式 output_without_command：贴了输出样式行但全篇没有可核对的命令
    （severity=high, 需人工复核 → 列清单不阻塞）
- state-derived-from-nonexistent-source：引用 ``data/*.jsonl`` 或 frontmatter
  字段名驱动状态，却不给命中数证据（severity=high → 列清单不阻塞）

误报纪律（历史教训：泛词误报导致 coach 一律 high_risk）：
- 只匹配高精度形状，不加 error/fail/update 这类泛词
- 输出样式行只认 ``SUCCESS:`` / ``PASS:`` 这类带冒号的"手写汇报"格式，
  不认 pytest 的 ``PASSED``/``FAILED``、jest 的 ``PASS src/...``、go 的 ``ok``
- 结构性反模式的 trigger_keywords 弱命中一律降级（见 evaluator），
  只有结构证据才能升到 critical

所有判定都是文本形状匹配：不跑命令、不装依赖、不做 LLM 调用。
"""

from __future__ import annotations

import re
from typing import List, Optional

# 反模式 key（与 anti-patterns/*.md 的 key 字段一致）
FABRICATED_KEY = "fabricated-evidence-in-claim"
STATE_KEY = "state-derived-from-nonexistent-source"

STRUCTURAL_KEYS = frozenset({FABRICATED_KEY, STATE_KEY})

# 严重程度排序（合并命中时取更高）
SEV_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


# ============================================================
# 代码块 / 命令 / 输出样式行识别
# ============================================================

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)

# shell 提示符行
_PROMPT_RE = re.compile(r"^\s*[$#]\s+\S")

# 常见 CLI 首 token → 判定为命令行
_COMMAND_FIRST_TOKENS = frozenset({
    "python", "python3", "pip", "pip3", "git", "npm", "npx", "node", "pytest",
    "bash", "sh", "zsh", "curl", "wget", "grep", "rg", "cat", "ls", "wc",
    "echo", "make", "cargo", "go", "docker", "sw_vers", "uname", "which",
    "env", "jq", "sed", "awk", "head", "tail", "sort", "uniq", "find",
    "poetry", "uv", "ruff", "tox", "bundle", "ruby", "yarn", "pnpm",
    "misakanet_search", "misakanet_get_lesson",
})

# 输出样式行（"手写汇报"格式）：带冒号的 claim 标记 / 括号标记 / ✓ 前缀。
# 刻意不匹配 pytest 的 PASSED/FAILED、jest 的 "PASS src/..."、go 的 "ok pkg"
# —— 那些是真实工具输出，按输出粘贴属正常 PR。
_CLAIM_MARKER_RE = re.compile(
    r"^\s*(?:"
    r"(SUCCESS|PASS|OK|DONE)\s*:"
    r"|\[(SUCCESS|PASS|OK|DONE)\]"
    r"|[✓✔]\s*(SUCCESS|PASS|OK|DONE)\b"
    r")",
    re.IGNORECASE,
)

# print(表达式) — 用于检测"命令只是 print(某函数返回值)"。
# 不锚定行尾：命令可能是 `python3 -c "... print(f())"`，后面还有引号。
_PRINT_CALL_RE = re.compile(r"\bprint\s*\((.*)\)")

# 字符串字面量（print 的参数里出现引号 → 前缀可能来自字面量，不判不一致）
_QUOTED_RE = re.compile(r"""["']""")


def parse_fenced_blocks(text: str) -> List[str]:
    """提取 markdown 围栏代码块内容（不含围栏行）。"""
    return [m.group(1) for m in _FENCE_RE.finditer(text or "")]


def looks_like_command(line: str) -> bool:
    """该行是否像一条可复核的命令（而非输出/散文）。"""
    s = line.strip()
    if not s:
        return False
    if _PROMPT_RE.match(s):
        return True
    # 跳过 env 前缀: FOO=bar cmd ...
    tokens = s.split()
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return False
    first = tokens[0].split("/")[-1]
    return first in _COMMAND_FIRST_TOKENS


def claim_marker(line: str) -> Optional[str]:
    """输出样式行 → 标记词 (SUCCESS/PASS/OK/DONE)，否则 None。"""
    m = _CLAIM_MARKER_RE.match(line)
    if not m:
        return None
    for g in m.groups():
        if g:
            return g.upper()
    return None


# ============================================================
# (a) fabricated-evidence-in-claim
# ============================================================

def _check_print_output_mismatch(block: str) -> Optional[dict]:
    """输出含 SUCCESS: 类前缀，但命令只是 print(某表达式) → 必然输出不符。

    只在同一个代码块里比对（同一块 = 自称同一段日志）。
    """
    lines = block.splitlines()
    command_lines = [ln for ln in lines if looks_like_command(ln)]
    if not command_lines:
        return None

    for ln in lines:
        marker = claim_marker(ln)
        if not marker:
            continue
        # 命令文本里出现过该标记（如 print("SUCCESS:", ...)）→ 前缀可核对，跳过
        if any(marker.lower() in cmd.lower() for cmd in command_lines):
            continue
        for cmd in command_lines:
            pm = _PRINT_CALL_RE.search(cmd.strip())
            if not pm:
                continue
            printed = pm.group(1)
            # print 了字符串字面量 → 前缀可能来自字面量；只有 print(表达式) 才是必然输出
            if _QUOTED_RE.search(printed):
                continue
            return {
                "key": FABRICATED_KEY,
                "check": "print_output_mismatch",
                "severity": "critical",
                "needs_human_review": True,
                "description": (
                    f"输出含 `{marker}:` 前缀，但命令只是 `print({printed.strip()})` — "
                    f"print(表达式) 的必然输出不含该前缀，贴出的输出与命令对不上（需人工复核）"
                ),
                "fix_action": (
                    "1) 逐条复跑块内命令，把终端输出原样粘贴，不允许凭记忆写输出；"
                    "2) 若输出前缀是手写汇报格式，说明它不是原始日志，撤回或改贴真实输出"
                ),
            }
    return None


def _check_output_without_command(body: str, block: str) -> Optional[dict]:
    """贴了输出样式行，但全篇没有可核对的命令 → 需人工复核。"""
    lines = block.splitlines()
    if not any(claim_marker(ln) for ln in lines):
        return None
    if any(looks_like_command(ln) for ln in lines):
        return None
    # 正文别处有命令 → 输出块可以人工对照，不算缺陷
    if any(looks_like_command(ln) for ln in (body or "").splitlines()):
        return None
    return {
        "key": FABRICATED_KEY,
        "check": "output_without_command",
        "severity": "high",
        "needs_human_review": True,
        "description": (
            "贴了 SUCCESS:/PASS: 输出样式行，但没有可核对的命令 — "
            "输出无法被第三方复现（需人工复核）"
        ),
        "fix_action": (
            "1) 在输出前补上产生它的命令（含参数）；"
            "2) 环境信息用机器可复核命令的输出（sw_vers / python3 --version / node --version）"
        ),
    }


# ============================================================
# (b) state-derived-from-nonexistent-source
# ============================================================

# data/*.jsonl|json 路径引用
_DATA_PATH_RE = re.compile(r"(?<![\w.])data/[\w./-]+\.(?:jsonl|json)\b")

# frontmatter 字段访问: meta.get("x") / fm["x"] / meta.intake_id
_FM_FIELD_RE = re.compile(
    r"\b(?:meta|fm|frontmatter|metadata)\s*"
    r"(?:"
    r"\.\s*get\(\s*[\"']([A-Za-z0-9_]+)[\"']"
    r"|\[\s*[\"']([A-Za-z0-9_]+)[\"']\s*\]"
    r"|\.\s*([A-Za-z_][A-Za-z0-9_]*)"
    r")"
)

# 状态上下文：没有这些词就只是读元数据，不算"驱动状态"
_STATE_CTX_RE = re.compile(
    r"status|state|pending|lookup|derive|derived|convert|conversion|"
    r"状态|驱动|查询|转换",
    re.IGNORECASE,
)


def _check_data_path_reference(text: str) -> Optional[dict]:
    paths = sorted(set(_DATA_PATH_RE.findall(text or "")))
    if not paths:
        return None
    shown = ", ".join(f"`data/{p}`" if not p.startswith("data/") else f"`{p}`"
                      for p in paths[:3])
    return {
        "key": STATE_KEY,
        "check": "data_path_reference",
        "severity": "high",
        "needs_human_review": False,
        "description": (
            f"引用 {shown} 作为状态来源 — 先给命中数证据"
        ),
        "fix_action": (
            "1) `git cat-file -e <branch>:<path>` 验证文件在目标分支真实存在；"
            "2) 把命中数写进 PR 描述（`wc -l` / `grep -c`）；"
            "3) 命中为 0 的文件不能驱动状态；4) 把「查不到」与「尚未发生」分成两个可区分的返回"
        ),
    }


def _check_frontmatter_field_state(text: str) -> Optional[dict]:
    if not _STATE_CTX_RE.search(text or ""):
        return None
    fields: List[str] = []
    for m in _FM_FIELD_RE.finditer(text or ""):
        for g in m.groups():
            if g and g.lower() not in ("get", "pop", "items", "keys", "values"):
                fields.append(g)
                break
    fields = sorted(set(fields))
    if not fields:
        return None
    shown = ", ".join(f"`{f}`" for f in fields[:5])
    return {
        "key": STATE_KEY,
        "check": "frontmatter_field_state",
        "severity": "high",
        "needs_human_review": False,
        "description": (
            f"引用 frontmatter 字段 {shown} 作为状态来源 — 先给命中数证据"
        ),
        "fix_action": (
            "1) `grep -rh '^<field>:' <语料目录>/ | wc -l` 统计字段全量命中数，写进 PR 描述；"
            "2) 命中为 0 的字段不能驱动状态（规格写了 ≠ 语料里有）；"
            "3) 优先复用仓里已有的 lookup helper，别另写匹配器"
        ),
    }


# ============================================================
# 入口
# ============================================================

_SOURCE_PR = {
    FABRICATED_KEY: "Ikalus1988/MisakaNet#1819 (comment 5925609094)",
    STATE_KEY: "Ikalus1988/MisakaNet PR #2494 (comment 5927372088)",
}


def check_structural_patterns(title: str, text: str) -> List[dict]:
    """对 PR 标题 + 正文做结构性检查，返回命中列表。

    纯静态：只做正则/形状匹配，绝不执行代码块内容。
    每个命中至少包含: key, check, severity, needs_human_review,
    description, fix_action, match_type='structural'。
    """
    body = text or ""
    full = f"{title or ''}\n{body}"
    findings: List[dict] = []

    for block in parse_fenced_blocks(body):
        for fn in (_check_print_output_mismatch, lambda b: _check_output_without_command(body, b)):
            hit = fn(block)
            if hit:
                findings.append(hit)

    for fn in (_check_data_path_reference, _check_frontmatter_field_state):
        hit = fn(full)
        if hit:
            findings.append(hit)

    for f in findings:
        f.setdefault("match_type", "structural")
        f.setdefault("match_mode", "structural")
        f.setdefault("symptom", "")
        f.setdefault("source_pr", _SOURCE_PR.get(f["key"], ""))
        f.setdefault("source_url", "")
        f.setdefault("keyword", "")
        f.setdefault("matched_keyword", "")
    return findings


def _higher_severity(a: str, b: str) -> str:
    return a if SEV_RANK.get(a, 0) >= SEV_RANK.get(b, 0) else b


def merge_structural_matches(keyword_hits: List[dict], structural_hits: List[dict]) -> List[dict]:
    """合并关键词命中与结构命中（按 key 去重）。

    severity 规则（误报纪律）：
    - 只有关键词命中 → 保留关键词 severity（结构性反模式会在信号层降级为 high）
    - 有结构命中 → severity 以结构证据为准（弱启发式 high、强启发式 critical），
      不与关键词的声明 severity 取 max —— SUCCESS: 这类泛词不能把弱启发式顶成 critical
    """
    merged: List[dict] = []
    by_key: dict = {}

    for hit in list(keyword_hits) + list(structural_hits):
        key = hit.get("key", "")
        if key in by_key:
            entry = by_key[key]
            if hit.get("match_type") == "structural":
                if entry.get("structural_confirmed"):
                    entry["severity"] = _higher_severity(
                        entry.get("severity", "medium"), hit.get("severity", "medium")
                    )
                else:
                    # 结构证据覆盖关键词命中的声明 severity
                    entry["severity"] = hit.get("severity", "medium")
                entry["structural_confirmed"] = True
                entry["match_type"] = "structural"
                # 结构命中的描述/修复更具体，覆盖关键词命中的
                entry["description"] = hit.get("description") or entry.get("description", "")
                entry["fix_action"] = hit.get("fix_action") or entry.get("fix_action", "")
                entry["check"] = hit.get("check", entry.get("check", ""))
            # 关键词命中不改变已合并条目的 severity
            entry["needs_human_review"] = bool(entry.get("needs_human_review")) or bool(
                hit.get("needs_human_review")
            )
            continue
        entry = dict(hit)
        entry.setdefault("severity", "medium")
        if entry.get("match_type") == "structural":
            entry["structural_confirmed"] = True
        by_key[key] = entry
        merged.append(entry)

    return merged
