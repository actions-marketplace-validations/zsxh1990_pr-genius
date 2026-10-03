"""PR metadata extraction — impact, review complexity, author history.

Extracts structured metadata from PR title/body/diff_stat for maintainer decision support.
No GitHub API calls — uses only locally available information.

Phase 5.1 (v1.5.1) — Maintainer View enhancement.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional


# ============================================================
# Impact assessment
# ============================================================

@dataclass
class ImpactAssessment:
    """What files/lines are affected by this PR."""
    files_changed: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    scope: str = ""  # e.g. "tests + docs", "core + auth"
    breaking_change: bool = False
    security_sensitive: bool = False
    dependency_changes: bool = False


# Patterns that indicate breaking changes
_BREAKING_PATTERNS = [
    r"!\s*:",  # conventional commit breaking change (feat!:)
    r"breaking\s+change",
    r"backward[s]?\s+incompatible",
    r"deprecat(e|ion|ing)",
    r"remov(e|al|ing)\s+(api|endpoint|method|function)",
    r"major\s+(version|bump)",
]

# Patterns that indicate security-sensitive changes
_SECURITY_PATTERNS = [
    r"secur(e|ity|ing)",
    r"auth(entication|orization)?",
    r"credential",
    r"token",
    r"password",
    r"secret",
    r"encrypt",
    r"decrypt",
    r"cert(ificate)?",
    r"oauth",
    r"jwt",
    r"saml",
    r"rbac",
    r"permission",
    r"vulnerabilit(y|ies)",
    r"cve-",
    r"xss",
    r"csrf",
    r"injection",
]

# File paths that indicate security-sensitive code
_SECURITY_PATHS = [
    "auth", "security", "login", "session", "token",
    "credential", "password", "secret", "encrypt",
    "oauth", "jwt", "saml", "rbac", "permission",
]

# File paths that indicate dependency changes
_DEPENDENCY_PATHS = [
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.toml", "Cargo.lock",
    "go.mod", "go.sum",
    "Gemfile", "Gemfile.lock",
    "pom.xml", "build.gradle",
    "composer.json", "composer.lock",
    "Pipfile", "Pipfile.lock",
    "poetry.lock",
]


def parse_diff_stat(diff_stat: str) -> tuple[int, int, int]:
    """Parse diff stat string to extract files/lines added/deleted.

    Accepted formats (git diff --stat style):
      - "file1.py | 10 +++--"     → per-file row; the number is total changed
        lines and the +- histogram splits them into insertions/deletions
      - "3 files changed, 10 insertions(+), 5 deletions(-)"  → summary row

    issue #59: "file.py | 5 +" must yield (files=1, added=5, deleted=0) —
    the histogram is authoritative, deletions are never invented.

    Returns: (files_changed, lines_added, lines_deleted)
    """
    if not diff_stat:
        return 0, 0, 0

    files = 0
    added = 0
    deleted = 0

    # Parse "N files changed, N insertions(+), N deletions(-)"
    summary_match = re.search(
        r"(\d+)\s+files?\s+changed.*?(\d+)\s+insertions?\(\+\).*?(\d+)\s+deletions?\(-\)",
        diff_stat
    )
    if summary_match:
        files = int(summary_match.group(1))
        added = int(summary_match.group(2))
        deleted = int(summary_match.group(3))
        return files, added, deleted

    # Parse individual file lines: "file.py | 10 +++--"
    file_rows = re.findall(r".+\|\s+(\d+)\s+([+-]+)", diff_stat)
    if file_rows:
        files = len(file_rows)
        for total_str, bar in file_rows:
            total = int(total_str)
            plus = bar.count("+")
            minus = bar.count("-")
            marks = plus + minus
            if marks == 0:
                # No histogram visible — treat the number as insertions.
                added += total
            else:
                # The histogram is a relative split of the changed lines.
                added += round(total * plus / marks)
                deleted += total - round(total * plus / marks)
        return files, added, deleted

    # Parse just file count: "3 files changed"
    file_count_match = re.search(r"(\d+)\s+files?\s+changed", diff_stat)
    if file_count_match:
        files = int(file_count_match.group(1))

    return files, added, deleted


def assess_scope(diff_stat: str, title: str, body: str) -> str:
    """Determine the scope of changes (e.g., 'tests + docs', 'core + auth')."""
    text = f"{diff_stat} {title} {body}".lower()
    scopes = []

    # Use word boundary matching to avoid false positives (e.g., "guide" contains "ui")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["test", "spec", "pytest", "jest", "unittest"]):
        scopes.append("tests")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["doc", "readme", "changelog", "guide", "tutorial"]):
        scopes.append("docs")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["ci", "cd", "workflow", "action", "pipeline", ".github"]):
        scopes.append("ci/cd")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["auth", "login", "session", "token", "oauth"]):
        scopes.append("auth")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["api", "endpoint", "route", "handler"]):
        scopes.append("api")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["ui", "frontend", "component", "style", "css"]):
        scopes.append("ui")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["db", "database", "migration", "schema", "sql"]):
        scopes.append("database")
    if any(re.search(r'\b' + kw + r'\b', text) for kw in ["config", "setting", "env", "environment"]):
        scopes.append("config")

    return " + ".join(scopes) if scopes else "general"


def detect_breaking_change(title: str, body: str) -> bool:
    """Detect if this PR is a breaking change."""
    text = f"{title} {body}".lower()
    return any(re.search(p, text) for p in _BREAKING_PATTERNS)


def detect_security_sensitive(title: str, body: str, diff_stat: str) -> bool:
    """Detect if this PR touches security-sensitive code."""
    text = f"{title} {body} {diff_stat}".lower()
    return any(re.search(p, text) for p in _SECURITY_PATTERNS)


def detect_dependency_changes(diff_stat: str) -> bool:
    """Detect if this PR changes dependency files."""
    if not diff_stat:
        return False
    return any(dep in diff_stat.lower() for dep in _DEPENDENCY_PATHS)


def assess_impact(
    title: str,
    body: str = "",
    diff_stat: str = "",
) -> ImpactAssessment:
    """Assess the impact of a PR."""
    files, added, deleted = parse_diff_stat(diff_stat)
    return ImpactAssessment(
        files_changed=files,
        lines_added=added,
        lines_deleted=deleted,
        scope=assess_scope(diff_stat, title, body),
        breaking_change=detect_breaking_change(title, body),
        security_sensitive=detect_security_sensitive(title, body, diff_stat),
        dependency_changes=detect_dependency_changes(diff_stat),
    )


# ============================================================
# Review complexity
# ============================================================

@dataclass
class ReviewComplexity:
    """How complex is this PR to review."""
    level: str = "medium"  # low / medium / high
    estimated_minutes: int = 15
    needs_domain_expert: bool = False


def assess_review_complexity(
    impact: ImpactAssessment,
    title: str = "",
    body: str = "",
) -> ReviewComplexity:
    """Estimate review complexity based on impact and content."""
    # Base complexity from file count
    if impact.files_changed <= 2 and impact.lines_added <= 50:
        level = "low"
        minutes = 5
    elif impact.files_changed <= 10 and impact.lines_added <= 200:
        level = "medium"
        minutes = 15
    else:
        level = "high"
        minutes = 30

    # Adjust for breaking changes
    if impact.breaking_change:
        level = "high"
        minutes = max(minutes, 30)

    # Adjust for security-sensitive
    if impact.security_sensitive:
        level = "high"
        minutes = max(minutes, 30)

    # Adjust for dependency changes
    if impact.dependency_changes:
        minutes = max(minutes, 15)

    # Check if domain expert is needed
    text = f"{title} {body}".lower()
    needs_expert = any(kw in text for kw in [
        "algorithm", "mathematical", "cryptographic", "protocol",
        "performance", "optimization", "benchmark", "profiling",
        "architecture", "design pattern", "refactor",
    ])

    return ReviewComplexity(
        level=level,
        estimated_minutes=minutes,
        needs_domain_expert=needs_expert,
    )
