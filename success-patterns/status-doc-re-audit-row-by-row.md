---
type: Success Pattern
key: status-doc-re-audit-row-by-row
description: "被要求只改版本号时，反问「内容是否也真」并逐行给出线上实测证据"
tags: [docs, status-page, audit, evidence, maintainer-trust]
created: 2026-10-01
source_url: https://github.com/Ikalus1988/MisakaNet/pull/2440
updated: 2026-10-01
confidence: high
---

# Re-audit a Status Doc Row by Row, Not by Version Bump

## Pattern

Asked to "bump the version line", re-verify every content row against live sources and report the evidence per row. A status page that is right about the number and wrong about the modules is still wrong.

## Problem

Maintainer review of a status-file PR:

> 1. The version is one behind again. Please bump to `v2.39.0`.
> 2. **The module table is a status claim, not a changelog.** Please re-check the table against the live site rather than only the version line.

Doing only (1) is the tempting fast path. It lands, and the doc stays wrong in the way that actually matters.

## Solution

**1. Confirm the version from two independent sources** — not from the PR's own text:

```bash
git show upstream/main:.release-please-manifest.json   # 2.39.0
curl -sS https://registry.npmjs.org/<pkg>/latest        # 2.39.0
curl -sS https://misakanet.org/api/versions             # release/registry/npm/plugin_manifest
```

**2. Verify each named feature by hitting it.** The reviewer named five things that landed; check each:

| Claim | Probe | Result |
|---|---|---|
| Search projection | `GET /data/lessons-lite.json` vs `/data/lessons.json` | 185188 B / 7 fields vs 1325134 B, both 427 rows |
| Activity panel | `GET /api/activity` | 200, `source: /api/analytics/traffic`, `total` 4144 |
| Versions endpoint | `GET /api/versions` | 200, four sources |
| Alias redirects | `curl -w '%{redirect_url}' /connect` | 301 → `/start` |
| Marketplace | `GET /marketplace`, `GET /integrations`, grep homepage | **404 / 404 / absent** |

**3. Omit rows you cannot evidence — and say why.**

> One item I left out on purpose: Marketplace listing. I could not find it on the site. I would rather omit a row than assert a status I have no evidence for. If it means a plugin-directory listing rather than a page here, point me at it.

That sentence is what makes the rest of the table believable.

**4. Add the structural cause, not just the symptom.** The reason the file keeps going stale:

> 当前缺失 — the version line is hand-maintained and nothing reconciles it with `/api/versions`, so it drifts. A `--check` that diffs the header against that endpoint would stop the recurrence.

**5. Flag anything in flight that would make you stale immediately** (an open release PR), so the maintainer can sequence.

## Why it works

- Turns a chore into an audit the maintainer can act on.
- The omitted row signals that the included rows were checked, not assumed.
- Naming the drift mechanism converts a one-off fix into a proposal.

## Verification

After landing, every row in the table has a probe that a reviewer can re-run, and every probe has a stated result. A row with no probe does not exist.
