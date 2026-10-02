---
type: Repo Profile
title: future-agi/future-agi PR 模式分析
description: future-agi observability 仓 PR 模式 + zsxh1990 PR #778 + 克莱恩亲自 check-in
repo: future-agi/future-agi
url: https://github.com/future-agi/future-agi
star: 2103
language: Python
zsxh_pr_count: 1
status: closed-no-merge  # 2026-10-01 重验: #778 已于 2026-08-02 由 zsxh1990 自行 close（8 周零 maintainer 响应）
analyzed_at: 2026-10-01
priority_reason: 历史：克莱恩 2026-06-28 14:25 GMT+8 亲自发过 friendly check-in（仍无 maintainer 回应）；2026-08-02 已 close 销账
tags:
  - repo-profile
  - observability
  - ai-tracing
  - priority-followup
related:
  - ./pr-778-span-list-without-project-id.md
agent_guidelines:
  allow_unsolicited_pr: true
  require_signed_off: false
  require_cla: false
  require_changeset: false
  require_issue_first: false
  ai_policy: welcoming
  ai_assisted_disclosure: false
  human_required_in: []
  maintainer_vibe: slow  # 2026-10-01 重验: 我方 #778 8 周零人类响应; 但仓内部团队极活跃 (30d 337 merged)
  bot_review: entelligence
  ci_first_run_needs_approval: false
  default_branch: main
  response_time_h_median: null  # 未核实: 我方 PR 至今零人类响应, 无样本可算
  merge_rate_30d: 0.894  # 2026-09-01→2026-10-01: 337 merged / 40 closed-unmerged (GH search)
  close_keywords: []
  one_pr_friendly: false  # PR 评审慢，多 PR 风险高
misakanet_queries:
  - misakanet/lessons/contrib/friendly-checkin-template.md  # Ikalus1988 发的 friendly check-in 模板
misakanet_lessons: []
federation_status: declared-2026-07-02
verified_at: "2026-10-01T13:29:03Z"
evidence_urls:
  - https://github.com/future-agi/future-agi
  - https://api.github.com/repos/future-agi/future-agi
  - https://api.github.com/repos/future-agi/future-agi/releases/latest
  - https://api.github.com/repos/future-agi/future-agi/commits
confidence: high  # autogen from GH API; bump to medium if human-curated
last_release: v1.45.0
last_commit_sha: d794a49b
stars: 2103
agent_guidelines_evidence:
  allow_unsolicited_pr: https://github.com/future-agi/future-agi/blob/main/CONTRIBUTING.md
  require_issue_first: https://github.com/future-agi/future-agi/blob/main/CONTRIBUTING.md
  ai_policy: https://github.com/future-agi/future-agi/blob/main/CONTRIBUTING.md
  maintainer_vibe: https://github.com/future-agi/future-agi/pulls?q=is%3Apr+is%3Aclosed
  external_merge_rate_30: https://github.com/future-agi/future-agi/pulls?q=is%3Apr+is%3Aclosed
  close_keywords: https://github.com/future-agi/future-agi/pulls?q=is%3Apr+is%3Aclosed
---


# future-agi/future-agi

> Future AGI 是 AI 可观测性平台（tracing + evaluation）。  
> **AI 友好度**：中（entelligence-ai-pr-reviews bot 配置 = 半主动迎 AI）。  
> **zsxh1990 PR 经验**：1 个（#778，2026-08-02 自行 close，零 maintainer 响应）。  
> **2026-10-01 重验**：star 1.3k→2.1k，仓极活跃（30d 337 merged，今天连发 v1.45.0），但对外部 PR 静默。

---

## 1. 友好度画像（2026-10-01 重验）

- ✅ entelligence-ai-pr-reviews bot（半自动 AI review）
- ✅ 仓极活跃：30d 337 merged / 40 closed = 89.4%；版本号从 0.5.10 跳到 v1.45.0（release-please 风格日更）
- ⚠️ **对外部 PR 静默**：我方 #778 开 8 周零人类 maintainer 回复（bot review ≠ maintainer 通过）
- ⚠️ 近期 merged 样本（10 个）以内部/常驻贡献者为主（khushalsonawat、commitPirate、JayaSurya-27、cdileep23 + futureagi-release-bot）

---

## 2. zsxh1990 PR 进展

### 🔴 #778 [feat: enable span list view without project_id](https://github.com/future-agi/future-agi/pull/778) — closed-not-merged

| 维度 | 数据（2026-10-01 核实） |
|---|---|
| 创建 | 2026-06-04 10:55 UTC |
| 关闭 | **2026-08-02 05:41 UTC 由 zsxh1990 自行 close** |
| 状态 | closed，merged=false |
| +2 / -2 / 1 file | 极小 |
| entelligence review | 2 findings + 1 comment |

**关键时间线**：

| 时间 | 事件 |
|---|---|
| 2026-06-04 10:55 | PR 创建 |
| 2026-06-04 10:59 | entelligence AI 自动 review（2 findings：project=None NameError + NULL project_id EndUser lookup） |
| 2026-06-08 16:31 | zsxh1990："Good catch! Will push fix for the NULL project_id EndUser lookup issue." |
| 2026-06-08 16:38 | entelligence AI 第 2 轮 review |
| 2026-06-28 07:25 | **@Ikalus1988 亲自发 friendly check-in** |
| 2026-06-30 14:45 | 太阳 heartbeat 标记 priority |
| 2026-07-07 | zsxh1990 第二次 check-in |
| 2026-07-23 | zsxh1990 报告冲突并询问 "Is this feature still needed?"（上游已大改） |
| 2026-08-02 05:41 | **zsxh1990 自行 close**："open for 8 weeks with no response to conflict resolution question. Happy to reopen if there's interest." |

**克莱恩 6/28 14:25 GMT+8 发的 check-in 原文**：

> "Hi team — friendly check-in on this one 🙂  
> 
> It's been a couple weeks since the PR was opened. The bot review flagged two items (project=None NameError, NULL project_id EndUser lookup) which I've addressed.  
> 
> Happy to make any adjustments if there's feedback from the human review."

---

## 3. 提 PR 方向

### 🥇 tracing 增强

- span 批量导出优化
- 跨服务 trace 关联
- cost tracking

### 🥈 evaluation 工具

- LLM-as-judge 模板
- 人工反馈接入
- benchmark dashboard

---

## 4. 处置结论（2026-10-01 重验）

**已完结**：#778 于 2026-08-02 按 ClawSweeper 优雅退出规则自行 close（8 周零回应，含一次冲突确认问询）。

**教训（可复用）**：
- bot review（entelligence）积极 ≠ maintainer 会看
- 上游大改导致冲突后再问 "still needed?" 仍无回应 → 就是无声拒绝，close 是正确动作
- 本仓内部开发极活跃（30d 337 merged）但对外部小 PR 路过型无视——**下次投递前先在 issue 确认需求，别直接开 PR**

**如要重启**：先确认 span list 需求是否已被内部实现（仓 2 个月 337 个 merge，很可能已覆盖），再决定是否 reopen。

---

## 5. 关联文档

- [OKF bundle 根入口](../index.md)
- [PR #778 案例深读](./pr-778-span-list-without-project-id.md)