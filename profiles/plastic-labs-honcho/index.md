---
type: Repo Profile
title: plastic-labs/honcho PR 模式分析
description: honcho 仓 AI 友好度 + zsxh1990 PR #801 进展
repo: plastic-labs/honcho
url: https://github.com/plastic-labs/honcho
star: 7424
language: Python
zsxh_pr_count: 1
status: closed-no-merge  # 2026-10-01 重验: #801 已于 2026-08-07 由 maintainer Rajat-Ahuja1997 关闭（gap 已被 crud.delete_session 覆盖）
data_source: zsxh PR #801
analyzed_at: 2026-10-01
evidence_urls:
  - https://github.com/plastic-labs/honcho
  - https://api.github.com/repos/plastic-labs/honcho
  - https://api.github.com/repos/plastic-labs/honcho/pulls/801
  - https://api.github.com/repos/plastic-labs/honcho/issues/801/comments
  - ./pr-801-queue-purge.md
confidence: high  # zsxh1990 PR #801 全程 4 rounds + close 理由已核实
verified_at: 2026-10-01T13:29:03Z
tags:
  - repo-profile
  - ai-memory
  - python
  - fastapi
  - sqlalchemy
related:
  - ./pr-801-queue-purge.md
agent_guidelines:
  allow_unsolicited_pr: false  # 2026-10-01 重验: 新 CONTRIBUTING 强制 issue + maintainer-approved 标签, 无则 72h 自动关
  require_signed_off: false
  require_cla: false  # 2026-07-02 GH API 核实：CONTRIBUTING.md 存在但无 CLA 条款，仅 AGPL-3.0 license
  require_changeset: false
  require_issue_first: true  # 2026-10-01 重验: "Every pull request needs an issue, and that issue needs the maintainer-approved label"
  ai_policy: conditional  # 2026-10-01 重验: 新增 "If you're an agent" 专节 — 欢迎 agent 但强制 gate + 禁止谎报测试
  ai_assisted_disclosure: false
  human_required_in: []
  maintainer_vibe: friendly  # 2026-10-01 重验: Rajat-Ahuja1997 带技术论据礼貌关 PR, 并主动另开修复
  bot_review: coderabbit
  ci_first_run_needs_approval: false
  default_branch: main
  response_time_h_median: null  # 未核实: 我方 #801 人类首条回复即 8 周后的 close 评论
  merge_rate_30d: 0.921  # 2026-09-01→2026-10-01: 105 merged / 9 closed-unmerged (GH search)
  close_keywords:
    - "please add tests"
    - "AsyncSession"
    - "needs-approved-issue"
  one_pr_friendly: false  # 2026-10-01 重验: 无 maintainer-approved issue 的 PR 72h 自动关
misakanet_queries:
  - misakanet/lessons/contrib/default-parameter-trap.md  # honcho #801 db 默认参数陷阱已入 MisakaNet
misakanet_lessons:
  - id: default-parameter-trap
    contributed_via: zsxh1990/honcho#801
    absorbed_at: 2026-06-21
federation_status: declared-2026-07-02
# verified_at 唯一值见上（2026-10-01 重验；原 07-02/07-06 重复键已合并）
last_release: v3.2.1
last_commit_sha: 37e383e1
stars: 7424
agent_guidelines_evidence:
  allow_unsolicited_pr: https://github.com/plastic-labs/honcho/blob/main/CONTRIBUTING.md
  require_issue_first: https://github.com/plastic-labs/honcho/blob/main/CONTRIBUTING.md
  ai_policy: https://github.com/plastic-labs/honcho/blob/main/CONTRIBUTING.md
  maintainer_vibe: https://github.com/plastic-labs/honcho/pulls?q=is%3Apr+is%3Aclosed
  external_merge_rate_30: https://github.com/plastic-labs/honcho/pulls?q=is%3Apr+is%3Aclosed
  close_keywords: https://github.com/plastic-labs/honcho/pulls?q=is%3Apr+is%3Aclosed
---

# plastic-labs/honcho

