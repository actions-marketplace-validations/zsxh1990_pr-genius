"""Issue #41 self-tests: --enforce-evidence must actually cover review-cases/*.json.

可重复跑的隔离测试 —— 每个用例自建 tmp 仓库 (index.md + review-cases/*.json),
不碰真实 review-cases/ 数据。

约定 (issue #41 自测要求):
1. 缺 verified_at / evidence_urls 的 JSON → `--enforce-evidence` 必须 exit 1;
   不带该 flag 必须 exit 0
2. 字段齐全的 JSON → 两种模式都 exit 0
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATE_SCRIPT = REPO_ROOT / "validate.py"
CHECK_MODULE = REPO_ROOT / "validate_checks" / "review_case_evidence.py"

# 合法样例: 字段齐全 (verified_at ISO-8601 + evidence_urls http(s) 列表)
COMPLETE_RECORD = {
    "id": "example-complete-1",
    "repo": "example/repo",
    "pr_number": 1,
    "title": "A real PR",
    "verified_at": "2026-10-01T12:00:00Z",
    "evidence_urls": ["https://github.com/example/repo/pull/1"],
}

# 缺字段样例: 两个证据字段都没有
MISSING_RECORD = {
    "id": "example-missing-1",
    "repo": "example/repo",
    "pr_number": 2,
    "title": "No evidence fields",
}

# 字段在但格式非法: verified_at 不是 ISO-8601, evidence_urls 不是 http(s) URL 列表
INVALID_RECORD = {
    "id": "example-invalid-1",
    "repo": "example/repo",
    "pr_number": 3,
    "verified_at": "yesterday",
    "evidence_urls": ["not-a-url"],
}

INDEX_MD = """\
---
type: Index
title: Test index
---
# Test index
"""


def setup_isolated_validate(tmp_path: Path) -> Path:
    """Copy validate.py + its evidence check into tmp_path (ROOT resolves there)."""
    shutil.copy2(VALIDATE_SCRIPT, tmp_path / "validate.py")
    pkg = tmp_path / "validate_checks"
    pkg.mkdir(exist_ok=True)
    shutil.copy2(CHECK_MODULE, pkg / "review_case_evidence.py")
    return tmp_path / "validate.py"


def write_case(tmp_path: Path, name: str, record: dict) -> Path:
    cases = tmp_path / "review-cases"
    cases.mkdir(exist_ok=True)
    p = cases / name
    p.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return p


def run_validate(tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
    setup_isolated_validate(tmp_path)
    (tmp_path / "index.md").write_text(INDEX_MD, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(tmp_path / "validate.py"), *args],
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )


# ---------------------------------------------------------------------------
# 1. 缺字段样例: --enforce-evidence exit 1; 不带 flag exit 0
# ---------------------------------------------------------------------------


class TestMissingEvidenceFields:
    def test_enforce_evidence_exits_1(self, tmp_path: Path):
        write_case(tmp_path, "missing.json", MISSING_RECORD)
        result = run_validate(tmp_path, "--enforce-evidence")
        assert result.returncode == 1
        assert "[evidence-gate]" in result.stdout
        assert "missing `verified_at`" in result.stdout
        assert "missing `evidence_urls`" in result.stdout

    def test_without_flag_exits_0(self, tmp_path: Path):
        write_case(tmp_path, "missing.json", MISSING_RECORD)
        result = run_validate(tmp_path)
        assert result.returncode == 0
        # 只警告: 找到的是 warning 文本, 不是 error 汇总
        assert "[evidence-gate]" in result.stdout
        assert "❌" not in result.stdout

    def test_strict_without_enforce_exits_0(self, tmp_path: Path):
        """不带 --enforce-evidence 时只 warning, 不挡 --strict (issue #41 要求 4)。"""
        write_case(tmp_path, "missing.json", MISSING_RECORD)
        result = run_validate(tmp_path, "--strict")
        assert result.returncode == 0

    def test_invalid_format_treated_as_missing(self, tmp_path: Path):
        """字段在但格式非法 → 与缺失同级, enforce 下同样 exit 1。"""
        write_case(tmp_path, "invalid.json", INVALID_RECORD)
        result = run_validate(tmp_path, "--enforce-evidence")
        assert result.returncode == 1
        assert "invalid `verified_at`" in result.stdout
        assert "invalid `evidence_urls`" in result.stdout


# ---------------------------------------------------------------------------
# 2. 字段齐全样例: 两种模式都 exit 0
# ---------------------------------------------------------------------------


class TestCompleteEvidenceFields:
    def test_enforce_evidence_exits_0(self, tmp_path: Path):
        write_case(tmp_path, "complete.json", COMPLETE_RECORD)
        result = run_validate(tmp_path, "--enforce-evidence")
        assert result.returncode == 0
        assert "100.0%" in result.stdout
        assert "[evidence-gate]" not in result.stdout

    def test_without_flag_exits_0(self, tmp_path: Path):
        write_case(tmp_path, "complete.json", COMPLETE_RECORD)
        result = run_validate(tmp_path)
        assert result.returncode == 0
        assert "[evidence-gate]" not in result.stdout

    def test_strict_exits_0(self, tmp_path: Path):
        write_case(tmp_path, "complete.json", COMPLETE_RECORD)
        result = run_validate(tmp_path, "--strict")
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 3. 覆盖率输出 (issue #41 要求 5: 百分比, 可看趋势)
# ---------------------------------------------------------------------------


class TestCoverageReport:
    def test_coverage_zero_of_two(self, tmp_path: Path):
        write_case(tmp_path, "a.json", MISSING_RECORD)
        write_case(tmp_path, "b.json", INVALID_RECORD)
        result = run_validate(tmp_path)
        assert result.returncode == 0
        assert "evidence coverage: 0/2 (0.0%)" in result.stdout

    def test_coverage_one_of_two(self, tmp_path: Path):
        write_case(tmp_path, "a.json", COMPLETE_RECORD)
        write_case(tmp_path, "b.json", MISSING_RECORD)
        result = run_validate(tmp_path, "--enforce-evidence")
        assert result.returncode == 1
        assert "evidence coverage: 1/2 (50.0%)" in result.stdout

    def test_no_review_cases_dir_is_ok(self, tmp_path: Path):
        result = run_validate(tmp_path)
        assert result.returncode == 0
        assert "no review-cases/ dir" in result.stdout


# ---------------------------------------------------------------------------
# 4. 纯函数单测
# ---------------------------------------------------------------------------


class TestIsoAndUrlHelpers:
    def test_iso8601_accepts(self):
        from validate_checks.review_case_evidence import _is_iso8601

        for v in (
            "2026-10-01",
            "2026-10-01T12:00:00Z",
            "2026-10-01T12:00:00.500+08:00",
            "2026-10-01 12:00:00",
        ):
            assert _is_iso8601(v), v

    def test_iso8601_rejects(self):
        from validate_checks.review_case_evidence import _is_iso8601

        for v in ("yesterday", "01/10/2026", "", None, 20261001, "2026-13-45"):
            assert not _is_iso8601(v), v

    def test_urls_ok(self):
        from validate_checks.review_case_evidence import _urls_ok

        assert _urls_ok(["https://github.com/a/b/pull/1"])
        assert _urls_ok(["http://example.com/issue/2"])
        assert not _urls_ok([])
        assert not _urls_ok("https://example.com")
        assert not _urls_ok(["ftp://example.com"])
        assert not _urls_ok(["https://example.com", "nope"])

    def test_check_returns_stats(self, tmp_path: Path):
        from validate_checks.review_case_evidence import check_review_case_evidence

        write_case(tmp_path, "complete.json", COMPLETE_RECORD)
        write_case(tmp_path, "missing.json", MISSING_RECORD)
        warnings: list[str] = []
        errors: list[str] = []
        stats = check_review_case_evidence(tmp_path, warnings, errors)
        assert stats == {"total": 2, "complete": 1, "coverage_pct": 50.0}
        assert errors == []
        assert any("missing `verified_at`" in w for w in warnings)

        warnings.clear()
        errors.clear()
        check_review_case_evidence(tmp_path, warnings, errors, enforce_evidence=True)
        assert warnings == []
        assert any("missing `verified_at`" in e for e in errors)
