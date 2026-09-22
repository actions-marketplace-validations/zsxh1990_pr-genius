---
type: Anti-Pattern
tags: [contribai, issue-selection, due-diligence, auto-close, competition]
key: contribai-issue-claim-no-due-diligence
symptom: |
  认领 issue 前不做可行性评估，直接评论 "I'd like to work on this"。
  结果：PR 被 auto-close bot 关闭、被竞品 PR 抢先、或维护者自己已修。
  典型表现：一次认领 5 个 issue，4 个不可行。
root_cause: |
  跳过了认领前的 6 步可行性检查流程：
  1. 没搜竞品 PR（duplicate-pr 反模式）
  2. 没检查仓库 auto-close 策略（first-time-large-repo 反模式）
  3. 没确认账号权限（哪个账号能绕过 bot）
  4. 没读源码确认是 bug 还是 by design（not-a-real-bug 反模式）
  5. 没检查 issue 评论区竞争态势
  6. 没用 pr-genius issue 审核 issue 质量
trigger_keywords:
  - "I'd like to work on this"
  - "I'll open a PR"
  - "claimed"
  - "auto-closed"
  - "This repo only keeps pull requests open when they come from a maintainer"
fix_action: |
  认领前必跑完整 6 步检查（见下方「认领 Coach 流程」）。
  任何一步红灯 → 放弃该 issue，换下一个。
source_pr: "modelcontextprotocol/python-sdk #3437/#3464/#3439 + servers #4763 + pr-agent #3114 (2026-09-07 全部失败)"
prevention: |
  认领 issue 是投资行为，不是声明行为。
  每次认领前必须完成 6 步可行性检查，全部绿灯才能评论认领。
created: 2026-09-07
learned_at: 2026-09-07
source_url: https://github.com/zsxh1990/pr-genius/tree/main/anti-patterns/contribai-issue-claim-no-due-diligence.md
updated: 2026-09-07
confidence: high

---

## 实证：2026-09-07 认领事故

一次认领 5 个 issue，4 个不可行：

| Issue | 失败原因 | 命中反模式 |
|---|---|---|
| python-sdk #3437 | 3 个 PR 已被 auto-close bot 关闭 | duplicate-pr + first-time-large-repo |
| python-sdk #3464 | 1 人已声明 + auto-close bot | duplicate-pr + first-time-large-repo |
| python-sdk #3439 | auto-close bot 必定关闭社区 PR | first-time-large-repo |
| servers #4763 | 竞品 PR #4764 已提交 | duplicate-pr |
| pr-agent #3114 | 竞品 PR #3121 已 accepted | duplicate-pr |

**根因**：跳过了认领前的可行性检查流程，直接评论认领。

## 关键发现：auto-close bot

python-sdk (modelcontextprotocol) 仓库有 auto-close 策略：
> "This repo only keeps pull requests open when they come from a maintainer, or from..."

社区 PR 被自动关闭，不进入 review 队列。核心维护者 @maxisbey 的 PR 合并速度中位数 0.9h，
但社区贡献者的 PR 在秒级被 bot 关闭。

**教训**：大仓（≥10k star）必须先检查已关闭 PR 的 bot 评论，确认社区 PR 是否被接受。

## 认领 Coach 流程（6 步门控）

认领任何 issue 前，必须完成以下 6 步检查。任何一步红灯 → 放弃。

### Step 1: Issue 质量审核

```bash
prgenius issue --repo <owner/repo> --number <N> --format text
```

- 质量分 ≥70 才继续
- 风险等级不是 high_risk 才继续

### Step 2: 竞品 PR 搜索

```bash
# 搜索同 issue 的已提交/已合并 PR
gh search prs --repo <owner/repo> --state all --sort updated --limit 20 \
  --json number,author,title,state

# 在结果中查找关键词匹配
# 如果有 OPEN 状态的竞品 → 红灯
# 如果有 MERGED 状态的竞品 → 红灯（已修复）
# 如果有 CLOSED 状态的竞品 → 检查关闭原因
```

- 无竞品 OPEN/MERGED PR → 绿灯
- 有竞品但已 CLOSED（非 duplicate）→ 黄灯，继续检查
- 有竞品 OPEN 或 MERGED → 红灯，放弃

