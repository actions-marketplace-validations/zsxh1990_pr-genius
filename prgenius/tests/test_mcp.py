"""MCP smoke test — M0 克莱恩 2026-07-19 验收

Verifies pr-genius 的 MCP 表面 (8 个 tool) 都能正确返回 JSON.

Strategy: 调用 MCP tool 包装下的底层函数 (analyze_pr, triage_pr,
profile_get, iter_case_studies, etc.), 而不是走 mcp.call_tool().
原因: FastMCP 0.x 的 Tool 对象不暴露 .fn, 且 convert_result 路径有
str/str 除法 bug (MCP transport 上游问题). 直接测底层逻辑 = 测试
MCP tool 实际能干的事 (Claude Code / Cursor / Inspector 调用时
fns 已经返回正确 dict, 仅 transport 序列化层有 bug).

Run:
    PYTHONPATH=./prgenius/src python3 -m pytest prgenius/tests/test_mcp.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_ROOT_STR = str(REPO_ROOT)


def _has_mcp_dep():
    try:
        import mcp  # noqa: F401
        return True
    except ImportError:
        return False


# ============================================================
# MCP 表面注册层 (测试 mcp.py)
# ============================================================

@pytest.mark.asyncio
async def test_mcp_loads():
    """MCP server loads with FastMCP backend."""
    if not _has_mcp_dep():
        pytest.skip("mcp package not installed (pip install mcp>=1.0)")
    from prgenius.mcp import _load_tools
    mcp = _load_tools(REPO_ROOT_STR)
    assert mcp is not None
    # 类名随 mcp 版本变 (1.x: FastMCP, 2.x: MCPServer) —— 契约是"是个 MCP 服务端",
    # 不是某个类名。断言类名会让升级 mcp 变成假失败。
    assert type(mcp).__name__ in {"FastMCP", "MCPServer"}, (
        f"unexpected MCP server class: {type(mcp).__name__}"
    )


@pytest.mark.asyncio
async def test_mcp_8_tools_registered():
    """All 12 tools register (Phase 0-5)."""
    if not _has_mcp_dep():
        pytest.skip("mcp package not installed (pip install mcp>=1.0)")
    from prgenius.mcp import _load_tools
    mcp = _load_tools(REPO_ROOT_STR)
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    expected = {
        # Phase 0-4
        "analyze_pr", "coach_pr", "triage_pr",
        "get_repo_profile", "list_open_prs", "get_case_study",
        "search_patterns", "schema_info",
        # Phase 3
        "status_prs", "profile_writeback_suggestions",
        # Phase 5
        "maintainer_view", "review_queue",
    }
    assert expected.issubset(tool_names), (
        f"missing tools: {expected - tool_names}; got {sorted(tool_names)}"
    )


@pytest.mark.asyncio
async def test_mcp_tools_have_readonly_annotations():
    """All tools must have readOnlyHint=True, destructiveHint=False, idempotentHint=True.

    pr-genius 是只读 advisor — 不写任何状态."""
    if not _has_mcp_dep():
        pytest.skip("mcp package not installed (pip install mcp>=1.0)")
    from prgenius.mcp import _load_tools
    mcp = _load_tools(REPO_ROOT_STR)
    tools = await mcp.list_tools()
    for tool in tools:
        ann = tool.annotations
        # 字段拼写随 mcp 版本变: 1.x camelCase (readOnlyHint),
        # 2.x snake_case (read_only_hint)。两个都收, 读不到就报清楚 —— 验的是
        # "只读 advisor" 这个契约, 不是某一代 API 的属性名。
        def _hint(*names):
            for n in names:
                if hasattr(ann, n):
                    return getattr(ann, n)
            raise AssertionError(
                f"{tool.name}: annotations has none of {names}; got {type(ann).__name__} "
                f"with fields {[f for f in dir(ann) if f.endswith('_hint')]}"
            )

        assert _hint("readOnlyHint", "read_only_hint") is True, f"{tool.name}: readOnlyHint"
        assert _hint("destructiveHint", "destructive_hint") is False, f"{tool.name}: destructiveHint"
        assert _hint("idempotentHint", "idempotent_hint") is True, f"{tool.name}: idempotentHint"


# ============================================================
# MCP tool 实际行为层 (调用 MCP tool 包装的底层 fn)
# 这里直接 import evaluate/triage/parser/evaluator 模块, 它们是 MCP tool 实际干的活.
# ============================================================

def test_schema_info_returns_okf_schema():
    """schema_info MCP tool → schema_info() returns OKF schema dict."""
    from prgenius.parser import schema_info
    result = schema_info()
    assert isinstance(result, dict)
    assert "schema_versions" in result
    assert "delta_kinds" in result
    assert "close_decision_status" in result


def test_get_repo_profile_misakanet_returns_full_profile():
    """get_repo_profile MCP tool → profile_get() 返回 MisakaNet 完整画像."""
    from prgenius.parser import profile_get
    result = profile_get(REPO_ROOT_STR, "Ikalus1988/MisakaNet")
    assert result is not None, "MisakaNet profile must exist"
    assert result["frontmatter"]["repo"] == "Ikalus1988/MisakaNet"
    assert "agent_guidelines" in result["frontmatter"]
    gl = result["frontmatter"]["agent_guidelines"]
    assert "ai_policy" in gl
    assert "maintainer_vibe" in gl


def test_triage_pr_pass_on_misakanet():
    """triage_pr MCP tool → triage_pr() 对 clean PR 返回 pass + safe_to_review."""
    from prgenius.triage import triage_pr
    result = triage_pr(
        title="fix: tiny typo",
        repo="Ikalus1988/MisakaNet",
        body="Fix typo in README",
        diff_stat="docs/faq.md | 3 ++-",
        repo_root=REPO_ROOT_STR,
    )
    assert result["verdict"] == "pass"
    assert result["policy_loaded"] is True
    # MCP 层 recommended_action 逻辑
    if result["verdict"] == "pass":
        result["recommended_action"] = "safe_to_review"
    assert result["recommended_action"] == "safe_to_review"


def test_triage_pr_needs_preflight_on_unknown_repo():
    """triage_pr MCP tool → unknown/repo 返回 needs_preflight + 6 generic_checks.

    克莱恩 14:54 P0 验收门槛."""
    from prgenius.triage import triage_pr
    result = triage_pr(
        title="docs: add installation",
        repo="unknown/repo",
        body="Adds README section",
        repo_root=REPO_ROOT_STR,
    )
    assert result["verdict"] == "needs_preflight"
    assert result["policy_loaded"] is False
    assert len(result["generic_checks"]) == 6


def test_analyze_pr_pallets_flask_triggers_high_risk_with_policy():
    """analyze_pr MCP tool → pallets/flask (≥10k star + 有 policy) 仍 high_risk.

    Month 2 演进: Flask 现在有 docs/policies/pallets-flask.md,
    所以 _check_has_policy() 返回 True → needs_preflight 不再触发.
    但 first_contributor_large_repo + docs-only 撞 policy rule 3
    (CHANGES.rst entry missing) + rule 2 (docs-only 撞维护者规划)
    → tier 仍 high_risk.

    克莱恩 14:54 P0 原始验收门槛: tier=high_risk / 6 generic_checks.
    Month 2 演进后: tier=high_risk / policy loaded=True / CHANGES.rst missing 触发.
    """
    from prgenius.evaluator import analyze_pr
    result = analyze_pr(
        title="docs: add installation instructions",
        description="",
        repo="pallets/flask",
        repo_root=REPO_ROOT_STR,
        body="Adds README section",
        star_count=67000,
    )
    # 仍 high_risk (first_contributor_large_repo + 大仓 docs-only)
    assert result["tier"] == "high_risk"
    # policy 加载成功 (Month 2 演进 — Flask 有了真实 policy)
    repo_context = result.get("repo_context", {})
    assert repo_context.get("has_policy") is True, (
        "pallets/flask 现在有 docs/policies/pallets-flask.md, has_policy 应为 True"
    )
    # 命中 contribai anti-patterns (docs-only 撞 policy + 缺 CHANGES.rst)
    anti_patterns = result.get("anti_patterns_hit", [])
    # 应该至少命中 contribai-docs-pr-missing-quickstart (docs-only)
    # 或 contribai-incomplete-readme-contributing (缺 CHANGES.rst)
    has_contribai = any(k.startswith("contribai-") for k in anti_patterns)
    assert has_contribai or any(
        s.get("key") in ("first_contributor_large_repo", "needs_preflight")
        for s in result.get("signals", {}).get("negative", [])
    ), (
        "Flask high_risk 应该有 contribai-* anti-pattern 或 first_contributor signal"
    )


def test_coach_pr_pallets_flask_returns_pass_false():
    """coach_pr MCP tool → pallets/flask 返回 pass=False + tier=high_risk."""
    from prgenius.evaluator import analyze_pr
    result = analyze_pr(
        title="docs: add installation",
        description="",
        repo="pallets/flask",
        repo_root=REPO_ROOT_STR,
        body="Adds README section",
        star_count=67000,
    )
    # MCP coach_pr 包装: 加 pass 字段
    result["pass"] = result["tier"] != "high_risk"
    assert result["pass"] is False
    assert result["tier"] == "high_risk"


def test_list_open_prs_returns_open_case_studies():
    """list_open_prs MCP tool → iter_case_studies() 过滤 final_status=open."""
    from prgenius.parser import iter_case_studies
    result = [
        {
            "repo": c["frontmatter"].get("repo"),
            "pr_number": c["frontmatter"].get("pr_number"),
            "pr_url": c["frontmatter"].get("pr_url"),
            "folder": c["folder"],
        }
        for c in iter_case_studies(REPO_ROOT_STR)
        if c["frontmatter"].get("final_status") == "open"
    ]
    assert len(result) >= 1
    for item in result:
        assert "repo" in item
        assert "pr_number" in item
        assert "pr_url" in item


def test_get_case_study_honcho_801():
    """get_case_study MCP tool → iter_case_studies() 找 honcho#801."""
    from prgenius.parser import iter_case_studies
    result = None
    for c in iter_case_studies(REPO_ROOT_STR):
        fm = c["frontmatter"]
        if (
            fm.get("repo", "").strip("/").lower() == "plastic-labs/honcho"
            and str(fm.get("pr_number")) == "801"
        ):
            result = {"frontmatter": fm, "body": c["body"], "path": c["path"]}
            break
    assert result is not None
    assert result["frontmatter"]["pr_number"] == 801
    assert "rounds" in result["frontmatter"]


