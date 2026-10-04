---
type: Anti-Pattern
title: "feat(voice): add global disable switch"
source: "Ikalus1988/MisakaNet#936"
source_url: "https://github.com/Ikalus1988/MisakaNet/pull/936"
category: merged-reference
severity: info
learned_at: 2026-08-13
---

## Problem

PR [Ikalus1988/MisakaNet#936](https://github.com/Ikalus1988/MisakaNet/pull/936) 已合并 by @Ikalus1988。

**标题**: feat(voice): add global disable switch
**作者**: @zsxh1990
**状态**: 已合并 by @Ikalus1988

## Root Cause

无 maintainer 评论

## What Happened

## Summary

Adds a global toggle to disable all voice prompts.

Closes #934

## Changes

**`docs/connect.html`**:
- Added global disable toggle (always visible below voice toggle)
- Toggle stores preference in `localStorage` (`misaka-voice-disabled`)
- Shows `MISAKANET_VOICE=0` env var hint when enabled
- Voice toggle greyed out when global disable is active

## Validation

- [x] Global disable toggle persists in localStorage
- [x] Voice disabled when global toggle is on
- [x] Voice toggle greye

## Lesson

> **没有失败信号，此处有意留空。** 这个 PR 已合并、且没有任何 maintainer
> 评论或改动要求，不存在可提炼的反模式或教训。保留本记录仅作已收割标记。
> **不要往这里填 Lesson** —— 那会制造一条声称发生了实际并未发生的失败。

## Solution

> 无 —— 没有失败需要修复。

## Verification

> 无。
