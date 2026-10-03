---
type: Knowledge Bundle
title: PR Genius — Pre-submission PR Advisor
description: Evidence-backed PR contribution advisor for large open-source projects
version: 1.9.1
created: 2026-07-01
updated: 2026-09-05
author: zsxh1990
conforms_to: OKF v0.1 (Sudhakaran88/okf-conformance) + agent_guidelines extension
---
mcp-name: io.github.zsxh1990/pr-genius

# PR Genius — The advisor that knows which PRs get closed

> **943 loaded patterns across 67 repos.**
> Clone → paste MCP config → ask "Should I open this PR to encode/httpx?"

[![CI](https://github.com/zsxh1990/pr-genius/actions/workflows/validate.yml/badge.svg)](https://github.com/zsxh1990/pr-genius/actions/workflows/validate.yml)
[![PyPI](https://img.shields.io/pypi/v/prgenius-core)](https://pypi.org/project/prgenius-core/)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/zsxh1990/pr-genius?style=flat&color=blueviolet)](https://github.com/zsxh1990/pr-genius/blob/main/LICENSE)
[![Glama score](https://glama.ai/mcp/servers/zsxh1990/pr-genius/badges/score.svg)](https://glama.ai/mcp/servers/zsxh1990/pr-genius)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-PR%20Genius-blue?logo=github)](https://github.com/marketplace/actions/pr-genius)
[![DSH Plugin](https://img.shields.io/badge/DSH--plugin-pr--genius-blueviolet)](docs/dsh-integration.md)

---

## 🎯 What is PR Genius?

PR Genius is **not** a PR dashboard. It's an **Outbound PR CRM** for professional OSS contributors and AI agents:

> Manage PRs you've *submitted to other repos* — when to fix CI, rebase, wait, ping, or abandon.

PR Genius is also a **DSH (Cordis) plugin** that slots into the DeepSeek Harness chat sidebar, advisor panel, session tab, and `/prgenius` slash-command. See [🧩 DSH Plugin](#-dsh-plugin) below.

| Capability | `gh` CLI | PR Genius |
|---|---|---|
| Cross-repo PR list | ✅ | ✅ |
| Status classification | ❌ | ✅ (9 states) |
| Stale detection | ❌ | ✅ |
| Action suggestions | ❌ | ✅ |
| Repo-specific policy | ❌ | ✅ |
| Snapshot & transitions | ❌ | ✅ |

**Status heartbeat** runs daily via cron, auto-detecting:
- 🔴 `NEEDS_REBASE` / `CI_FAILING` — fix immediately
- 🟡 `STALE_REVIEW` — ping after threshold
- 🟡 `STALE_NO_REVIEW` — consider abandoning
- 🟢 `CLEAN` / `WAITING` — continue waiting

---

## 🛡️ Why PR Genius?

**PR Genius doesn't write PRs for you. It knows which PRs get closed.**

| Capability | LLM directly | Scraper Agent | PR Genius |
|------------|-------------|---------------|-----------|
| Knowledge source | Training data | Real-time scrape | 943 structured patterns |
| Repo understanding | Generic | Surface data (stars) | 17-field agent_guidelines |
| Failure patterns | Unknown | Unknown | 251 anti-patterns |
| Success patterns | Unknown | Unknown | 692 success patterns |
| Maintainer preference | Guess | Recent PRs | Structured policy files |
| Merge probability | Can't estimate | Can't estimate | Based on repo merge rate + signals |

**Real cases (PR Genius helped avoid these rejections):**

| PR | Repo | What happened | PR Genius would have flagged |
|----|------|---------------|------------------------------|
| #491 | MisakaNet | "Destructive README rewrite" — closed | `breaking_change_no_compat` anti-pattern |
| #47434 | huggingface/transformers | "We'll handle internally" — closed | `maintainer_internal_handling` anti-pattern |
| #10393 | awesome-mcp-servers | Missing Glama badge — auto-flagged | `awesome-mcp-servers-glama-badge-required` anti-pattern |
| #282 | punkpeye/fastmcp | +271 lines, first PR — closed without review | `punkpeye-fastmcp-282-too-large` anti-pattern |
| — | contribai | Issue claim without due diligence — auto-closed | `contribai-issue-claim-no-due-diligence` anti-pattern |
| #2902 | soxoj/maigret | CI failure (tag `dev` not recognized) — fixed, merged | `maigret-tag-validation` pattern |
| — | Ikalus1988/MisakaNet | Claimed issue without due diligence — auto-closed | `contribai-issue-claim-no-due-diligence` anti-pattern |
| #928 | Ikalus1988/MisakaNet | Voice hooks PR — scope creep, closed | `ikalus1998-misakanet-928` lesson |
| #936 | Ikalus1988/MisakaNet | Global disable switch — incomplete impl | `ikalus1998-misakanet-936` lesson |
| #938 | Ikalus1988/MisakaNet | Anti-patterns reference doc — premature PR | `ikalus1998-misakanet-938` lesson |
| #965 | Ikalus1988/MisakaNet | README numbers sync — stale data | `ikalus1998-misakanet-965` lesson |
| #248 | punkpeye/awesome-mcp-devtools | Listing PR — still pending, no maintainer response | `punkpeye-awesome-mcp-devtools-248-pending` case study |

## 🚀 Quick Start

```bash
pip install prgenius-core

# Analyze PR
python3 -m prgenius analyze "feat: add feature" --repo org/repo --body "Fixes #123"

# Coach (pass/fail)
python3 -m prgenius coach "feat: add feature" --repo org/repo

# Triage (policy check)
python3 -m prgenius triage "docs: typo" --repo org/repo --diff-stat "docs/faq.md | 3 ++-"

# Status heartbeat (outbound PR monitoring)
python3 -m prgenius status --author zsxh1990
python3 -m prgenius status --author zsxh1990 --format json --save-snapshot

# Profile writeback suggestions (dry-run)
python3 -m prgenius profile writeback --author zsxh1990
```

## 🤖 GitHub Action

Use PR Genius as a GitHub Action in any repo:

```yaml
# .github/workflows/pr-genius.yml
name: PR Genius Check
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  issues: write   # required when comment_mode != never (post/update PR comment)

jobs:
  pr-genius:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: zsxh1990/pr-genius@v1
        id: pr-genius
        with:
          title: ${{ github.event.pull_request.title }}
          repo: ${{ github.repository }}
          body: ${{ github.event.pull_request.body }}
          pr_number: ${{ github.event.pull_request.number }}
          comment_mode: always   # never | high_risk | always — post full analysis as a PR comment
```

`comment_mode` controls whether the full analysis is posted as a visible PR
comment (mirrors pr-agent's `/review`):

- `never` — do not post (default when unset and `comment_on_high_risk` is false)
- `high_risk` — post only when the risk tier is `high_risk`
- `always` — post on every run; existing comments are updated in place (no spam)

> **Legacy**: `comment_on_high_risk: true` is still supported and behaves like
> `comment_mode: high_risk`.

### Version Auto-Update

- **`@v1`** — Always points to the latest `v1.x.x` release (recommended)
- **`@v1.9.1`** — Pinned to specific version (for reproducibility)
- **`@main`** — Latest development version (not recommended for production)

The `v1` tag is automatically updated when a new version is published to PyPI.

### Docker Image (Alternative)

Use PR Genius as a Docker container via GitHub Container Registry:

```yaml
# .github/workflows/pr-genius-docker.yml
name: PR Genius Check (Docker)
on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write

jobs:
  pr-genius:
    runs-on: ubuntu-latest
    steps:
      - name: Run PR Genius
        uses: docker://ghcr.io/zsxh1990/pr-genius:latest
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          args: coach "${{ github.event.pull_request.title }}" --repo ${{ github.repository }} --format json
```

**Docker Image Tags:**
- `ghcr.io/zsxh1990/pr-genius:latest` — Latest release
- `ghcr.io/zsxh1990/pr-genius:1.9.1` — Specific version
- `ghcr.io/zsxh1990/pr-genius:1.9` — Minor version
- `ghcr.io/zsxh1990/pr-genius:1` — Major version (auto-updated)

**Auto-update with Dependabot:**

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
```

## 🤖 MCP Configuration

```json
{
  "mcpServers": {
    "pr-genius": {
      "command": "python",
      "args": ["-m", "prgenius", "mcp", "serve"]
    }
  }
}
```

Docker: `docker run --rm -i ghcr.io/zsxh1990/pr-genius:1.9.1`

### 13 MCP Tools

| Tool | Purpose | Required Args |
|------|---------|---------------|
| `analyze_pr` | Merge probability + optimization path + 3-tier risk | `title`, `repo` |
| `coach_pr` | Go/no-go decision (pass/fail) | `title`, `repo` |
| `triage_pr` | Maintainer policy check (9 rules) | `title`, `repo` |
| `get_repo_profile` | Repo profile (17 fields) | `repo` |
| `list_open_prs` | Local open **case-study records** (not live GitHub PRs; live ones → `status_prs`); optional `repo`/`author` filters | *(none)* |
| `get_case_study` | PR case study details | `case_id` |
| `search_patterns` | Anti-pattern/success-pattern search | `query` |
| `schema_info` | OKF schema versions | *(none)* |
| `status_prs` | Outbound PR status heartbeat | `author` |
| `profile_writeback_suggestions` | Profile update suggestions (dry-run) | `author` |
| `maintainer_view` | Maintainer-side PR view (5 actions: `READY_FOR_REVIEW`, `WAIT_FOR_AUTHOR`, `CLOSE_DUPLICATE`, `CLOSE_STALE_OR_RISKY`, `HOLD_MAINTAINER_DECISION`) | `repo` |
| `contributor_view` | Contributor readiness decision (5 actions: `READY_TO_SUBMIT`, `FIX_BEFORE_SUBMIT`, `NEEDS_DISCUSSION`, `IMPROVE_CHANCE`, `ASK_MAINTAINER`) | `repo` |
| `review_queue` | Prioritized review queue | `repo` |
| `prgenius_doctor` | Install/data/MCP self-test — run this when analyze returns nothing | *(none)* |

### Tool Parameter Notes

- **`title`** (required for `analyze_pr`, `coach_pr`, `triage_pr`): The PR title, e.g. `"fix: timeout in connection pool"`
- **`repo`** (required for most tools): Repository in `owner/name` format, e.g. `"encode/httpx"`
- **`pr_description`** (optional): Additional PR body text for deeper analysis
- **`query`** (required for `search_patterns`): Search keywords, e.g. `"connection timeout"`
- **`diff_stat`** (optional for `analyze_pr`, `coach_pr`): `git diff --stat` output — populates the `impact`/`review` fields (both are `null` without it) and is the authoritative PR-size signal
- **`star_count`** ≥ 0, **`repo_merge_rate`** in `[0.0, 1.0]`, **`author_association`** in `NONE/CONTRIBUTOR/COLLABORATOR/MEMBER/OWNER`, **`mergeable`** in `MERGEABLE/CONFLICTING/UNKNOWN` — invalid values are rejected instead of silently producing meaningless output

## 🧩 DSH Plugin

PR Genius ships as a [DSH (Cordis)](https://github.com/deepseek-ai/dsh) plugin (v2.0.0+). The TypeScript layer is a thin shell — analysis is delegated to the existing Python MCP engine; the plugin adds four UI surfaces on top.

### Install

```bash
dsh plugin add pr-genius
```

Or apply the one-line patch in [`cordis.patch.yml`](cordis.patch.yml). Full guide: [`docs/dsh-integration.md`](docs/dsh-integration.md).

### Four surfaces

| Surface | Slot | What it does |
|---------|------|-------------|
| **Dashboard** (sidebar) | `ui-sidebar` | PR Intelligence Dashboard — cross-repo status at a glance |
| **Advisor tab** | `conversation.view` | Session-level advisor for the current conversation |
| **Advisor panel** | `ui-sidebar` (panel mode) | Same advisor as a right-hand panel |
| **`/prgenius`** | `ctx.command` | Slash-command for inline PR checks |

Maintainer mode is the same four surfaces on a different projection (5-action decision: `READY_FOR_REVIEW`, `WAIT_FOR_AUTHOR`, `CLOSE_DUPLICATE`, `CLOSE_STALE_OR_RISKY`, `HOLD_MAINTAINER_DECISION`).

### Configuration

All tunables are Schemastery-validated and settable from `cordis.yml` — no code changes needed. Invalid values fail at load time naming the field. See [`src/config.ts`](src/config.ts) for the full schema (12 fields: MCP transport/endpoint/timeout, sidebar default view, maintainer confidence threshold, stale-days, locale, risk filter, etc.).

### Relationship to v1.x

The DSH plugin wraps the same Python analysis engine (`prgenius/src/prgenius/mcp.py`). v1.x CLI and MCP server continue to work unchanged. The plugin adds UI surfaces and config management; it does not fork the analysis logic.

> **Honesty note**: The DSH plugin has been verified for TypeScript compilation, unit tests, and static contract conformance (`scripts/check_dsh_plugin_contract.py`, 27/27 checks). It has **not** been run against a live DSH runtime — rendering and runtime behavior require DSH verification. See [`docs/compatibility.md`](docs/compatibility.md) for the version matrix (every cell marked unrun) and [`docs/maturity-self-assessment.md`](docs/maturity-self-assessment.md) for the completeness scorecard.

## 📊 Data Scale

> Numbers below are measured from the repo at the current commit. Run `python3 -c "from prgenius.parser import iter_profiles, iter_case_studies; from prgenius.evaluator import load_anti_patterns, load_success_patterns; print(len(list(iter_profiles('.'))), len(list(iter_case_studies('.'))), len(load_anti_patterns('.')), len(load_success_patterns('.')))"` to verify.

| Dimension | Count |
|-----------|-------|
| Repo profiles | 67 |
| Case studies | 53 |
| Success patterns | 692 (436 .md + 256 .json) |
| Anti-patterns | 251 (61 .md + 190 .json) |
| Total patterns | 943 (all loaded) |
| Covered repos | 67 (uv, react, kubernetes, transformers, httpx, etc.) |

## 🤖 Robots / Agents

1. **[docs/index.md](docs/index.md)** — file map
2. **[AGENT_GUIDELINES_SCHEMA.md](AGENT_GUIDELINES_SCHEMA.md)** — agent_guidelines schema
3. **[ROUNDS_SCHEMA.md](ROUNDS_SCHEMA.md)** — rounds schema
4. **[BLACKLIST.md](BLACKLIST.md)** — repos we don't track

## 📖 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). AI-assisted PRs welcome.

## 🤝 Community

- 📋 [Code of Conduct](CODE_OF_CONDUCT.md)
- 🔒 [Security Policy](SECURITY.md)
- 🐛 [Issue Tracker](../../issues)
- 📜 [Changelog](CHANGELOG.md)

## 中文文档

中文版 README：[README.zh-CN.md](README.zh-CN.md)

## Citation

```bibtex
@misc{pr-genius-2026,
  title  = {PR Genius — Evidence-backed PR Contribution Advisor},
  author = {zsxh1990},
  year   = {2026},
  url    = {https://github.com/zsxh1990/pr-genius}
}
```
<!-- action bot verification test -->
