"""Tests for CLI entry points — argument parsing, subcommand registration, help output."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prgenius.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# All top-level subcommands registered in main()
SUBCOMMANDS = [
    "analyze",
    "coach",
    "eval",
    "triage",
    "doctor",
    "suggest",
    "harvest",
    "profile",
    "case",
    "schema",
    "status",
    "update-issue",
    "auto-ping",
    "auto-rebase",
    "dump",
    "mcp",
    "maintainer",
    "review-queue",
    "issue",
    "issue-batch",
]


# ---------------------------------------------------------------------------
# 1. main() with no args
# ---------------------------------------------------------------------------


def test_main_no_args_prints_usage_and_exits():
    """Calling main() with no arguments should fail gracefully (required subcommand missing)."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    # argparse exits 2 for missing required subcommand
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# 2. main() with --help
# ---------------------------------------------------------------------------


def test_main_help(capsys):
    """--help on the root parser should print usage and exit 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "prgenius" in captured.out.lower() or "usage" in captured.out.lower()


def test_main_version(capsys):
    """--version should print version string and exit 0."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "prgenius" in captured.out


# ---------------------------------------------------------------------------
# 3. main() with invalid subcommand
# ---------------------------------------------------------------------------


def test_main_invalid_subcommand():
    """An unknown subcommand should fail gracefully."""
    with pytest.raises(SystemExit) as exc_info:
        main(["nonexistent-subcommand"])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# 4. Each subcommand with --help
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subcmd", SUBCOMMANDS)
def test_subcommand_help(capsys, subcmd):
    """Every registered subcommand should accept --help without error."""
    with pytest.raises(SystemExit) as exc_info:
        main([subcmd, "--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    # Help output should contain the subcommand name or "usage"
    text = captured.out.lower()
    assert "usage" in text or subcmd in text


# Nested subcommands that need a second-level arg to reach --help
@pytest.mark.parametrize("subcmd,extra", [
    ("profile", "get"),
    ("profile", "writeback"),
    ("case", "list"),
    ("schema", "info"),
    ("mcp", "serve"),
])
def test_nested_subcommand_help(capsys, subcmd, extra):
    """Nested subcommands (e.g. profile get) should accept --help."""
    with pytest.raises(SystemExit) as exc_info:
        main([subcmd, extra, "--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    text = captured.out.lower()
    assert "usage" in text or extra in text


# ---------------------------------------------------------------------------
# 5. console_scripts entry point registered in pyproject.toml
# ---------------------------------------------------------------------------


def test_console_scripts_entry_in_pyproject():
    """pyproject.toml must declare the prgenius-core CLI entry point."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    assert pyproject.exists(), f"pyproject.toml not found at {pyproject}"
    content = pyproject.read_text(encoding="utf-8")
    assert "prgenius-core" in content
    assert "prgenius.cli:main" in content


# ---------------------------------------------------------------------------
# 6. cmd_* functions are wired to subcommands via set_defaults
# ---------------------------------------------------------------------------


@patch("prgenius.cli.analyze_pr")
def test_analyze_subcommand_invokes_cmd_analyze(mock_analyze):
    """Invoking 'analyze' should call cmd_analyze which calls analyze_pr."""
    mock_analyze.return_value = {
        "tier": "low_risk",
        "repo": "org/repo",
        "signals": {"positive": [], "negative": [], "neutral": []},
        "checklist": [],
        "repo_context": {},
        "summary": "low_risk summary",
    }
    rc = main(["analyze", "fix: typo", "--repo", "org/repo", "--format", "json"])
    assert rc == 0
    mock_analyze.assert_called_once()


@patch("prgenius.cli.triage_pr")
def test_triage_subcommand_invokes_cmd_triage(mock_triage):
    """Invoking 'triage' should call cmd_triage which calls triage_pr.

    issue #63: verdict=pass only occurs with policy_loaded=True, and that is
    the only path that may exit 0.
    """
    mock_triage.return_value = {
        "verdict": "pass",
        "repo": "org/repo",
        "message": "ok",
        "policy_loaded": True,
        "violations": [],
        "rules_checked": 3,
        "policy_file": "docs/policies/org-repo.md",
    }
    rc = main(["triage", "fix: typo", "--repo", "org/repo", "--format", "json"])
    assert rc == 0
    mock_triage.assert_called_once()


@patch("prgenius.cli.triage_pr")
def test_triage_no_policy_exits_nonzero(mock_triage):
    """issue #63: no policy must not exit 0 (CI treats 0 as 'policy passed').

    exit 2 = no policy + no universal anti-patterns; exit 3 = no policy + hits.
    """
    base = {
        "verdict": "needs_preflight",
        "repo": "org/repo",
        "message": "No maintainer policy found",
        "policy_loaded": False,
        "violations": [],
        "generic_checks": [],
    }
    mock_triage.return_value = {**base, "fallback_signals": []}
    rc = main(["triage", "fix: typo", "--repo", "org/repo", "--format", "json"])
    assert rc == 2

    mock_triage.return_value = {
        **base,
        "fallback_signals": [{"key": "some-anti-pattern", "severity": "high"}],
    }
    rc = main(["triage", "fix: typo", "--repo", "org/repo", "--format", "json"])
    assert rc == 3


@patch("prgenius.cli.check_status")
def test_status_subcommand_requires_author_or_repo(mock_status):
    """status without --author or --repo should exit with error."""
    mock_status.return_value = {"prs": [], "transitions": []}
    # No --author and no --repo
    rc = main(["status"])
    assert rc == 1


@patch("prgenius.cli.check_status")
def test_status_subcommand_calls_check_status(mock_status):
    """status with --author and --format json should call check_status."""
    mock_status.return_value = {
        "author": "testuser",
        "checked_at": "2026-01-01T00:00:00Z",
        "prs": [],
        "transitions": [],
        "summary": {},
    }
    # Use --format json to skip format_table which needs richer data
    rc = main(["status", "--author", "testuser", "--format", "json"])
    assert rc == 0
    mock_status.assert_called_once()


def test_harvest_subcommand_missing_script():
    """harvest should fail gracefully when the harvest script doesn't exist."""
    with patch("prgenius.cli._get_repo_root") as mock_root:
        mock_root.return_value = Path("/nonexistent")
        rc = main(["harvest", "org/repo", "123"])
    assert rc == 1


@patch("prgenius.cli.profile_get")
def test_profile_get_subcommand(mock_profile_get):
    """profile get should call profile_get and return 0."""
    mock_profile_get.return_value = {
        "path": "profiles/org/repo.md",
        "folder": "org/repo",
        "frontmatter": {"schema_version": "0.2"},
        "body": "line1\nline2",
    }
    rc = main(["profile", "get", "org/repo"])
    assert rc == 0
    mock_profile_get.assert_called_once()


@patch("prgenius.cli.profile_get")
def test_profile_get_not_found(mock_profile_get):
    """profile get for unknown repo should return exit code 2."""
    mock_profile_get.return_value = None
    rc = main(["profile", "get", "unknown/repo"])
    assert rc == 2


# ---------------------------------------------------------------------------
# issue #72: CLI input validation — impossible values must be rejected
# ---------------------------------------------------------------------------


def test_analyze_rejects_negative_star_count():
    """--star-count < 0 is impossible; argparse must reject it (exit 2)."""
    with pytest.raises(SystemExit) as exc_info:
        main(["analyze", "test", "--repo", "encode/httpx", "--star-count", "-1000"])
    assert exc_info.value.code == 2


def test_analyze_rejects_merge_rate_above_one():
    """--repo-merge-rate must be in [0.0, 1.0]."""
    with pytest.raises(SystemExit) as exc_info:
        main(["analyze", "test", "--repo", "encode/httpx", "--repo-merge-rate", "2.0"])
    assert exc_info.value.code == 2


def test_analyze_rejects_bad_author_association():
    """--author-association must be one of the known enums."""
    with pytest.raises(SystemExit) as exc_info:
        main(["analyze", "test", "--repo", "encode/httpx",
              "--author-association", "INVALID_VALUE"])
    assert exc_info.value.code == 2


def test_analyze_rejects_bad_mergeable():
    """--mergeable must be one of MERGEABLE/CONFLICTING/UNKNOWN."""
    with pytest.raises(SystemExit) as exc_info:
        main(["analyze", "test", "--repo", "encode/httpx", "--mergeable", "MAYBE"])
    assert exc_info.value.code == 2


def test_coach_rejects_negative_star_count():
    """coach shares the same validators as analyze."""
    with pytest.raises(SystemExit) as exc_info:
        main(["coach", "test", "--repo", "encode/httpx", "--star-count", "-1"])
    assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# issue #70: doctor subcommand
# ---------------------------------------------------------------------------


def test_doctor_subcommand_json(capsys):
    """doctor --format json emits a machine-readable self-test report."""
    rc = main(["--repo-root", str(REPO_ROOT), "doctor", "--format", "json"])
    captured = capsys.readouterr()
    import json as _json
    report = _json.loads(captured.out)
    for key in ("ok", "prgenius_version", "python_version", "knowledge_base",
                "gh", "mcp", "sample", "warnings"):
        assert key in report, f"missing doctor key: {key}"
    # exit 0 = OK, 1 = hard failure — either is a valid self-test outcome
    assert rc in (0, 1)
    assert report["knowledge_base"]["anti_patterns"] > 0