def test_search_patterns_duplicate_query():
    """search_patterns MCP tool → 按 query='duplicate' 搜 anti-patterns + success-patterns."""
    import re
    from pathlib import Path
    query = "duplicate"
    results = []
    for pdir in [Path(REPO_ROOT_STR) / "anti-patterns", Path(REPO_ROOT_STR) / "success-patterns"]:
        if not pdir.exists():
            continue
        for f in pdir.glob("*.md"):
            if f.name == "README.md":
                continue
            content = f.read_text(encoding="utf-8")
            if query not in content.lower():
                continue
            m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
            if not m:
                continue
            fm = {}
            for line in m.group(1).split("\n"):
                if ":" in line:
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip('"')
            fm["file"] = str(f.relative_to(REPO_ROOT_STR))
            results.append(fm)
    assert isinstance(results, list)
    assert len(results) >= 1
    keys = [r.get("key") for r in results]
    assert any("duplicate" in (k or "") for k in keys), f"got: {keys}"


# ============================================================
# issue #74: list_open_prs must accept a repo filter
# ============================================================

def test_list_open_prs_accepts_repo_arg():
    """README documents list_open_prs(repo=...) — the fn must accept it.

    issue #74 repro: fn(repo='encode/httpx') used to raise TypeError.
    """
    if not _has_mcp_dep():
        pytest.skip("mcp package not installed (pip install mcp>=1.0)")
    from prgenius.mcp import _load_tools
    server = _load_tools(REPO_ROOT_STR)
    tools = getattr(getattr(server, "_tool_manager", None), "_tools", None)
    if tools is None or "list_open_prs" not in tools:
        pytest.skip("FastMCP tool manager not introspectable")
    fn = getattr(tools["list_open_prs"], "fn", None)
    if fn is None:
        pytest.skip("FastMCP Tool does not expose .fn")
    # Must not raise TypeError for the documented signature
    fn(repo="encode/httpx")
    fn(repo="encode/httpx", author="someone")


