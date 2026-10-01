"""Regression tests for issue #45 — coach 结构性缺陷检查.

覆盖:
1. structural.py 纯静态启发式 (绝不执行 PR 代码)
2. 退出码约定: severity=critical 反模式 → 阻塞; severity=high → 列清单不阻塞
3. 误报回归: 本仓库 review-cases/ 的真实 PR 案例 + 正常 PR 形状不得被判 high_risk
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prgenius.cli import main
from prgenius.evaluator import analyze_pr, check_anti_patterns
from prgenius.structural import (
    FABRICATED_KEY,
    STATE_KEY,
    check_structural_patterns,
    claim_marker,
    looks_like_command,
    merge_structural_matches,
    parse_fenced_blocks,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _coach_exit(title: str, body: str, description: str = "", repo: str = "org/repo") -> int:
    return main([
        "coach", title, "--repo", repo,
        "--description", description, "--body", body,
        "--format", "json",
    ])


# MisakaNet #1819 的缺陷形状: print(某函数返回值) 的必然输出不含 SUCCESS: 前缀
FABRICATED_BODY = """## T2 verification

```bash
python3 -c "import testpkg; print(testpkg.hello())"
SUCCESS: world
```

Raw logs attached, verified on macOS.
"""

STATE_BODY = """This change derives conversion status from meta.intake_id
and the contrib_id frontmatter fields.
It reads data/contribution_queue.jsonl for pending items.
"""

NORMAL_PYTEST_BODY = """Fixes #42

Ran the suite locally:

```
$ python3 -m pytest -q
tests/test_a.py ........                                        [100%]
8 passed in 0.21s
```
"""

NORMAL_JEST_BODY = """Fixes #7

```
$ npx jest
PASS  src/foo.test.js
Tests:       3 passed, 3 total
```
"""

NORMAL_DOCS_BODY = """Fixes #3

Fix a typo in the README quickstart. No behavior change.
"""


class TestPrimitiveHelpers:
    def test_parse_fenced_blocks(self):
        blocks = parse_fenced_blocks("a\n```bash\necho hi\n```\n```\nls\n```\n")
        assert blocks == ["echo hi\n", "ls\n"]

    def test_looks_like_command(self):
        assert looks_like_command("python3 -c \"print(1)\"")
        assert looks_like_command("$ git status")
        assert looks_like_command("FOO=1 pytest -q")
        assert not looks_like_command("SUCCESS: world")
        assert not looks_like_command("just prose about output")

    def test_claim_marker_recognizes_hand_written_formats_only(self):
        assert claim_marker("SUCCESS: world") == "SUCCESS"
        assert claim_marker("  [PASS] all good") == "PASS"
        assert claim_marker("✔ DONE x") == "DONE"
        # 真实工具输出 — 不是 claim 标记
        assert claim_marker("PASSED tests/test_a.py::test_x") is None
        assert claim_marker("FAILED tests/test_b.py::test_y") is None
        assert claim_marker("PASS  src/foo.test.js") is None
        assert claim_marker("ok  	github.com/x/y	0.01s") is None
        assert claim_marker("=== 8 passed in 0.21s ===") is None


class TestPrintOutputMismatch:
    """(a) 强启发式: 输出前缀与命令必然输出不符 → critical, 需人工复核."""

    def test_fabricated_shape_is_detected(self):
        hits = check_structural_patterns("fix: verify T2", FABRICATED_BODY)
        checks = {(h["key"], h["check"], h["severity"]) for h in hits}
        assert (FABRICATED_KEY, "print_output_mismatch", "critical") in checks
        assert all(h["needs_human_review"] for h in hits if h["check"] == "print_output_mismatch")

    def test_fabricated_shape_blocks_coach(self):
        result = analyze_pr("fix: verify T2", "Raw logs attached", "org/repo", REPO_ROOT,
                            body=FABRICATED_BODY)
        assert result["tier"] == "high_risk"
        assert FABRICATED_KEY in result["anti_patterns_hit"]
        assert _coach_exit("fix: verify T2", FABRICATED_BODY, "Raw logs attached") == 1

    def test_print_with_marker_literal_is_not_flagged(self):
        body = """```bash
python3 -c "print('SUCCESS:', testpkg.hello())"
SUCCESS: world
```
"""
        hits = [h for h in check_structural_patterns("fix: verify", body)
                if h["check"] == "print_output_mismatch"]
        assert hits == []

    def test_string_literal_print_not_flagged(self):
        body = """```bash
python3 -c "print(f'SUCCESS: {x}')"
SUCCESS: 5
```
"""
        hits = [h for h in check_structural_patterns("fix: verify", body)
                if h["check"] == "print_output_mismatch"]
        assert hits == []

    def test_real_tool_output_paste_not_flagged(self):
        for body in (NORMAL_PYTEST_BODY, NORMAL_JEST_BODY):
            assert check_structural_patterns("fix: tests", body) == []


class TestOutputWithoutCommand:
    """(a) 弱启发式: 贴了输出但没有可核对的命令 → high, 需人工复核, 不阻塞."""

    def test_output_without_any_command_flagged(self):
        body = """Raw logs attached:

