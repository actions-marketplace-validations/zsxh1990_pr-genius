"""Tests for evaluator module (Phase 6.1)."""

import os
import time
import pytest
import tempfile
from pathlib import Path

from prgenius.evaluator import (
    is_bot_author,
    get_repo_size,
    check_issue_link,
    _parse_label,
    analyze_pr,
    eval_pr,
    load_anti_patterns,
    _anti_patterns_cache,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestIsBotAuthor:
    """Test bot author detection."""

    def test_known_bot(self):
        """Known bot should return True."""
        assert is_bot_author("dependabot[bot]") is True
        assert is_bot_author("github-actions[bot]") is True
        assert is_bot_author("renovate[bot]") is True

    def test_human_author(self):
        """Human author should return False."""
        assert is_bot_author("zsxh1990") is False
        assert is_bot_author("octocat") is False

    def test_case_insensitive(self):
        """Should be case insensitive."""
        assert is_bot_author("DEPENDABOT[bot]") is True
        assert is_bot_author("GitHub-Actions[bot]") is True

    def test_empty_string(self):
        """Empty string should return False."""
        assert is_bot_author("") is False

    def test_whitespace(self):
        """Whitespace should be handled."""
        assert is_bot_author("  dependabot[bot]  ") is True


class TestGetRepoSize:
    """Test repo size classification."""

    def test_small_repo(self):
        """Small repo (< 5000 stars)."""
        assert get_repo_size(50) == "small"
        assert get_repo_size(500) == "small"

    def test_medium_repo(self):
        """Medium repo (5000-50000 stars)."""
        assert get_repo_size(5000) == "medium"
        assert get_repo_size(10000) == "medium"

    def test_large_repo(self):
        """Large repo (>= 50000 stars)."""
        assert get_repo_size(50000) == "large"
        assert get_repo_size(100000) == "large"

    def test_zero_stars(self):
        """Zero stars should be small."""
        assert get_repo_size(0) == "small"


class TestCheckIssueLink:
    """Test issue link detection."""

    def test_fixes_keyword(self):
        """Should detect 'Fixes #123'."""
        assert check_issue_link("Fixes #123") is True

    def test_closes_keyword(self):
        """Should detect 'Closes #456'."""
        assert check_issue_link("Closes #456") is True

    def test_resolves_keyword(self):
        """Should detect 'Resolves #789'."""
        assert check_issue_link("Resolves #789") is True

    def test_no_issue_link(self):
        """Should return False when no issue link."""
        assert check_issue_link("Just a regular PR body") is False

    def test_empty_body(self):
        """Empty body should return False."""
        assert check_issue_link("") is False


class TestParseLabel:
    """Test label parsing."""

    def test_positive_label(self):
        """Should parse positive label."""
        label, polarity = _parse_label("help wanted")
        assert label == "help wanted"
        assert polarity == "positive"

    def test_negative_label(self):
        """Should parse negative label."""
        label, polarity = _parse_label("wontfix")
        assert label == "wontfix"
        assert polarity == "negative"

    def test_unknown_label(self):
        """Should parse unknown label."""
        label, polarity = _parse_label("breaking change")
        assert label == "breaking change"
        assert polarity == "unknown"


class TestAnalyzePr:
    """Test PR analysis."""

    def test_basic_analysis(self):
        """Should return a valid analysis dict."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert "tier" in result
        assert "signals" in result
        assert "summary" in result
        assert result["tier"] in ("low_risk", "medium_risk", "high_risk")

    def test_summary_field(self):
        """Should have summary field with emoji."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert result["summary"].startswith(("🟢", "🟡", "🔴"))

    def test_signals_structure(self):
        """Should have proper signals structure."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        signals = result["signals"]
        assert "positive" in signals
        assert "negative" in signals
        assert "neutral" in signals
        assert isinstance(signals["positive"], list)
        assert isinstance(signals["negative"], list)
        assert isinstance(signals["neutral"], list)

    def test_merge_probability(self):
        """Should return merge probability."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
            repo_merge_rate=0.5,
        )
        assert "merge_probability" in result
        assert 0.0 <= result["merge_probability"] <= 1.0

    def test_checklist(self):
        """Should return a checklist."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert "checklist" in result
        assert isinstance(result["checklist"], list)

    def test_bot_author_detected(self):
        """Should detect bot author in signals."""
        result = analyze_pr(
            title="chore: bump deps",
            description="Bump deps",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Auto-generated",
            author="dependabot[bot]",
        )
        signals = result["signals"]["neutral"]
        keys = [s["key"] for s in signals]
        assert "bot_author" in keys

    def test_owner_author_detected(self):
        """Should detect owner author."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
            author="org",
            author_association="OWNER",
        )
        signals = result["signals"]["positive"]
        keys = [s["key"] for s in signals]
        assert "owner_author" in keys

    def test_issue_linked_detected(self):
        """Should detect issue link."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #123",
        )
        signals = result["signals"]["positive"]
        keys = [s["key"] for s in signals]
        assert "issue_linked" in keys

    def test_first_contributor_detected(self):
        """Should detect first contributor."""
        result = analyze_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
            author_association="NONE",
        )
        signals = result["signals"]["neutral"]
        keys = [s["key"] for s in signals]
        assert "first_contributor" in keys


class TestEvalPr:
    """Test eval_pr (compatibility layer)."""

    def test_returns_eval_dict(self):
        """Should return eval dict with tier."""
        result = eval_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        assert "tier" in result
        assert "tier_raw" in result
        assert "analysis" in result
        assert result["tier"] in ("低风险", "中风险", "高风险")

    def test_tier_mapping(self):
        """Should map tier correctly."""
        result = eval_pr(
            title="fix: typo",
            description="Fix typo",
            repo="org/repo",
            repo_root=REPO_ROOT,
            body="Fixes #1",
        )
        tier_raw = result["tier_raw"]
        tier_display = result["tier"]
        if tier_raw == "low_risk":
            assert tier_display == "低风险"
        elif tier_raw == "medium_risk":
            assert tier_display == "中风险"
        elif tier_raw == "high_risk":
            assert tier_display == "高风险"


class TestCacheInvalidation:
    """Test that pattern caches invalidate when files change on disk."""

    ANTI_PATTERN_TEMPLATE = """---