### Step 3: Auto-close Bot 检查

```bash
# 查看最近关闭的 PR，找 bot 评论
gh pr list --repo <owner/repo> --state closed --limit 5 \
  --json number,author,title

# 逐个查看关闭原因
gh pr view <N> --repo <owner/repo> --json comments

# 关键词：
# - "auto-closed automatically"
# - "only keeps pull requests open when they come from a maintainer"
# - "require-linked-issue"
# - "stale"
```

- 无 auto-close bot → 绿灯
- 有 auto-close bot 但仅针对无 issue link 的 PR → 黄灯（确保 PR link issue）
- 有 auto-close bot 针对所有社区 PR → 红灯，放弃或用维护者账号

### Step 4: 账号权限确认

```bash
# 检查哪个账号能绕过 auto-close
# 方法：查看最近 MERGED 的社区 PR 作者
gh pr list --repo <owner/repo> --state merged --limit 10 \
  --json number,author

# 如果 merged PR 全是维护者 → 社区账号不可行
# 如果有非维护者的 merged PR → 检查该账号的特殊权限
```

- 我的账号有权限 → 绿灯
- 需要用另一个账号 → 切换账号后绿灯
- 所有账号都无权限 → 红灯，放弃

### Step 5: 竞争态势评估

```bash
# 检查 issue 评论区的认领声明
gh issue view <N> --repo <owner/repo> --json comments

# 关键词：
# - "I'd like to work on this"
# - "I'll open a PR"
# - "claimed"
# - "WIP"
# - "PR submitted"

# 检查已关闭竞品 PR 的评论（为什么被关？）
gh pr view <竞品PR> --repo <owner/repo> --json comments
```

- 无人认领 + 无竞品 PR → 绿灯
- 有人声明但无 PR → 黄灯（24h 内无 PR 则绿灯）
- 有 OPEN 竞品 PR → 红灯
- 竞品 PR 已 accepted/approved → 红灯

### Step 6: Bug 真实性验证

```bash
# 读源码确认是 bug 还是 by design
# 1. 找到相关代码
grep -rn "<keyword>" <repo-path>/src/

# 2. 读 maintainer 在 issue/邮件列表的评论
gh issue view <N> --repo <owner/repo> --json comments | grep -i "by design\|intended\|working as expected"

# 3. 写 failing test 复现（可选，但强烈推荐）
```

- 确认是 bug（有 failing test 或明确的错误行为）→ 绿灯
- 不确定（by design vs bug）→ 黄灯，先在 issue 区讨论
- 确认是 by design → 红灯，放弃

## 评分卡

| 检查项 | 权重 | 红灯 | 黄灯 | 绿灯 |
|---|---|---|---|---|
| Issue 质量 | 10% | <50 | 50-70 | ≥70 |
| 竞品 PR | 30% | OPEN/MERGED 竞品 | CLOSED 竞品 | 无竞品 |
| Auto-close | 20% | 全关社区 PR | 有条件关 | 不关 |
| 账号权限 | 15% | 所有账号无权 | 需切账号 | 当前账号有权 |
| 竞争态势 | 15% | 已 accepted | 已声明 | 无人认领 |
| Bug 真实性 | 10% | by design | 不确定 | 确认 bug |

**综合评分**：红灯任一项 → 放弃。黄灯 ≥2 项 → 谨慎。全部绿灯 → 认领。

## 与 pr-genius 工具的集成

pr-genius `issue` 命令只审核 issue 本身质量（描述完整性、标签、可复现性），
不审核**认领可行性**（竞品、auto-close、账号权限、竞争态势）。

建议 pr-genius 增加 `issue-viability` 或在 `issue` 命令中增加可行性维度。

## 关联反模式

- `contribai-duplicate-pr` — 竞品 PR 搜索
- `contribai-first-time-large-repo` — auto-close bot 检查
- `contribai-not-a-real-bug` — bug 真实性验证
- `contribai-stale-pr` — 竞品 PR 是否已过时

## Applicability

All repository sizes. Large repos (≥10k star) 尤其需要 Step 3 和 Step 4。