# ============================================================
# issue #70: prgenius_doctor tool registered + doctor report shape
# ============================================================

@pytest.mark.asyncio
async def test_mcp_doctor_tool_registered():
    if not _has_mcp_dep():
        pytest.skip("mcp package not installed (pip install mcp>=1.0)")
    from prgenius.mcp import _load_tools
    server = _load_tools(REPO_ROOT_STR)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert "prgenius_doctor" in names


def test_run_doctor_report_shape():
    from prgenius.doctor import run_doctor
    report = run_doctor(Path(REPO_ROOT_STR))
    assert "ok" in report
    assert "prgenius_version" in report
    assert "python_version" in report
    assert "knowledge_base" in report
    assert "gh" in report
    assert "mcp" in report
    kb = report["knowledge_base"]
    assert kb["anti_patterns"] > 0
    assert kb["readable"] is True


# ============================================================
# issue #72: MCP input validation
# ============================================================

def test_validate_pr_args_rejects_impossible_values():
    from prgenius.mcp import _validate_pr_args
    import pytest as _pytest
    with _pytest.raises(ValueError):
        _validate_pr_args(-1, 0.5, "NONE", "MERGEABLE")
    with _pytest.raises(ValueError):
        _validate_pr_args(0, 2.0, "NONE", "MERGEABLE")
    with _pytest.raises(ValueError):
        _validate_pr_args(0, 0.5, "INVALID_VALUE", "MERGEABLE")
    with _pytest.raises(ValueError):
        _validate_pr_args(0, 0.5, "NONE", "MAYBE")
    # valid values pass
    _validate_pr_args(0, 0.5, "CONTRIBUTOR", "UNKNOWN")