```text
SUCCESS: all checks passed
```
"""
        hits = [h for h in check_structural_patterns("chore: report", body)
                if h["check"] == "output_without_command"]
        assert len(hits) == 1
        assert hits[0]["severity"] == "high"
        assert hits[0]["needs_human_review"] is True

    def test_output_with_command_elsewhere_in_body_not_flagged(self):
        body = """Run `python3 -m pytest -q` first.

```text
SUCCESS: all checks passed
```
"""
        # 正文有命令行 (backtick 内联不算命令行, 但独立命令行算)
        body2 = body.replace("Run `python3 -m pytest -q` first.", "$ python3 -m pytest -q")
        assert [h for h in check_structural_patterns("chore: report", body2)
                if h["check"] == "output_without_command"] == []

    def test_weak_heuristic_does_not_block(self):
        body = """```text
SUCCESS: all checks passed
```
"""
        result = analyze_pr("chore: report", "verification", "org/repo", REPO_ROOT, body=body)
        assert result["tier"] != "high_risk"
        assert FABRICATED_KEY in result["anti_patterns_hit"]
        assert _coach_exit("chore: report", body, "verification") == 0


class TestStateDerivedChecks:
    """(b) data/*.jsonl / frontmatter 字段驱动状态 → 提示先给命中数证据."""

    def test_data_jsonl_reference_flagged(self):
        hits = [h for h in check_structural_patterns("feat: status", STATE_BODY)
                if h["check"] == "data_path_reference"]
        assert len(hits) == 1
        assert hits[0]["severity"] == "high"
        assert "命中数" in hits[0]["description"]
        assert "git cat-file -e" in hits[0]["fix_action"]

    def test_frontmatter_field_state_flagged(self):
        hits = [h for h in check_structural_patterns("feat: status", STATE_BODY)
                if h["check"] == "frontmatter_field_state"]
        assert len(hits) == 1
        assert "meta.intake_id" in hits[0]["description"] or "intake_id" in hits[0]["description"]
        assert "命中数" in hits[0]["description"]

    def test_frontmatter_fields_without_state_context_not_flagged(self):
        body = 'Docs use meta.get("title") for rendering the page header.'
        assert [h for h in check_structural_patterns("docs: meta", body)
                if h["check"] == "frontmatter_field_state"] == []

    def test_state_findings_listed_but_do_not_block(self):
        result = analyze_pr("feat: conversion status", "derive status", "org/repo", REPO_ROOT,
                            body=STATE_BODY)
        assert result["tier"] != "high_risk"
        assert STATE_KEY in result["anti_patterns_hit"]
        hints = " ".join(c["hint"] for c in result["checklist"])
        assert "命中数" in hints
        assert _coach_exit("feat: conversion status", STATE_BODY, "derive status") == 0


class TestKeywordMatchingAndDemotion:
    """trigger_keywords 对标题+正文匹配; 结构性反模式的关键词弱命中不阻塞."""

    def test_trigger_keywords_match_title_and_body(self):
        hits = check_anti_patterns(
            "fix: raw logs attached", "nothing else", "org/repo", REPO_ROOT,
            body="See description",
        )
        assert any(h["key"] == FABRICATED_KEY for h in hits)

        hits2 = check_anti_patterns(
            "fix: something", "nothing else", "org/repo", REPO_ROOT,
            body="Here is the output of the build.",
        )
        assert any(h["key"] == FABRICATED_KEY for h in hits2)

    def test_keyword_only_hit_on_structural_pattern_is_demoted(self):
        body = "Here is the output summary. Verified on macOS."
        result = analyze_pr("fix: report", "update", "org/repo", REPO_ROOT, body=body)
        assert FABRICATED_KEY in result["anti_patterns_hit"]
        neg = [s for s in result["signals"]["negative"] if s["key"] == FABRICATED_KEY][0]
        assert neg["severity"] == "high"          # 关键词弱命中不升 critical
        assert neg["match_type"] == "keyword"
        assert result["tier"] != "high_risk"
        assert _coach_exit("fix: report", body, "update") == 0

    def test_critical_non_structural_pattern_still_blocks(self):
        # ai-generated-content 是 critical 且非结构性 — 关键词命中仍应阻塞
        result = analyze_pr("fix: stuff", "generated by ai, chatgpt output",
                            "org/repo", REPO_ROOT, body="Fixes #1")
        assert "ai-generated-content" in result["anti_patterns_hit"]
        assert result["tier"] == "high_risk"
        assert _coach_exit("fix: stuff", "generated by ai, chatgpt output", "") == 1

    def test_structural_evidence_upgrades_keyword_hit(self):
        kw_hits = check_anti_patterns("fix: verify", "raw logs attached", "org/repo", REPO_ROOT)
        st_hits = check_structural_patterns("fix: verify", FABRICATED_BODY)
        merged = merge_structural_matches(kw_hits, st_hits)
        entry = [m for m in merged if m["key"] == FABRICATED_KEY][0]
        assert entry["severity"] == "critical"
        assert entry["structural_confirmed"] is True


class TestHighSeverityListsButDoesNotBlock:
    """issue #45 退出码约定: severity=high 反模式命中 → exit 0 + checklist."""

    def test_high_anti_pattern_in_checklist_with_priority_p1(self):
        result = analyze_pr("feat: status", "derive status", "org/repo", REPO_ROOT,
                            body=STATE_BODY)
        items = [c for c in result["checklist"] if c["action"] == f"fix_{STATE_KEY}"]
        assert len(items) == 1
        assert items[0]["priority"] == "P1"

    def test_critical_anti_pattern_is_p0(self):
        result = analyze_pr("fix: verify T2", "Raw logs attached", "org/repo", REPO_ROOT,
                            body=FABRICATED_BODY)
        items = [c for c in result["checklist"] if c["action"] == f"fix_{FABRICATED_KEY}"]
        assert items and items[0]["priority"] == "P0"

    def test_merge_conflict_still_blocks(self):
        # 非反模式 high 信号维持原语义
        result = analyze_pr("fix: x", "Fixes #1", "org/repo", REPO_ROOT,
                            body="Fixes #1", mergeable="CONFLICTING")
        assert result["tier"] == "high_risk"


# ---------------------------------------------------------------------------
# 误报回归 — 本仓库已有真实 PR 案例 (review-cases/) + 正常 PR 形状
# 历史教训: 泛词误报导致 coach 一律 high_risk
# ---------------------------------------------------------------------------

def _load_real_cases():
    cases_dir = REPO_ROOT / "review-cases"
    cases = []
    for f in sorted(cases_dir.glob("*.json")):
        try:
            cases.append(json.loads(f.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return cases


class TestFalsePositiveRegression:
    def test_real_pr_cases_not_all_high_risk(self):
        cases = _load_real_cases()
        if len(cases) < 50:
            pytest.skip("review-cases corpus too small")
        tiers = {}
        structural_fp = []
        for case in cases:
            body = case.get("body_summary") or ""
            result = analyze_pr(
                case.get("title", ""), body, case.get("repo", "org/repo"),
                REPO_ROOT, body=body,
            )
            tiers[result["tier"]] = tiers.get(result["tier"], 0) + 1
            for hit in result["anti_patterns_detail"]:
                if hit.get("match_type") == "structural" and hit["key"] in (
                    FABRICATED_KEY, STATE_KEY
                ):
                    structural_fp.append((case.get("case_id"), hit["key"], hit.get("check")))

        high = tiers.get("high_risk", 0)
        # 不能把正常 PR 全判 high_risk: 基线 302 案例里 9 条 high_risk (~3%)，
        # 阈值 20% 是"一律 high_risk"灾难的保守护栏
        assert high / len(cases) < 0.20, f"high_risk 率过高: {tiers}"
        # 标题/摘要层面不该冒出结构性命中（案例库没有完整 body，结构检查应静默）
        assert structural_fp == [], f"structural false positives: {structural_fp[:5]}"

    @pytest.mark.parametrize("body,description", [
        (NORMAL_PYTEST_BODY, "Ran the test suite"),
        (NORMAL_JEST_BODY, "Frontend tests"),
        (NORMAL_DOCS_BODY, "Typo fix"),
    ])
    def test_normal_pr_shapes_stay_clean(self, body, description):
        result = analyze_pr("fix: normal change", description, "org/repo", REPO_ROOT, body=body)
        assert result["tier"] != "high_risk", result["signals"]["negative"]
        assert not any(
            h["key"] in (FABRICATED_KEY, STATE_KEY) and h.get("match_type") == "structural"
            for h in result["anti_patterns_detail"]
        )
        assert _coach_exit("fix: normal change", body, description) == 0

    def test_review_corpus_reports_case_count(self):
        # 防止回归测试悄悄变成空转
        assert len(_load_real_cases()) >= 100
