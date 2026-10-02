---
type: Repo Profile
title: sourcebot-dev/sourcebot PR 模式分析
description: Sourcebot 仓 PR 模式 + zsxh1990 PR #1383 进展
repo: sourcebot-dev/sourcebot
url: https://github.com/sourcebot-dev/sourcebot
star: 3958
language: TypeScript
zsxh_pr_count: 1
status: closed-no-merge  # 2026-10-01 重验: #1383 已于 2026-08-02 由 zsxh1990 自行 close（6 周零 maintainer 响应）
analyzed_at: 2026-10-01
tags:
  - repo-profile
  - code-search
  - ctags
  - typescript
related:
  - ./pr-1383-ctags-failure-detection.md
agent_guidelines:
  allow_unsolicited_pr: true
  require_signed_off: false
  require_cla: false
  require_changeset: false
  require_issue_first: true  # 2026-10-01 重验: CONTRIBUTING "Want to take on an issue? Leave a comment and a maintainer may assign it"; UI/core feature 必须先 design review
  ai_policy: welcoming
  ai_assisted_disclosure: false
  human_required_in: []
  maintainer_vibe: slow  # 2026-10-01 重验: 我方 #1383 6 周零人类响应; 近期 merged 10/10 全是公司内部 2 人 (brendan-kellam/msukkari)
  bot_review: coderabbit
  ci_first_run_needs_approval: false
  default_branch: main
  response_time_h_median: null  # 未核实: 无可靠样本 (我方 PR 至今无人类响应)
  merge_rate_30d: 0.894  # 2026-09-01→2026-10-01: 42 merged / 5 closed-unmerged (GH search)
  close_keywords: []
  one_pr_friendly: false  # 2026-10-01 重验: UI/core 需 design review, 外部 PR 近期 0 merge
misakanet_queries:
  - misakanet/lessons/contrib/silent-failure-detection.md  # ctags 沉默失败检测
misakanet_lessons: []
federation_status: declared-2026-07-02
verified_at: "2026-10-01T13:29:03Z"
evidence_urls:
  - https://github.com/sourcebot-dev/sourcebot
  - https://api.github.com/repos/sourcebot-dev/sourcebot
  - https://api.github.com/repos/sourcebot-dev/sourcebot/releases/latest
  - https://api.github.com/repos/sourcebot-dev/sourcebot/commits
confidence: high  # autogen from GH API; bump to medium if human-curated
last_release: v5.1.15
last_commit_sha: 390e8b2d
stars: 3958
agent_guidelines_evidence:
  allow_unsolicited_pr: https://github.com/sourcebot-dev/sourcebot/blob/main/CONTRIBUTING.md
  require_issue_first: https://github.com/sourcebot-dev/sourcebot/blob/main/CONTRIBUTING.md
  ai_policy: https://github.com/sourcebot-dev/sourcebot/blob/main/CONTRIBUTING.md
  maintainer_vibe: https://github.com/sourcebot-dev/sourcebot/pulls?q=is%3Apr+is%3Aclosed
  external_merge_rate_30: https://github.com/sourcebot-dev/sourcebot/pulls?q=is%3Apr+is%3Aclosed
  close_keywords: https://github.com/sourcebot-dev/sourcebot/pulls?q=is%3Apr+is%3Aclosed
---


# sourcebot-dev/sourcebot

> Sourcebot 是 self-hosted 代码搜索平台（open core：FSL core + EE 商业许可，公司产品非 side-project）。  
> **AI 友好度**：中（中型 startup，CodeRabbit 已配；UI/core feature 须先 design review）。  
> **zsxh1990 PR 经验**：1 个（#1383，2026-08-02 自行 close，零 maintainer 响应）。  
> **2026-10-01 重验**：star 3.6k→4.0k，30d 合并 42 个但近 10 个全出自公司内部 2 人。

---

## 1. 友好度画像（2026-10-01 重验）

- ✅ CodeRabbit 自动 review 配置
- ✅ 仓活跃（30d 42 merged / 5 closed = 89.4%；昨天仍有 merge）
- ⚠️ **open core**：core = FSL 许可（2 年后转 Apache/MIT）；ee = 商业许可（贡献保留权利）
- ⚠️ **CONTRIBUTING 护栏**：UI/core product feature **必须先与 core team design review**，"PRs that ignore these guardrails will likely be closed"；最适合合并的是 bug fix / code host 集成 / LLM provider / docs
- ⚠️ 认领 issue 流程："Leave a comment and a maintainer may assign it to you"
- ⚠️ **近期外部 PR 合并为零**：2026-09 最近 10 个 merged 全部是 brendan-kellam（6）+ msukkari（4）公司内部
- ⚠️ 对我方 #1383：6 周零人类 maintainer 响应

---

## 2. zsxh1990 PR 进展

### 🔴 #1383 [feat: detect and surface ctags indexing failures](https://github.com/sourcebot-dev/sourcebot/pull/1383) — closed-not-merged

| 维度 | 数据（2026-10-01 核实） |
|---|---|
| 创建 | 2026-06-28 09:23 UTC |
| 关闭 | **2026-08-02 05:41 UTC 由 zsxh1990 自行 close** |
| 状态 | closed，merged=false |
| +60 / -6 / 2 files | 极小 PR（理想 size）|
| CodeRabbit review | 1 actionable finding（Linked Issues 警告：UI 未展示 warning） |

**时间线**：

| 时间 | 事件 |
|---|---|
| 2026-06-28 | PR 创建；CodeRabbit review（1 actionable） |
| 2026-07-07 | zsxh1990 friendly check-in |
| 2026-07-16 | zsxh1990 提 UI follow-up 方案（detection+persist 本 PR / UI 下一 PR） |
| 2026-08-02 | **zsxh1990 自行 close**："open for 6 weeks with no maintainer response. Happy to reopen if there's interest." |

**教训**：Bot review 通过 ≠ maintainer 会看。小而精 + CodeRabbit 绿也救不了"内部团队自己排期"的仓。

**处置建议**：已 close 留档。若要再投本仓，走 CONTRIBUTING 路径——先在 issue 下留言请 maintainer assign，
且选题优先 bug fix / 集成类；UI/core 方向必须先 design review 否则必关。

---

## 3. 提 PR 方向（2026-10-01 按新 CONTRIBUTING 重排）

> **护栏**：UI/core feature 必须先 design review，否则"likely closed"。CONTRIBUTING 明文最欢迎：bug fix / code host integrations / LLM providers / docs。先在 issue 下留言等 assign。

### 🥇 bug fix（最欢迎）

- `is:issue is:open label:bug`（当前有 1687/1689/1691 等明确 bug 带 repro）
- 搜索正确性类：转义引号、linguist-language 覆盖、路径含空格/非 ASCII 无法索引

### 🥈 connector / LLM provider 扩展（欢迎）

- 新增 GitLab / Bitbucket connector
- 改进 GitHub connector 速率限制处理
- 新 LLM provider

### 🥉 docs 改进（欢迎）

### ⚠️ search UX / indexing error UI（需 design review 先行）

- #1383 的 UI follow-up（degraded 状态展示）属于此类——直接提 PR 会被关

---

## 4. 关联文档

- [OKF bundle 根入口](../index.md)
- [PR #1383 案例深读](./pr-1383-ctags-failure-detection.md)