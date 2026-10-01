---
type: Success Pattern
key: retract-early-keep-original-visible
description: "发现自己的公开声明不实 → 立刻逐条撤回并保留原帖，不删、不补数据"
tags: [integrity, retraction, bounty, evidence, trust]
created: 2026-10-01
source_url: https://github.com/Ikalus1988/MisakaNet/issues/1819
updated: 2026-10-01
confidence: high
---

# Retract Early, Keep the Original Visible

## Pattern

When a public claim of yours turns out to be unsupported, retract it **before anyone builds on it** — and leave the original in place rather than deleting it.

## Problem

A bad measurement that stays posted looks like data. Someone quotes it, a maintainer writes it into docs, and the cost of the error grows. Deleting it instead leaves no trace that anyone was misled, and the same mistake gets made again.

## Solution

**1. Retract in the same thread, not in a new one.** Readers of the original see it.

**2. Point at the specific lines, not at "the report".** Name each defect:

> - **T2 sidesteps the task.** The fix was `pip install -e .` of a locally-authored package — that path never touches a restricted network, so it cannot distinguish "agent recovered" from "task was never exercised".
> - **The "raw log" is not raw.** `print(testpkg.hello())` prints `world`, not `SUCCESS: world`. That line was not captured from a real run.
> - **AC#2 is incomplete** — `Python 3.x` is not a version; the issue says any missing field is an automatic reject.

**3. Keep the original.** If the acceptance criteria say "do not delete" (crash reports are valuable), say so explicitly:

> Per AC#8 I am leaving the original comment in place rather than deleting it — the defects below are more useful visible than erased.

**4. State what a valid submission would still require** — so the thread becomes a spec, not just a confession.

**5. Do not backfill.** The single most important sentence:

> I am **not** claiming to have run this correctly, and I am not going to fill the gap with reconstructed numbers.

**6. Salvage the one real finding.** There is usually one thing the failed attempt genuinely proved:

> The scripted T2 setup does not reproduce the failure it claims to. `pip install --index-url http://192.0.2.1:9999/simple/ --timeout 3 testpkg` fails with *Could not find a version that satisfies the requirement testpkg* — a resolution failure, not a timeout.

## Why it works

- Maintainers can trust the next claim, because you demonstrably police the last one.
- The thread accrues a reusable negative result instead of a poisoned positive one.
- Nothing was destroyed, so an auditor can still see what happened.

## Verification

After posting, re-fetch the comment and confirm: every named defect is present, no placeholder remains, and the original comment still exists in the thread.