> Honcho 是 [Plastic Labs](https://www.plastic-labs.com/) 的 AI agent 记忆/上下文层（FastAPI + SQLAlchemy）。  
> **AI 友好度**：条件式欢迎（新 CONTRIBUTING 有 "If you're an agent" 专节：欢迎 agent，但强制 issue-gate）。  
> **zsxh1990 PR 经验**：1 个（#801，2026-08-07 被 maintainer 带论据礼貌关闭）。  
> **技术栈**：Python 3.11+ / FastAPI / SQLAlchemy 2.0 async / Pydantic v2。  
> **2026-10-01 重验**：star 5.7k→7.4k；**贡献规则大改**——必须先拿 `maintainer-approved` issue。

---

## 1. 友好度画像（2026-10-01 重验）

- ✅ **无 CLA**（2026-07-02 核实 + 2026-10-01 新 CONTRIBUTING 仍无 CLA 条款，AGPL-3.0）
- ✅ CodeRabbit bot 配置（自动 PR review，公开讨论友好）
- ✅ 维护者友好且讲理：#801 被 close 时给出具体技术论据（`crud.delete_session` 已覆盖 gap），并主动为剩余缺口另开修复
- ✅ 仓活跃：30d 105 merged / 9 closed = 92.1%
- 🔴 **重大规则变更（新 CONTRIBUTING.md）**：**每个 PR 必须关联 issue，且 issue 带 `maintainer-approved` 标签**。
  不满足 → 打 `needs-approved-issue` 标签 + 72 小时内不补齐自动 close。
- 🔴 **"If you're an agent" 专节**：agent 必须先 `gh issue view <N>` 验证 gate；禁止"PR 先开、issue 后补"；
  **禁止谎报测试**（"Do not report checks you did not run"）；建议直接用仓内 `skills/pre-pr/SKILL.md` 门禁
- ⚠️ Discord 是最快路径（"by a wide margin"），maintainer 在 Discord 比 issue tracker 活跃

---

## 2. zsxh1990 PR 进展

### 🔴 #801 [feat: add queue purge endpoint for stranded work units](https://github.com/plastic-labs/honcho/pull/801) — closed-not-merged

| 维度 | 数据（2026-10-01 核实） |
|---|---|
| 创建 | 2026-06-12 01:44 UTC |
| 关闭 | **2026-08-07 18:35 UTC 由 maintainer @Rajat-Ahuja1997 关闭** |
| 状态 | closed，merged=false |
| +283 / -0 / 3 files | 适中 |
| comments: 5+ / review_comments: 3 | 互动良好 |

**关闭理由（maintainer 原文要点，2026-08-07）**：

> "thanks for the contribution, but I think the gap that this addresses is already closed.
> `crud.delete_session` already deletes all session's queue items and ActiveQueueSession rows...
> One gap here is that queue items created by a dream are currently not deleted... but I will file that fix separately.
> Closing this and marking #799 as already fixed"

**结论**：技术性礼貌 close（需求被上游实现抢先），**不是态度问题**。honcho 维护者画像维持 friendly。

**关键反馈**：

1. **2026-06-12 CodeRabbit 第 1 轮**：标 2 个 actionable + 1 个 outside-diff
2. **2026-06-20 14:18 zsxh1990 自报**：
   > "Addressed both CodeRabbit findings from the initial review — thanks for the catch, they were real bugs.
   > 
   > **🔴 Critical (DB session injection) — fixed in `7ac3afe`**
   > The default value `db: AsyncSession = db` was picking up the `src.db` *module* (from `from src import db, models`),"
3. **2026-06-20 14:24 CodeRabbit 第 2 轮**：再标 1 个 finding
4. **2026-07-02 / 07-07 / 08-04 / 08-06**：zsxh1990 四次 friendly ping（附 CI 绿证据）
5. **2026-08-07**：maintainer Rajat-Ahuja1997 带论据 close（见上）

### 关键教训（内化为 MEMORY.md §8）

**PR 默认参数陷阱**：`db: AsyncSession = db` 看着对，**实际 import 冲突**
- `from src import db, models` 的 `db` 是 module
- `from src.dependencies import db` 的 `db` 才是 `Depends(get_db)` 代理
- 改前必用 basedpyright 验证 default value 类型匹配

**ORM anti-pattern**：`select(Model).scalars().all() → len()` 应改 `select(func.count())`

详细案例见 [pr-801-queue-purge.md](./pr-801-queue-purge.md)。

---

## 3. 提 PR 方向（2026-10-01 按新 CONTRIBUTING 重排）

> **硬门禁**：先在 [maintainer-approved issue 队列](https://github.com/plastic-labs/honcho/issues?q=is%3Aissue+is%3Aopen+label%3Amaintainer-approved) 认领，或开 issue 等 triage 打标；PR 必须 `Fixes #N` 关联。**没有 approved issue 的 PR = 72h 自动关。** 小例外仅限 typo / 断链 / 明显错例。

**外部贡献最易落地的轴（CONTRIBUTING 原文）**：**Ubiquity**（集成、自托管粗糙面、向量库/推理后端、SDK 易用性）与 **Developer experience**。最难接受：deriver prompts / dialectic / dreamer 等推理管线改动（内部 eval 度量 + 高冲突，须先 Discord）。

### 🥇 bug fix（maintainer-approved 队列内）

- 当前 open bug 示例：#1270 embedding reconciler 批次污染、#1250 非 TTY 时 wizard 误触发、#1260 context-limit 错误规范化
- FastAPI 异步陷阱、SQLAlchemy session leak、Pydantic v2 迁移遗留

### 🥈 Ubiquity / 集成类

- 向量库 / 推理后端适配、自托管修复、SDK 人体工学
- 理由：additive、极少撞 in-flight 工作（CONTRIBUTING 明说）

### 🥉 docs 改进

- typo/断链/错例可直接 PR；成规模的 docs 仍走 issue-gate

---

## 4. SOP（与 OpenClaw/uv 通用差异）

| 维度 | honcho 特色 |
|---|---|
| **Issue gate** | PR 前必须有 `maintainer-approved` issue（72h 自动关无 gate 的 PR） |
| CI | 跑 SQLAlchemy 2.0 async 测试 + 基于 pytest-asyncio |
| Type check | 必过 basedpyright/mypy strict（新 CONTRIBUTING：`uv run ruff check src/` → `uv run basedpyright` → pytest） |
| Commit msg | Conventional Commits |
| CLA | **无**（2026-07-02 + 2026-10-01 两次核实，AGPL-3.0） |
| PR body | 仓内 `skills/pre-pr/SKILL.md` 定格式：Description / Proofs / Fixes；测试命令必须真实跑过 |

---

## 5. 反模式

- ❌ FastAPI default value 写 `db: AsyncSession = db`（撞 #801 已修 bug）
- ❌ `.scalars().all() → len()` 模式（CodeRabbit 必抓）
- ❌ 同步 SQLAlchemy（项目全 async）
- ❌ uv sync 后不检查 `uv.lock` 改动（MEMORY.md §10）

---

## 6. 关联文档

- [OKF bundle 根入口](../index.md)
- [PR #801 案例深读](./pr-801-queue-purge.md)