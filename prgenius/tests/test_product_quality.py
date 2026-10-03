"""Product-quality gates for issues #66, #67, #68, #69 (Ikalus1988 audit).

每个 issue 都有可复跑的测量/断言:
  #66 反模式在真实 PR 上的命中率可测量, 输出带 coverage 盘点
  #67 泛化判据冻结在 scripts/measure_pattern_coverage.py 的 criteria 里
  #68 merge_probability 降级必须自报 degraded + 原因
  #69 success-patterns 只做检索/参考, 不参与评分 (评分语义不许偷偷变)

判据冻结原则: 不为了让数字好看调整判据, 也不给命中率设"及格线"。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prgenius.evaluator import (
    _estimate_merge_probability,
    analyze_pr,
    check_anti_patterns,
    coerce_merge_rate,
    load_success_patterns,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# issue #66 — coverage 盘点 + 真实语料测量
# ---------------------------------------------------------------------------


class TestIssue66Coverage:
    def test_coverage_field_reports_eligible_patterns(self):
        """analyze_pr 输出必须说明: 库里多少条、多少条对本 PR 可参与匹配。"""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        cov = result["coverage"]
        for key in (
            "anti_patterns_loaded",
            "anti_patterns_loaded_md",
            "anti_patterns_loaded_json",
            "anti_patterns_with_trigger_keywords",
            "anti_patterns_without_trigger_keywords",
            "anti_patterns_scope_generic",
            "anti_patterns_scope_repo_specific",
            "anti_patterns_eligible",
            "anti_patterns_fired",
        ):
            assert key in cov, f"coverage missing {key}"
        assert cov["anti_patterns_loaded_md"] + cov["anti_patterns_loaded_json"] == cov["anti_patterns_loaded"]
        assert cov["anti_patterns_with_trigger_keywords"] + cov["anti_patterns_without_trigger_keywords"] == cov["anti_patterns_loaded"]
        assert cov["anti_patterns_scope_generic"] + cov["anti_patterns_scope_repo_specific"] == cov["anti_patterns_loaded"]
        assert 0 <= cov["anti_patterns_fired"] <= cov["anti_patterns_eligible"] <= cov["anti_patterns_loaded"]
        # fired 数必须和 signals 里报出来的命中一致
        assert cov["anti_patterns_fired"] == len(result["anti_patterns_hit"])

    def test_measurement_script_runs_on_real_corpus(self):
        """scripts/measure_pattern_coverage.py 可在真实语料上复跑且自洽。"""
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import measure_pattern_coverage as mpc

        m = mpc.measure(REPO_ROOT)
        a, s, c = m["anti_patterns"], m["success_patterns"], m["corpus"]

        assert c["cases"] > 0, "review-cases 语料为空, 测量无意义"
        assert 0 <= a["pattern_fire_rate"] <= 1
        assert 0 <= a["case_hit_rate"] <= 1
        assert a["with_trigger_keywords"] + a["without_trigger_keywords"] == a["loaded_total"]
        assert a["scope_generic_no_repo_field"] + a["scope_repo_specific"] == a["loaded_total"]
        assert a["fired_by_shipped_matcher"] <= a["loaded_total"]
        assert a["cases_with_hit"] <= c["cases"]
        assert s["loaded_total"] == (
            s["with_content_tags"] + s["with_meta_tags_only"] + s["without_tags"]
        )
        # 判据必须随测量输出 (冻结判据, 不许事后换口径)
        assert set(m["criteria"]) >= {
            "scope_generic",
            "scope_repo",
            "with_trigger_keywords",
            "reachable",
            "empirically_generic",
        }


# ---------------------------------------------------------------------------
# issue #67 — 泛化判据 + repo 过滤语义
# ---------------------------------------------------------------------------


class TestIssue67Genericness:
    def test_genericness_criteria_are_frozen_and_explicit(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import measure_pattern_coverage as mpc

        m = mpc.measure(REPO_ROOT)
        crit = m["criteria"]
        # 泛化定义判据: 不足"跨 ≥2 个真实仓库命中"就不得算 empirically_generic
        assert "≥2" in crit["empirically_generic"] or ">=2" in crit["empirically_generic"]
        assert "repo" in crit["scope_generic"]
        a = m["anti_patterns"]
        assert a["scope_generic_no_repo_field"] + a["scope_repo_specific"] == a["loaded_total"]
        # empirically_generic 一定是 reachable 的子集
        assert a["empirically_generic"] <= a["reachable_via_keywords"]
        s = m["success_patterns"]
        assert s["empirically_generic"] <= s["reachable_via_content_tags"]

    def test_repo_scoped_pattern_only_fires_on_its_repo(self, tmp_path):
        """repo: 字段过滤必须生效 — 别的仓库的 PR 不该被它命中 (issue #67 语义)。"""
        (tmp_path / "anti-patterns").mkdir()
        (tmp_path / "anti-patterns" / "scoped-widget.md").write_text(
            "---\n"
            "type: Anti-Pattern\n"
            "key: scoped-widget\n"
            "repo: acme/widgets\n"
            "trigger_keywords:\n"
            "  - \"zonkabot release gate\"\n"
            "symptom: \"zonkabot release gate\"\n"
            "fix_action: talk to acme maintainers\n"
            "---\n\n# scoped-widget\n",
            encoding="utf-8",
        )
        on_repo = check_anti_patterns(
            "chore: zonkabot release gate", "", "acme/widgets", tmp_path
        )
        off_repo = check_anti_patterns(
            "chore: zonkabot release gate", "", "other/project", tmp_path
        )
        assert any(h["key"] == "scoped-widget" for h in on_repo)
        assert not any(h["key"] == "scoped-widget" for h in off_repo)


# ---------------------------------------------------------------------------
# issue #68 — merge_probability 降级必须说出来
# ---------------------------------------------------------------------------


class TestIssue68MergeProbabilityBasis:
    def test_measured_probability_equals_repo_merge_rate(self):
        """有仓库合并率时, merge_probability 必须用它, 不许静默走 tier 默认。"""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="encode/httpx",
            repo_root=REPO_ROOT,
            body="Fixes #1",
            repo_merge_rate=0.2,
        )
        assert result["merge_probability"] == pytest.approx(0.2)
        assert result["repo_context"]["merge_rate"] == 0.2
        assert result["merge_probability_basis"] == "measured"
        assert result["merge_probability_degraded"] is False
        assert result["merge_probability_degraded_reason"] == ""
        assert result["comparison"].get("repo_merge_rate") == 0.2

    def test_degraded_flag_and_reason_without_rate(self):
        """拿不到合并率时必须 degraded=true + 原因 (issue #68 核心)。"""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="encode/httpx",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["merge_probability_degraded"] is True
        assert result["merge_probability_basis"] in ("tier_estimate", "unknown")
        reason = result["merge_probability_degraded_reason"]
        assert reason, "degraded 必须带原因"
        assert "merge_rate" in reason
        assert 0.0 < result["merge_probability"] < 1.0

    def test_url_string_rate_is_not_treated_as_measured(self):
        """external_merge_rate_30 是 URL 字符串时不得当合并率 (issue #68 根因)。"""
        mp, _, comparison, meta = _estimate_merge_probability(
            signals_neg=[], signals_pos=[], signals_neu=[],
            tier="medium_risk",
            repo_context={"external_merge_rate_30": "https://github.com/x/y/pulls?q=is%3Apr"},
        )
        assert meta["degraded"] is True
        assert meta["basis"] == "tier_estimate"
        assert mp == pytest.approx(0.35)  # medium_risk 档默认
        assert comparison == {}

        mp2, _, comparison2, meta2 = _estimate_merge_probability(
            signals_neg=[], signals_pos=[], signals_neu=[],
            tier="medium_risk",
            repo_context={
                "external_merge_rate_30": "https://github.com/x/y/pulls?q=is%3Apr",
                "external_merge_rate": 0.4,
            },
        )
        assert meta2["degraded"] is False
        assert meta2["basis"] == "measured"
        assert meta2["rate_source"] == "external_merge_rate"
        assert mp2 == pytest.approx(0.4)
        assert comparison2["repo_merge_rate"] == 0.4

    def test_signal_adjustments_still_scale_measured_base(self):
        """降级标注不改概率语义: 区分性信号的乘法仍然生效。"""
        mp, _, _, meta = _estimate_merge_probability(
            signals_neg=[{"key": "merge_conflict", "severity": "high", "description": "x"}],
            signals_pos=[], signals_neu=[],
            tier="high_risk",
            repo_context={"merge_rate": 0.2},
        )
        assert meta["basis"] == "measured"
        assert mp == pytest.approx(0.2 * 0.3)

    def test_coerce_merge_rate_rejects_non_numeric(self):
        assert coerce_merge_rate(0.2) == 0.2
        assert coerce_merge_rate("0.2") == 0.2
        assert coerce_merge_rate("https://example.com/pulls") == 0.0
        assert coerce_merge_rate(None) == 0.0
        assert coerce_merge_rate(0) == 0.0
        assert coerce_merge_rate(1.5) == 0.0

    @pytest.mark.parametrize("degraded,expect_mark", [(True, True), (False, False)])
    def test_cli_text_marks_estimate(self, degraded, expect_mark, capsys):
        """CLI 文本输出在非实测时必须写 (estimate)。"""
        from unittest.mock import patch

        from prgenius.cli import main as cli_main

        canned = {
            "tier": "medium_risk",
            "repo": "encode/httpx",
            "title": "feat: small refactor",
            "summary": "🟡 0 concern(s) to review — see checklist",
            "merge_probability": 0.35,
            "merge_probability_basis": "tier_estimate" if degraded else "measured",
            "merge_probability_degraded": degraded,
            "merge_probability_degraded_reason": "rate unavailable" if degraded else "",
            "signals": {"positive": [], "negative": [], "neutral": []},
            "checklist": [],
            "repo_context": {},
        }
        with patch("prgenius.cli.analyze_pr", return_value=canned):
            rc = cli_main(["analyze", "feat: small refactor", "--repo", "encode/httpx"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "35%" in out
        assert ("(estimate)" in out) is expect_mark


# ---------------------------------------------------------------------------
# issue #69 — success-patterns 只检索/参考, 不参与评分
# ---------------------------------------------------------------------------


class TestIssue69SuccessPatternsNotScored:
    def test_scoring_path_never_consults_success_patterns(self):
        """评分路径一旦读 success-patterns 就爆炸 — 契约: 不参与评分。"""
        import prgenius.evaluator as ev

        def _bomb(repo_root):
            raise AssertionError(
                "success patterns must not be consulted by scoring (issue #69)"
            )

        original = ev.load_success_patterns
        ev.load_success_patterns = _bomb
        try:
            result = analyze_pr(
                title="fix: typo",
                description="Fix typo",
                repo="org/repo",
                repo_root=REPO_ROOT,
                body="Fixes #1",
                repo_merge_rate=0.5,
            )
        finally:
            ev.load_success_patterns = original
        assert result["tier"] in ("low_risk", "medium_risk", "high_risk")

    def test_loader_contract_documents_retrieval_only(self):
        """契约必须写在 docstring 里, 不是靠口头约定。"""
        doc = load_success_patterns.__doc__ or ""
        assert "不参与评分" in doc
        assert "issue #69" in doc

    def test_readme_documents_retrieval_only(self):
        """README 不许再把 success-patterns 卖成参与评分的正反馈系统。"""
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        assert "retrieval/reference only" in readme
        assert "not wired into scoring" in readme
