"""prgenius doctor — install / data / integration self-test (issue #70).

Answers the "why is my analyze returning nothing?" questions in one shot:

- Python / package version
- knowledge-base readability (anti-patterns, success-patterns, profiles,
  case studies, policies) and the repo_root actually resolved
- gh CLI availability
- MCP server surface (can the tools register locally)
- sample analyze against a known profile
- data-coverage warnings (anti-patterns without trigger_keywords,
  success-patterns not consulted by the scorer)

Output contract: `run_doctor()` returns a machine-readable dict;
`format_doctor_text()` renders the human-readable twin. The CLI
(`prgenius doctor [--format json]`) and the MCP tool `prgenius_doctor`
both wrap the same dict, so agents and humans see the same facts.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from . import __version__

# A well-known profile used as the sample target (issue #70 sample block).
SAMPLE_REPO = "encode/httpx"
SAMPLE_TITLE = "feat: add new feature"


def _count_anti_patterns(repo_root: Path) -> tuple[int, int, int]:
    """Return (total, with_trigger_keywords, json_only)."""
    from .evaluator import load_anti_patterns

    patterns = load_anti_patterns(repo_root)
    total = len(patterns)
    json_only = sum(1 for p in patterns.values() if p.get("_is_json_pattern"))
    with_kw = sum(
        1
        for p in patterns.values()
        if not p.get("_is_json_pattern") and p.get("trigger_keywords")
    )
    return total, with_kw, json_only


def _count_success_patterns(repo_root: Path) -> int:
    from .evaluator import load_success_patterns

    return len(load_success_patterns(repo_root))


def _count_dirs(repo_root: Path, name: str) -> int:
    d = repo_root / name
    if not d.is_dir():
        return 0
    return sum(1 for p in d.iterdir() if p.is_dir())


def _count_case_studies(repo_root: Path) -> int:
    from .parser import iter_case_studies

    return sum(1 for _ in iter_case_studies(repo_root))


def _check_gh() -> dict:
    path = shutil.which("gh")
    info: dict = {"available": path is not None, "path": path, "version": None, "error": None}
    if not path:
        info["error"] = "gh CLI not found on PATH"
        return info
    try:
        proc = subprocess.run(
            [path, "--version"], capture_output=True, text=True, timeout=10
        )
        if proc.returncode == 0:
            info["version"] = (proc.stdout or "").splitlines()[0].strip()
        else:
            info["error"] = f"gh --version exited {proc.returncode}"
    except (OSError, subprocess.TimeoutExpired) as e:
        info["error"] = f"gh --version failed: {e}"
    return info


def _check_mcp(repo_root: Path) -> dict:
    """Verify the MCP surface can load and register tools locally.

    This is the pre-flight an agent needs before wiring pr-genius into an
    MCP host: if `_load_tools()` raises or registers nothing, every MCP
    call will fail. It does not open a network connection (the server is
    stdio-based), so 'connectable' here means 'the stdio shell can start
    with these tools registered'.
    """
    info: dict = {
        "package_installed": False,
        "tools_registered": 0,
        "tools": [],
        "ok": False,
        "error": None,
    }
    try:
        import mcp  # noqa: F401

        info["package_installed"] = True
    except ImportError as e:
        info["error"] = f"mcp package not installed: {e}"
        return info

    try:
        from .mcp import _load_tools

        server = _load_tools(str(repo_root))
        tools = getattr(getattr(server, "_tool_manager", None), "_tools", None)
        if tools is None:
            # Newer FastMCP: fall back to the public list API shape.
            info["error"] = "FastMCP tool manager not introspectable"
            return info
        info["tools_registered"] = len(tools)
        info["tools"] = sorted(tools.keys())
        info["ok"] = len(tools) > 0
        if not info["ok"]:
            info["error"] = "no tools registered"
    except Exception as e:  # noqa: BLE001 — doctor must report, never crash
        info["error"] = f"MCP tool load failed: {type(e).__name__}: {e}"
    return info


def _sample_block(repo_root: Path) -> dict:
    from .evaluator import analyze_pr
    from .parser import profile_get

    sample: dict = {
        "repo": SAMPLE_REPO,
        "profile_loaded": False,
        "profile": {},
        "analyze_title": SAMPLE_TITLE,
        "analyze": {},
    }
    profile = profile_get(repo_root, SAMPLE_REPO)
    if profile:
        fm = profile.get("frontmatter", {})
        gl = fm.get("agent_guidelines", {})
        sample["profile_loaded"] = True
        sample["profile"] = {
            "star": fm.get("star"),
            "merge_rate": gl.get("external_merge_rate_30", gl.get("external_merge_rate")),
        }
    try:
        result = analyze_pr(SAMPLE_TITLE, "", SAMPLE_REPO, repo_root)
        sample["analyze"] = {
            "tier": result.get("tier"),
            "pr_size": result.get("pr_size"),
            "positive_signals": len(result.get("signals", {}).get("positive", [])),
            "negative_signals": len(result.get("signals", {}).get("negative", [])),
            "anti_patterns_hit": len(result.get("anti_patterns_hit", [])),
        }
    except Exception as e:  # noqa: BLE001
        sample["analyze"] = {"error": f"{type(e).__name__}: {e}"}
    return sample


def run_doctor(repo_root: Optional[Path] = None) -> dict:
    """Run all self-checks and return a machine-readable report."""
    from .utils import get_repo_root

    root = Path(repo_root) if repo_root else get_repo_root()

    anti_total, anti_with_kw, anti_json = _count_anti_patterns(root)
    success_total = _count_success_patterns(root)

    kb = {
        "repo_root": str(root),
        "readable": (root / "anti-patterns").is_dir(),
        "anti_patterns": anti_total,
        "anti_patterns_with_trigger_keywords": anti_with_kw,
        "anti_patterns_json_only": anti_json,
        "success_patterns": success_total,
        "profiles": _count_dirs(root, "profiles"),
        "case_studies": _count_case_studies(root),
        "policies": 0,
    }
    policy_dir = root / "docs" / "policies"
    if policy_dir.is_dir():
        kb["policies"] = sum(1 for p in policy_dir.glob("*.md"))

    warnings: list[str] = []
    if not kb["readable"]:
        warnings.append(f"knowledge base not readable at {root} (anti-patterns/ missing)")
    missing_kw = anti_total - anti_with_kw - anti_json
    if missing_kw > 0:
        warnings.append(
            f"{missing_kw}/{anti_total} anti-patterns have no trigger_keywords "
            "(they can never match a PR)"
        )
    if success_total > 0:
        warnings.append(
            f"{success_total}/{success_total} success-patterns are not consulted by the scorer"
        )

    gh = _check_gh()
    if not gh["available"]:
        warnings.append("gh CLI not available — `prgenius status` / live PR checks will not work")

    mcp_info = _check_mcp(root)
    if not mcp_info["ok"]:
        warnings.append(f"MCP surface not usable: {mcp_info.get('error')}")

    report = {
        "ok": kb["readable"] and mcp_info["ok"],
        "prgenius_version": __version__,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "knowledge_base": kb,
        "gh": gh,
        "mcp": mcp_info,
        "sample": _sample_block(root),
        "warnings": warnings,
    }
    return report


def format_doctor_text(report: dict) -> str:
    """Render the human-readable twin of run_doctor()'s dict."""
    kb = report.get("knowledge_base", {})
    gh = report.get("gh", {})
    mcp_info = report.get("mcp", {})
    sample = report.get("sample", {})

    lines = [
        f"prgenius {report.get('prgenius_version')}",
        f"python:      {report.get('python_version')} ({report.get('python_executable')})",
        f"platform:    {report.get('platform')}",
        f"repo_root:   {kb.get('repo_root')}",
        f"knowledge:   {'readable' if kb.get('readable') else 'NOT READABLE'} — "
        f"{kb.get('anti_patterns')} anti-patterns, "
        f"{kb.get('success_patterns')} success-patterns, "
        f"{kb.get('profiles')} profiles, "
        f"{kb.get('case_studies')} case studies, "
        f"{kb.get('policies')} policies",
        f"gh:          {'✓ ' + (gh.get('version') or 'available') if gh.get('available') else '✗ ' + (gh.get('error') or 'not found')}",
        f"mcp:         {'✓ ' + str(mcp_info.get('tools_registered')) + ' tools' if mcp_info.get('ok') else '✗ ' + (mcp_info.get('error') or 'not ok')}",
    ]

    prof = sample.get("profile", {})
    lines.append(f"sample repo: {sample.get('repo')}")
    if sample.get("profile_loaded"):
        lines.append(f"  profile:   ✓ loaded (star={prof.get('star')}, merge_rate={prof.get('merge_rate')})")
    else:
        lines.append("  profile:   ✗ not found")
    an = sample.get("analyze", {})
    if "error" in an:
        lines.append(f"  analyze:   ✗ {an['error']}")
    elif an:
        lines.append(
            f"  analyze:   \"{sample.get('analyze_title')}\" → tier={an.get('tier')}, "
            f"pr_size={an.get('pr_size')}, "
            f"{an.get('positive_signals')} pos / {an.get('negative_signals')} neg "
            f"({an.get('anti_patterns_hit')} anti-pattern hits)"
        )

    warnings = report.get("warnings", [])
    if warnings:
        lines.append("warnings:")
        lines.extend(f"  - {w}" for w in warnings)
    else:
        lines.append("warnings:    none")

    lines.append(f"overall:     {'OK' if report.get('ok') else 'NOT OK'}")
    return "\n".join(lines)
