---
type: Repo Profile
title: harbor-framework/harbor PR 模式分析
description: Harbor Framework 仓 PR 模式 + zsxh1990 PR #2121 进展
repo: harbor-framework/harbor
url: https://github.com/harbor-framework/harbor
star: 5748
language: Python
zsxh_pr_count: 1
status: in-flight
analyzed_at: 2026-10-01
tags:
  - repo-profile
  - ai-agent-framework
  - python
  - litellm
related:
  - ./pr-2121-optional-deps.md
agent_guidelines:
  allow_unsolicited_pr: true
  require_signed_off: false
  require_cla: false
  require_changeset: false
  require_issue_first: false  # 2026-10-01 重验: CONTRIBUTING 未强制 issue-first, 但 interfaces/core 改动需先 RFC 讨论
  ai_policy: conditional  # 2026-10-01 重验: CONTRIBUTING Golden Rule (源自 Ghostty) — 欢迎 coding agent, 但须自证理解 + 披露 agent 使用
  ai_assisted_disclosure: true  # 2026-10-01 重验: "Disclose which agents were used and to what extent"
  human_required_in: [pr_body, comments]  # 2026-10-01 重验: "Docs, PR descriptions, issues, and comments should be written by a human with AI assistance"
  maintainer_vibe: slow  # 2026-10-01 重验: 我方 #2121 开 95d 三次 ping 零人类响应 (bot 活跃); 但外部 PR 合并率 86.8%/30d, 选择性响应
  bot_review: devin
  ci_first_run_needs_approval: false
  default_branch: main
  response_time_h_median: null  # 未核实: 无可靠样本可算中位数 (我方 #2121 至今无人类响应)
  merge_rate_30d: 0.868  # 2026-09-01→2026-10-01: 164 merged / 25 closed-unmerged (GH search)
  close_keywords: []
  one_pr_friendly: true
misakanet_queries:
  - misakanet/lessons/contrib/devin-ai-review-bot.md  # Harbor 接入 Devin AI review 经验
misakanet_lessons: []
federation_status: declared-2026-07-02
verified_at: "2026-10-01T13:29:03Z"
evidence_urls:
  - https://github.com/harbor-framework/harbor
  - https://api.github.com/repos/harbor-framework/harbor
  - https://api.github.com/repos/harbor-framework/harbor/releases/latest
  - https://api.github.com/repos/harbor-framework/harbor/commits
confidence: high  # autogen from GH API; bump to medium if human-curated
last_release: v0.23.0
last_commit_sha: bf991e49
stars: 5748
agent_guidelines_evidence:
  allow_unsolicited_pr: https://github.com/harbor-framework/harbor/blob/main/CONTRIBUTING.md
  require_issue_first: https://github.com/harbor-framework/harbor/blob/main/CONTRIBUTING.md
  ai_policy: https://github.com/harbor-framework/harbor/blob/main/CONTRIBUTING.md
  maintainer_vibe: https://github.com/harbor-framework/harbor/pulls?q=is%3Apr+is%3Aclosed
  external_merge_rate_30: https://github.com/harbor-framework/harbor/pulls?q=is%3Apr+is%3Aclosed
  close_keywords: https://github.com/harbor-framework/harbor/pulls?q=is%3Apr+is%3Aclosed
  ai_assisted_disclosure: https://github.com/harbor-framework/harbor/blob/main/CONTRIBUTING.md
  human_required_in: https://github.com/harbor-framework/harbor/blob/main/CONTRIBUTING.md
---


# harbor-framework/harbor

> Harbor 是 AI agent 框架（LiteLLM + datasets）。  
> **AI 友好度**：条件式欢迎（CONTRIBUTING Golden Rule：欢迎 coding agent，但须自证理解 + 披露 agent 使用；PR body/评论须人类主笔）。  
> **zsxh1990 PR 经验**：1 个 open（#2121，已开 95 天，零人类 maintainer 响应）。  
> **2026-10-01 重验**：star 2.9k→5.7k，30d 合并 164 个（86.8%），仓极活跃但我方 PR 被无视。

---

## 1. 友好度画像（2026-10-01 重验）