key: {key}
trigger_keywords:
  - {keyword}
symptom: {symptom}
fix_action: fix it
---
"""

    def _make_repo(self, tmpdir, key="test-pattern", keyword="badcode", symptom="bad code"):
        """Create a minimal repo structure with one anti-pattern file."""
        anti_dir = Path(tmpdir) / "anti-patterns"
        anti_dir.mkdir(exist_ok=True)
        pattern_file = anti_dir / f"{key}.md"
        pattern_file.write_text(
            self.ANTI_PATTERN_TEMPLATE.format(key=key, keyword=keyword, symptom=symptom),
            encoding="utf-8",
        )
        return Path(tmpdir)

    def test_cache_returns_same_object_on_no_change(self):
        """Cache hit should return the same dict (identity check)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = self._make_repo(tmpdir)
            cache_key = str(repo_root)
            _anti_patterns_cache.pop(cache_key, None)

            result1 = load_anti_patterns(repo_root)
            result2 = load_anti_patterns(repo_root)
            assert result1 is result2  # same object = cache hit

    def test_cache_invalidates_on_file_mtime_change(self):
        """When a pattern file is modified, the next load should pick it up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = self._make_repo(tmpdir, key="mtime-test", keyword="oldkword")
            cache_key = str(repo_root)
            _anti_patterns_cache.pop(cache_key, None)

            result1 = load_anti_patterns(repo_root)
            assert "mtime-test" in result1
            assert "oldkword" in result1["mtime-test"].get("trigger_keywords", [])

            # Force cache to expire by setting load_time to 0
            entry = _anti_patterns_cache[cache_key]
            assert isinstance(entry, tuple) and len(entry) == 3
            patterns, mtimes, _ = entry
            _anti_patterns_cache[cache_key] = (patterns, mtimes, 0.0)

            # Modify the pattern file
            pattern_file = repo_root / "anti-patterns" / "mtime-test.md"
            pattern_file.write_text(
                self.ANTI_PATTERN_TEMPLATE.format(key="mtime-test", keyword="newkword", symptom="new symptom"),
                encoding="utf-8",
            )
            os.utime(pattern_file, (time.time() + 10, time.time() + 10))

            # Next load should pick up the change
            result2 = load_anti_patterns(repo_root)
            assert result2 is not result1
            assert "newkword" in result2["mtime-test"].get("trigger_keywords", [])

    def test_cache_invalidates_on_new_file_added(self):
        """When a new pattern file is added, the next load should include it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = self._make_repo(tmpdir, key="existing", keyword="exists")
            cache_key = str(repo_root)
            _anti_patterns_cache.pop(cache_key, None)

            result1 = load_anti_patterns(repo_root)
            assert "existing" in result1
            assert "added-later" not in result1

            # Force cache to expire
            entry = _anti_patterns_cache[cache_key]
            assert isinstance(entry, tuple) and len(entry) == 3
            patterns, mtimes, _ = entry
            _anti_patterns_cache[cache_key] = (patterns, mtimes, 0.0)

            # Add a new pattern file
            new_file = repo_root / "anti-patterns" / "added-later.md"
            new_file.write_text(
                self.ANTI_PATTERN_TEMPLATE.format(key="added-later", keyword="newthing", symptom="new thing"),
                encoding="utf-8",
            )

            result2 = load_anti_patterns(repo_root)
            assert "existing" in result2
            assert "added-later" in result2
