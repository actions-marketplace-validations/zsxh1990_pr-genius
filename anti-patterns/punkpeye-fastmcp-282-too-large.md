---
key: punkpeye-fastmcp-282-too-large
type: Anti-Pattern
repo: punkpeye/fastmcp
created: 2026-07-29
anchors: [282]
tags: [pr-size, first-contribution, maintainer-bandwidth]
source_url: https://github.com/zsxh1990/pr-genius/tree/main/anti-patterns/punkpeye-fastmcp-282-too-large.md
updated: 2026-08-01
confidence: medium

---

# fastmcp: PR Too Large for First Contribution

## Pattern

First-time contributor PR with +271/-16 changes gets closed without review. Maintainer (punkpeye) has limited bandwidth and prefers smaller, focused PRs.

## Evidence

**PR #282** — "feat: add testWithOllama() for local LLM testing"
- Created: 2026-06-28
- Closed: 2026-07-24 (no merge)
- Size: +271/-16, 1 file
- Review: 0 maintainer reviews
- Result: Closed without review

## Root Cause

1. **PR size**: 271 additions is large for a first contribution to a personal project
2. **Maintainer bandwidth**: punkpeye maintains multiple large repos (awesome-mcp-servers 91k stars, fastmcp 3k stars)
3. **No issue first**: PR was not preceded by an issue discussion

## How to Avoid

1. **Split large PRs**: Break into 2-3 smaller PRs (< 100 lines each)
2. **Open issue first**: Discuss the feature before implementing
3. **Start with docs/tests**: First PR should be low-risk (docs fix, test addition)
4. **Check maintainer response time**: If >1 week, consider smaller PRs


## When This Fires (threshold, derived — not invented)

There is **no detector** for this pattern yet. What follows is the threshold
derived from signals the analyzer already computes, so a detector has something
defensible to stand on rather than a number pulled from the air.

The evidence above is `+271/-16` and it was closed without review. By the
two-dimensional size classifier already in `evaluator.py` (issue #59: XS ≤50
lines / ≤2 files, S 51-150 / 3-5, M 151-300 / 6-10, L 301-500 / 11-20, XL >500
or >20 files) that lands in **M**.

So this is **not** "L and XL are too big" — the general classifier already
surfaces those. The sharper claim is: **for a first contribution to a small
project, M is already too big.** The advice in the evidence agrees ("split into
2-3 PRs, < 100 lines each" — i.e. below S).

A detector would need two signals, both of which the analyzer already has:

| signal | source | fires when |
|---|---|---|
| first-time contributor | `author_association` in `NONE` / `FIRST_TIMER` | true |
| size | `pr_size` from `diff_stat` | `>= M` |

Both are already computed; neither requires new parsing. What is *not* settled is
whether "first contribution" alone is the right gate, or whether it should also
require the target repo to be small / low-traffic — the evidence cites
maintainer bandwidth, not just newcomer status. That judgement is a product
call, and it is why this file documents the threshold instead of shipping a
detector that guesses.

**Do not add `trigger_keywords` to fake coverage.** Keywords cannot express
"271 additions", and a keyword that happened to match would make this file look
detected when it is not.
