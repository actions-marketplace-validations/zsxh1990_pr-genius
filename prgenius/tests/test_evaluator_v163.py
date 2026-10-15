"""Tests for evaluator v1.6.3 features (PR size, impact scoring, anti-patterns)."""

import pytest
from pathlib import Path

from prgenius.evaluator import (
    analyze_pr,
    check_anti_patterns,
    load_anti_patterns, load_pr_observations,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestPRSizeAssessment:
    """Test PR size tier calculation."""

    def test_xs_pr(self):
        """PR with docs/typo keywords should be XS."""
        result = analyze_pr(
            title="docs: update README",
            description="Update documentation",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Update documentation",
        )
        assert result["pr_size"] == "XS"
        assert "极小" in result["pr_size_label"]

    def test_s_pr(self):
        """PR with fix/bug keywords should be S."""
        result = analyze_pr(
            title="fix: resolve login issue",
            description="Fix bug",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["pr_size"] == "S"
        assert "小" in result["pr_size_label"]

    def test_m_pr(self):
        """PR with add/feature keywords should be M."""
        result = analyze_pr(
            title="feat: add new feature",
            description="Add feature",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["pr_size"] == "M"
        assert "中等" in result["pr_size_label"]

    def test_xl_pr(self):
        """PR with major/refactor keywords should be XL."""
        result = analyze_pr(
            title="refactor: major rewrite of core system",
            description="Breaking change",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["pr_size"] == "XL"
        assert "超大" in result["pr_size_label"]

    def test_default_size(self):
        """PR without matching keywords should default to S."""
        result = analyze_pr(
            title="update: general changes",
            description="Various updates",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["pr_size"] == "S"


class TestImpactScoring:
    """Test impact score calculation."""

    def test_low_impact(self):
        """Low-risk PR should have low impact score."""
        result = analyze_pr(
            title="fix: typo in README",
            description="Small typo fix",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["impact_score"] <= 50
        assert result["risk_level"] in ("low", "medium")

    def test_high_impact(self):
        """High-risk PR should have high impact score."""
        result = analyze_pr(
            title="feat: major refactor of authentication system",
            description="Breaking change",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
            labels=["breaking-change"],
        )
        assert result["impact_score"] >= 50
        assert result["risk_level"] in ("medium", "high")

    def test_risk_description_exists(self):
        """Risk description should be provided."""
        result = analyze_pr(
            title="fix: typo",
            description="Small fix",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert "risk_description" in result
        assert isinstance(result["risk_description"], str)
        assert len(result["risk_description"]) > 0


class TestAntiPatternMatching:
    """Test anti-pattern matching with new patterns."""

    def test_load_anti_patterns(self):
        """Should load anti-patterns from markdown files."""
        patterns = load_anti_patterns(REPO_ROOT)
        assert len(patterns) > 0
        # Check that known patterns exist
        keys = list(patterns.keys())
        assert "ai-generated-content" in keys
        assert "breaking-change-no-compat" in keys
        assert "contribai-missing-tests" in keys
        assert "duplicate-pr-same-author" in keys

    def test_json_patterns_marked(self):
        """Failed-PR observations are NOT anti-patterns and are not loaded as them.

        This test used to assert the opposite — that `load_anti_patterns`
        returned 190 JSON records tagged `_is_json_pattern`. Those records are
        structured observations of failed PRs (repo, author, merged, signals),
        with no lesson and no fix_action. Counting them in the anti-pattern
        corpus made it 251 entries of which 190 could never fire, so every
        coverage figure needed a footnote explaining its own denominator.

        They now live in `pr-observations/`, read by `load_pr_observations()`.
        Keeping the old name on purpose: someone searching for the JSON-pattern
        behaviour lands on the explanation instead of restoring it.
        """
        patterns = load_anti_patterns(REPO_ROOT)
        assert not any(p.get("_is_json_pattern") for p in patterns.values()), (
            "anti-patterns/ holds anti-patterns; PR observations belong in pr-observations/"
        )

        observations = load_pr_observations(REPO_ROOT)
        assert len(observations) > 0, "pr-observations/ should still hold the failed-PR records"
        assert all("id" in o for o in observations), "observations keep their structured shape"
        # They are a dataset of things that did not land — that is the point.
        assert all(o.get("merged") is False for o in observations), (
            "pr-observations records PRs that failed; a merged one would be the wrong corpus"
        )

    def test_check_anti_patterns(self):
        """Should check anti-patterns against PR."""
        result = check_anti_patterns(
            title="feat: add new feature",
            description="Add feature",
            body="",
            repo="org/repo",
            repo_root=REPO_ROOT,
        )
        assert isinstance(result, list)
        # Each result should have required fields
        for item in result:
            assert "key" in item
            assert "fix_action" in item


class TestChecklistDeduplication:
    """Test checklist deduplication logic."""

    def test_no_duplicate_checklist_actions(self):
        """Checklist should not have duplicate action keys."""
        result = analyze_pr(
            title="feat: major refactor",
            description="Breaking change",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
            labels=["breaking-change"],
        )
        checklist = result["checklist"]
        # Extract action keys
        actions = [item.get("action", "") for item in checklist]
        # Check for duplicates
        assert len(actions) == len(set(actions)), f"Duplicate checklist actions found: {actions}"


class TestOutputFields:
    """Test that all required output fields are present."""

    def test_all_fields_present(self):
        """All v1.6.3 fields should be present in result."""
        result = analyze_pr(
            title="fix: typo",
            description="Small fix",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        required_fields = [
            "repo",
            "title",
            "tier",
            "summary",
            "merge_probability",
            "optimization_path",
            "signals",
            "checklist",
            "anti_patterns_hit",
            "anti_patterns_detail",
            "repo_context",
            "comparison",
            "pr_size",
            "pr_size_label",
            "impact_score",
            "risk_level",
            "risk_description",
        ]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
