---
type: Anti-Pattern
title: "feat(voice): MCP voice hooks for audio prompts on tool use"
source: "Ikalus1988/MisakaNet#928"
source_url: "https://github.com/Ikalus1988/MisakaNet/pull/928"
category: pr-review-feedback
severity: medium
learned_at: 2026-08-13
---

## Problem

PR [Ikalus1988/MisakaNet#928](https://github.com/Ikalus1988/MisakaNet/pull/928) 已合并 by @Ikalus1988。

**标题**: feat(voice): MCP voice hooks for audio prompts on tool use
**作者**: @zsxh1990
**状态**: 已合并 by @Ikalus1988

## Root Cause

> @Ikalus1988: ## DCO Sign-off Required

Please add Signed-off-by to your commits:

## What Happened

## Summary

Add voice feedback to MCP tool responses via PostToolUse hook.
When MisakaNet tools are used, the hook plays matching audio prompts.

Closes #912 (voice prompts playback verification).

## Changes

- **`scripts/mcp_server.py`** — add `voice` field to all tool responses
- **`scripts/mcp_http_server.py`** — add `voice` field to all tool responses
- **`scripts/misakanet_voice_hook.sh`** — PostToolUse hook script
- **`docs/integrations/mcp-voice-hooks.md`** — setup documentation
- **`tes

## Lesson

这条 PR 有真实失败信号，但信号很窄：**DCO sign-off 缺失**。维护者的第一条回复就是

> ## DCO Sign-off Required
> Please add Signed-off-by to your commits:

之后 PR 才被合并。所以它不是「设计被拒」，是**流程性退回**——本可以不发生。

可复用的教训：

1. **sign-off 不是可选项，是合并前置条件。** 走 DCO 的仓库会在 PR 打开后立刻退回，
   而不是在 review 里提。等到 review 才知道，等于多付一轮往返。
2. **提交时就带上，不要事后补。** `git commit -s` 写进提交习惯，比在 PR 被退后
   `git commit --amend --signoff` 再 force-push 干净得多——后者会丢掉已有 review
   的关联（rebase 后 DCO signoff 还可能再度丢失，需逐个 commit 核
   `%(trailers:key=Signed-off-by,valueonly)`）。
3. **改动越大，流程性退回的代价越高。** 这条 PR 动了 5 个文件（两个 server、一个
   hook 脚本、一份文档、测试），却卡在一个 trailer 上。

## Solution

提交时直接带 sign-off：

```bash
git commit -s -m "feat(voice): add audio prompts for MCP tool use"
```

或一次性配置该仓库：

```bash
git config format.signOff true
```

若已经被退回，逐个 commit 补签而不是只改最后一个：

```bash
git rebase --exec 'git commit --amend --no-edit --signoff -S' <base>
# 复核每个 commit 的 trailer
git log --format='%(trailers:key=Signed-off-by,valueonly)'
```

## Verification

如何验证教训已内化：

- 提 PR 前看本地 `git log --format='%(trailers:key=Signed-off-by,valueonly)'`
  每个 commit 都非空；
- 用 `python3 -m prgenius coach` 过一遍，确认没有 DCO 相关的待办项；
- 在需要 sign-off 的仓库开一个最小 PR，**不被退回**即为通过。
