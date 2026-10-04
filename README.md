---
type: Knowledge Bundle
title: PR Genius — Pre-submission PR Advisor
description: Evidence-backed PR contribution advisor for large open-source projects
version: 2.1.5
created: 2026-07-01
updated: 2026-09-05
author: zsxh1990
conforms_to: OKF v0.1 (Sudhakaran88/okf-conformance) + agent_guidelines extension
---
mcp-name: io.github.zsxh1990/pr-genius

# PR Genius — The advisor that knows which PRs get closed

> **943 loaded patterns across 67 repos.**
> (Trigger coverage — how often rules fire on real PRs — is measured separately by
> `scripts/measure_pattern_coverage.py`, issue #66. There is no "quality pass rate"
> claim here: it is not measurable for the current set, so it is not asserted.)
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

PR Genius is also a **DSH (Cordis) plugin** that slots into the DeepSeek Harness chat sidebar, advisor panel, session tab, preferences section, and `/prgenius` slash-command. See [🧩 DSH Plugin](#-dsh-plugin) below.

| Capability | `gh` CLI | PR Genius |
|---|---|---|
| Cross-repo PR list | ✅ | ✅ |
| Status classification | ❌ | ✅ (9 states) |
| Stale detection | ❌ | ✅ |
| Action suggestions | ❌ | ✅ |
| Common OSS PR policy | ❌ | ✅ |
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
| Success patterns | Unknown | Unknown | 692 patterns — retrieval/reference only, not wired into scoring (issue #69) |
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
# Code only. Add [mcp] if you want the MCP server.
pip install prgenius-core
pip install "prgenius-core[mcp]"     # + the MCP engine

# The knowledge bundle is NOT in the wheel — it lives in this git repo.
# Clone it and point the CLI at it (or export PRGENIUS_REPO_ROOT=<clone>).
git clone https://github.com/zsxh1990/pr-genius.git
export PRGENIUS_REPO_ROOT="$PWD/pr-genius"

# Sanity check: prints what it found and what is missing
prgenius-core doctor

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

> **First run of `doctor` matters.** It tells you whether the knowledge bundle
> was found and which optional pieces are missing. `overall: NOT OK` after a
> bare `pip install` is expected — it is the wheel containing code only, not a
> broken install. The warning names exactly what to do.

### CLI reference

The console script is `prgenius-core`; `python3 -m prgenius` is equivalent.
Every command takes a global `--repo-root` to point at a knowledge-base checkout.

| Command | What it does | Key flags |
|---|---|---|
| `analyze` | PR analysis + improvement suggestions | `title`, `--repo`, `--body`, `--diff-stat` |
| `eval` | Older three-tier assessment (kept for compatibility) | `title`, `--repo` |
| `coach` | Agent PR dojo — exit 0 = pass, 1 = fail | `title`, `--repo`, `--body` |
| `triage` | Policy-aware preflight checks | `title`, `--repo`, `--diff-stat` |
| `doctor` | Install / knowledge-base / `gh` / MCP self-test | `--format json` |
| `suggest` | Alias of `analyze` | same as `analyze` |
| `harvest` | Rejected PR → anti-pattern / lesson draft | `owner/repo [number]` |
| `profile get` | Show a repo profile | `owner/repo` |
| `profile writeback` | Profile update suggestions (dry-run) | `--author` |
| `case list` | List case studies | `--repo` |
| `schema info` | Supported OKF schema versions | — |
| `status` | Health of in-flight outbound PRs | `--author`, `--format json`, `--save-snapshot` |
| `update-issue` | Refresh a pinned GitHub issue with heartbeat status | `--author`, `--issue` |
| `auto-ping` | Suggest pings for stale PRs (**dry-run**; `--confirm` to act) | `--author`, `--confirm` |
| `auto-rebase` | Suggest rebases for PRs that need one (**dry-run**; `--confirm`) | `--author`, `--confirm` |
| `dump` | NDJSON dump of every case | `--out` |
| `mcp serve` | Run the MCP server on stdio | — |
| `maintainer` | Maintainer action decision for one PR (5 actions) | `title`, `--repo` |
| `review-queue` | Build a prioritised review-queue digest | `--prs-file` |
| `issue` | Score/evaluate a single issue | `--repo`, `--number`, `--format` |
| `issue-batch` | Score many issues at once | `--repo`, `--state`, `--label`, `--limit`, `--format` |

`issue` and `issue-batch` were added in v1.6.3. Examples:

```bash
# One issue
python3 -m prgenius issue --repo Ikalus1988/MisakaNet --number 2792

# A labelled batch, machine-readable
python3 -m prgenius issue-batch --repo Ikalus1988/MisakaNet \
  --state open --label question --limit 50 --format json
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
      - uses: zsxh1990/pr-genius@v2.1.4
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

### Version Pins

- **`@v2.1.4`** — Pinned to a specific release tag (for reproducibility)
- **`@main`** — Latest development version (not recommended for production)

> **No floating major tag tracks 2.x.** The only floating major tag is `v1`, and
> its auto-update is gated on `v1.*` releases (`publish-pypi.yml`), so it is
> frozen at `v1.8.0` — it does **not** follow `v1.9.x`, and there is no `v2` tag.
> Pin a full `vX.Y.Z` tag instead of relying on a floating major.

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

**Docker Image Tags** (emitted by `publish-ghcr.yml` from each `vX.Y.Z` git tag as `{version}` / `{major}.{minor}` / `{major}`):
- `ghcr.io/zsxh1990/pr-genius:latest` — Latest release
- `ghcr.io/zsxh1990/pr-genius:2.1.4` — Specific version
- `ghcr.io/zsxh1990/pr-genius:2.1` — Minor version
- `ghcr.io/zsxh1990/pr-genius:2` — Major version

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

Docker (stdio MCP server, built from the root `Dockerfile`): `docker build -t pr-genius . && docker run --rm -i pr-genius` — this image is a stdio server, not an HTTP service. (The `ghcr.io/zsxh1990/pr-genius` image is built from `Dockerfile.github_action` for the GitHub Action, not for MCP stdio.)

### 14 MCP Tools

| Tool | Purpose | Required Args |
|------|---------|---------------|
| `analyze_pr` | Merge probability + optimization path + 3-tier risk | `title`, `repo` |
| `coach_pr` | Go/no-go decision (pass/fail) | `title`, `repo` |
| `triage_pr` | Maintainer policy check (9 rules) | `title`, `repo` |
| `get_repo_profile` | Repo profile (17 fields) | `repo` |
| `list_open_prs` | Local open **case-study records** (not live GitHub PRs; live ones → `status_prs`); optional `repo`/`author` filters | *(none)* |
| `get_case_study` | PR case study details | `repo`, `pr_number` |
| `search_patterns` | Anti-pattern/success-pattern search | `query` |
| `schema_info` | OKF schema versions | *(none)* |
| `status_prs` | Outbound PR status heartbeat | `author` or `repo` |
| `profile_writeback_suggestions` | Profile update suggestions (dry-run) | `author` |
| `maintainer_view` | Maintainer-side PR view (5 actions: `READY_FOR_REVIEW`, `WAIT_FOR_AUTHOR`, `CLOSE_DUPLICATE`, `CLOSE_STALE_OR_RISKY`, `HOLD_MAINTAINER_DECISION`) | `title`, `repo` |
| `contributor_view` | Contributor readiness decision (5 actions: `READY_TO_SUBMIT`, `FIX_BEFORE_SUBMIT`, `NEEDS_DISCUSSION`, `IMPROVE_CHANCE`, `ASK_MAINTAINER`) | `title`, `repo` |
| `review_queue` | Prioritized review queue | `prs` or `prs_file` |
| `prgenius_doctor` | Install/data/MCP self-test — run this when analyze returns nothing | *(none)* |

### Tool Parameter Notes

- **`title`** (required for `analyze_pr`, `coach_pr`, `triage_pr`): The PR title, e.g. `"fix: timeout in connection pool"`
- **`repo`** (required for most tools): Repository in `owner/name` format, e.g. `"encode/httpx"`
- **`pr_description`** (optional): Additional PR body text for deeper analysis
- **`query`** (required for `search_patterns`): Search keywords, e.g. `"connection timeout"`
- **`diff_stat`** (optional for `analyze_pr`, `coach_pr`): `git diff --stat` output — populates the `impact`/`review` fields (both are `null` without it) and is the authoritative PR-size signal
- **`star_count`** ≥ 0, **`repo_merge_rate`** in `[0.0, 1.0]`, **`author_association`** in `NONE/CONTRIBUTOR/COLLABORATOR/MEMBER/OWNER`, **`mergeable`** in `MERGEABLE/CONFLICTING/UNKNOWN` — invalid values are rejected instead of silently producing meaningless output

## 🧩 DSH Plugin

PR Genius ships as a [DSH (Cordis)](https://github.com/deepseek-ai/dsh) plugin (v2.0.0+). The TypeScript layer is a thin shell — analysis is delegated to the existing Python MCP engine; the plugin adds five UI surfaces on top.

### Install

```bash
dsh plugin add pr-genius
```

Or apply the one-line patch in [`cordis.patch.yml`](cordis.patch.yml). Full guide: [`docs/dsh-integration.md`](docs/dsh-integration.md).

### Five surfaces

| Surface | Slot | What it does |
|---------|------|-------------|
| **Dashboard** (sidebar) | `sidebar.footer.action` | PR Intelligence Dashboard — cross-repo status at a glance |
| **Advisor tab** | `conversation.view` | Session-level advisor for the current conversation |
| **Advisor panel** | `details` (pinned SDK) / `sidebar.right.pane.tab` (upstream) — probed at runtime | Same advisor as a right-hand panel |
| **`/prgenius`** | `ctx.command` (Cordis command API, not a slot) | Slash-command for inline PR checks |
| **Preferences** | `settings.section` | Config card for the tunables below |

Maintainer mode is the same five surfaces on a different projection (5-action decision: `READY_FOR_REVIEW`, `WAIT_FOR_AUTHOR`, `CLOSE_DUPLICATE`, `CLOSE_STALE_OR_RISKY`, `HOLD_MAINTAINER_DECISION`).

### Configuration

All tunables are Schemastery-validated and settable from `cordis.yml` — no code changes needed. Invalid values fail at load time naming the field. See [`src/config.ts`](src/config.ts) for the full schema (14 leaf fields: `kbRoot`, MCP `transport`/`command`/`args`/`url`/`timeoutMs`/`protocolVersion`, sidebar default view, maintainer `enabled`/`actions`/`confidenceMin`/`staleDays`, locale, risk filter).

### Relationship to v1.x

The DSH plugin wraps the same Python analysis engine (`prgenius/src/prgenius/mcp.py`). v1.x CLI and MCP server continue to work unchanged. The plugin adds UI surfaces and config management; it does not fork the analysis logic.

> **Honesty note**: The DSH plugin has been verified for TypeScript compilation, unit tests, and static contract conformance (`scripts/check_dsh_plugin_contract.py`, 27/27 checks). It has **not** been run against a live DSH runtime — rendering and runtime behavior require DSH verification. See [`docs/compatibility.md`](docs/compatibility.md) for the version matrix (every cell marked unrun) and [`docs/maturity-self-assessment.md`](docs/maturity-self-assessment.md) for the completeness scorecard.

## 🧑‍💻 For Contributors

`maintainer_view` answers "what should the *maintainer* do with this PR?"
`contributor_view` answers the other side: "**should I submit this PR yet, and
what is blocking me?**" It is the pre-submission gate — run it *before* opening
the PR, then again whenever you change something.

```bash
python3 -m prgenius coach "fix: timeout in connection pool" \
  --repo encode/httpx --body "Fixes #4821"
```

or over MCP as `contributor_view` (same engine, `title` + `repo` required).

### The 5 outcomes and what to do about each

| Decision | Meaning | Your next move |
|---|---|---|
| `READY_TO_SUBMIT` | Nothing structural is blocking | Open the PR |
| `FIX_BEFORE_SUBMIT` | Concrete, fixable defects found | Fix the listed checklist items, re-run, then submit |
| `NEEDS_DISCUSSION` | Breaking change, core, or security surface | Open an issue first; a large surprise PR gets closed |
| `IMPROVE_CHANCE` | Not blocking, but it could be better | Optional — raise odds (tests, issue link, `diff-stat`) |
| `ASK_MAINTAINER` | Genuinely unclear from here | Ask the maintainer before investing more work |

### What moves you from `FIX_BEFORE_SUBMIT` to `READY_TO_SUBMIT`

Signals the evaluator weighs most, in practice:

1. **Link an issue.** `Fixes #N` / `Closes #N` in the body — the single most
   common reason a first PR gets bounced.
2. **Keep it small.** Size comes from `--diff-stat` (`git diff --stat` output).
   Without `diff-stat` the impact/review fields are `null`, so pass it.
3. **Tests that fail without your change.** A test that passes either way is
   decoration.
4. **Match the repo's conventions**, not the global ones — read that repo's
   profile first (`python3 -m prgenius profile get owner/name`). The rules
   differ per project; that is the point of the knowledge base.

The maintainer-side five actions are the mirror image — see the `maintainer_view`
row in the [MCP tools](#-mcp-configuration) table.

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