- ✅ **Vercel 集成**（PR 创建即触发部署预览）
- ✅ **Devin AI 自动 review**（2026-06→09 多轮 review 一直活跃）
- ✅ 外部 PR 合并率高（30d 164 merged / 25 closed-unmerged = 86.8%；最近 10 个 merged 出自 8 位不同人类作者）
- ⚠️ **Golden Rule**（CONTRIBUTING 明文，源自 Ghostty）：必须理解自己贡献的代码；PR description 人类手写；**披露用了哪些 agent 及程度**
- ⚠️ interfaces / core logic 改动**必须先 RFC 讨论**（`rfcs/` 目录，人类主笔，"If an RFC is slop, we will close it"）
- ⚠️ 对我方 #2121：**95 天零人类回复**（3 次 ping 无果）→ 对冷门方向选择性无视

---

## 2. zsxh1990 PR 进展

### 🟡 #2121 [feat: make litellm and datasets optional dependencies](https://github.com/harbor-framework/harbor/pull/2121)

| 维度 | 数据（2026-10-01 核实） |
|---|---|
| 创建 | 2026-06-28 09:14 UTC（**已 95 天**） |
| 状态 | **仍 open**（最近活动 2026-09-06） |
| +71 / -32 / 6 files | 小而精 |
| Vercel 部署 | 需 maintainer 授权 |
| Devin review | 多轮（2026-06-28 / 08-02 / 08-10 / 08-22 / 09-03 / 09-05，每轮 1-3 findings） |
| Codecov | 2026-09-06 patch coverage 63.6%（8 行未覆盖：kimi_cli / lite_llm / litellm_config / utils） |

**关键时间线**：

| 时间 | 事件 |
|---|---|
| 2026-06-28 | PR 创建；Devin 第 1 轮 review（2 findings） |
| 2026-07-07 | zsxh1990 friendly check-in |
| 2026-08-02 | Devin 再 review（3 new findings）；lock file 重生成 |
| 2026-08-04 / 08-06 | 两次 friendly ping（附 544MB→39MB 安装体积论据） |
| 2026-08-16 | zsxh1990 逐条回应 review（2 resolved + 5 addressing） |
| 2026-09-05 | Devin 最新 review（1 new + 3 flags） |
| 2026-09-06 | Codecov 报 patch coverage 63.6% |
| **全程** | **零人类 maintainer 评论/评审** |

**处置建议（数据依据）**：三次 ping 间隔 4-6 周均无回音；对照本仓 30d 合并 164 个的活跃度，
是"选择性不接"而非"没看到"。参考 OpenClaw ClawSweeper 优雅退出规则（7 天无活动即 close），
此 PR 早已越线——**建议主会话决定：主动 close 留档，或降级为 issue 讨论**。

---

## 3. 提 PR 方向

> 2026-10-01 重验补充：CONTRIBUTING 要求 **interfaces/core 改动先 RFC**；
> Agents/Plugins 集成类"较宽松"但需**至少一个用户需求证据**（issue 评论）。

### 🥇 optional dependencies 模式（已铺路）

- harbor 当前默认安装所有 deps（litellm + datasets 都很重）
- #2121 已拆 litellm + datasets → extras_require
- 后续可拆：`harbor[observability]` / `harbor[tracing]` / `harbor[vectordb]`

### 🥈 LiteLLM provider 扩展

- harbor 用 litellm 统一 LLM 调用
- 加新 provider（Ollama、vLLM、Together）只需 litellm 配置，无需新代码

### 🥉 agent runtime 改进

- 工具调用追踪
- Token usage metrics
- Async batching

---

## 4. SOP

| 维度 | harbor 特色 |
|---|---|
| CI | Vercel 预览 + GitHub Actions + Codecov（patch coverage 会被 bot 贴出） |
| Review | Devin AI + 人工（人工对我方 PR 目前缺位） |
| Test | pytest + Vercel preview 验证 |
| 部署 | merge → Vercel 自动部署 |
| **披露** | PR body 必须写明用了哪些 agent 及程度（Golden Rule） |
| **主笔** | PR description / 评论 / issue 人类主笔（首稿+终稿） |
| Fork | 开 "Allow edits by maintainers"（CONTRIBUTING 明文，利于 merge） |

---

## 5. 关联文档

- [OKF bundle 根入口](../index.md)
- [PR #2121 案例深读](./pr-2121-optional-deps.md)