---
type: Documentation
title: 案例仓库充实方案 — 目标 · 频次 · 判据
tags: [planning, roadmap, evidence, cadence, case-enrichment]
description: "案例库充实的目标排序、执行频次与可验证判据；含 2026-10-01 基线数据"
created: 2026-10-01
updated: 2026-10-01
confidence: high
---

# 案例仓库充实方案 — 目标 · 频次 · 判据

> 生成于 2026-10-01。基线数据来自当日 `validate.py` 与目录统计，非估算。

## 一、现状基线

| 库 | 规模 | 证据状态 |
|---|---|---|
| `anti-patterns/` | 61 md + 190 json | md 带 `evidence:` 列表；json 为结构化 PR 记录 |
| `success-patterns/` | 436 md | 带 `source_url`，多数无逐条证据 |
| `review-cases/` | **302 json** | **`verified_at` / `evidence_urls` 覆盖 0** |
| `profiles/` | 67 | 0 个 `needs_reverify`（2026-10-01 六个全部重验销账） |
| 根 `index.md` | 67 行画像 1:1 | ✅ #40 修复后与 `profiles/` 一致 |

**门禁状态**：`validate.py --strict` exit 0 · `--enforce-evidence` exit 0

### 两个必须先说清的事实

1. **`--enforce-evidence` 目前是假绿。** 它只校验带 `rounds` 的 markdown，而 302 条 review-case **全是 JSON**，没有 frontmatter，门根本没扫到它们。所以"证据覆盖 0"不是被门放过，而是**门没覆盖**。
2. **orphan 数已从记忆里的 543 降到 2。** 前一阶段的清理有效。剩下 2 条是 2026-10-01 新增的（见"已入库"）。

---

## 二、已入库（2026-10-01，本会话实战素材）

### 反模式 3 条

| key | 触发信号 | severity |
|---|---|---|
| `fabricated-evidence-in-claim` | 「原始日志」是手工拼装、输出与命令对不上 | **critical** |
| `state-derived-from-nonexistent-source` | 状态查询对所有输入返回同一值 | high |
| `pr-scope-collides-with-landed-work` | 评审说"大部分 diff 上游已有" | medium |

### 成功模式 2 条

| key | 核心动作 |
|---|---|
| `retract-early-keep-original-visible` | 逐条撤回 + 保留原帖 + 明说"未补数据" |
| `status-doc-re-audit-row-by-row` | 被要求只改版本号时，逐行给线上实测证据；**主动留出无法举证的行并说明** |

> 后者那句「我宁愿空一行也不写没证据的状态」是整条模式最有价值的部分——它让表里其余行变得可信。

---

## 三、目标（按 ROI 排序）

### G1 · 让证据门真的覆盖 review-case ｜ 最高

**问题**：302 条 JSON 记录零证据字段，而 `--enforce-evidence` 假绿。

**做法**：
1. 给 `validate.py` 加一条 check，扫 `review-cases/*.json`，要求每条含：
   - `verified_at`（ISO-8601）
   - `evidence_urls`（http(s) URL 列表，指向真实 PR/issue）
2. 新增记录强制带上；存量分期补，不必一次做完
3. 让 `--enforce-evidence` 覆盖 JSON，使假绿变真绿

**判据**：`evidence_urls` 覆盖率每周提升，且 `--enforce-evidence` 对缺失项真的 exit 1。

### G2 · 压 orphan 至 0 ｜ 高

**现状**：新增 2 条 orphan（被 64 个 case study 引用 0 次）。

**做法**：每条 anti-pattern 落地时，同步在至少一个 review-case / case study 里引用它的 key。
**判据**：`validate.py` 的 orphan 警告数 = 0。

### G3 · profile 重验消账 ｜ ✅ 已完成（2026-10-01，#43）

**结果**：6 个 profile 全部真重验并销账，`needs_reverify` 标记数 = 0。
重验对象：astral-sh-uv / e2b-dev-e2b / future-agi-future-agi / harbor-framework-harbor /
plastic-labs-honcho / sourcebot-dev-sourcebot。每个仓用 gh api 只读拉了真实状态
（stars / pushed / merged·closed PR / open issues / releases / 我方 PR 结局），
更新了画像正文（star、活跃度、合并习惯、维护者态度、近期 PR、贡献政策），
`analyzed_at` 更新为真实重验日 2026-10-01。

**重验发现的重大漂移**（详见各 profile "2026-10-01 重验" 段）：
- 4 个"在飞" PR 全部已终结：#1383/#778 自行 close（6-8 周零响应），#801 被 maintainer 带论据关闭，
  仅 harbor #2121 仍 open（95d 零人类响应）
- honcho 贡献规则大改：强制 issue + `maintainer-approved` gate，无 gate 72h 自动关
- uv AI_POLICY.md 迁至 astral-sh/.github；`bot:ai-policy-close` 执法 30d 占 close 的 47%
- harbor 新增 Golden Rule（须自证理解 + 披露 agent）；sourcebot UI/core 须先 design review

**注意**：`needs_reverify` 只是**声明债务，不是偿还**——本次是偿还动作本身：真跑了上游、真改了正文，不是改日期。

### G4 · 扩充"我方被拒/被纠错"的案例 ｜ 中

**原则**：最高价值的案例是**自己踩的**，不是别人的。本会话一次就产出 5 条，因为全程在记录
「失败→根因→修复→验证」。

**优先补的方向**：
- 竞品撞车（同一 bounty 多 PR 时如何判输赢、何时该拆 PR）
- 维护者给了设计意见后的返工（#2494 的契约分叉是典型）
- 自己内容里的事实错误（agentcap/codesign 那两条：**Verification 命令根本跑不通**）

### G5 · 让 coach 在提交前自动命中 ｜ 中长期

**现状**：`coach` 与 `harvest` 命令已有，但没接入日常提交路径。

**做法**：把反模式的 `trigger_keywords` 接到 coach 的检查表上，使提交前自检能命中
`fabricated-evidence-in-claim`、`state-derived-from-nonexistent-source` 这类**结构性**问题
（而不只是标题/标签的表层信号）。

---

## 四、频次编排

| 节奏 | 动作 | 产出 | 判据 |
|---|---|---|---|
| **每次提交前** | `python3 -m prgenius coach "$TITLE" --repo <r> --body "$BODY"` | exit 0/1 | 高风险即修 |
| **每次被拒/被纠错后** | `python3 -m prgenius harvest <repo> <N> --type <lesson\|anti-pattern>` | 1 条草稿 | 编辑后入库，补 `evidence` |
| **每日心跳（2 次）** | 走 `zsxh-todo-sweep` skill 的 8 步 | 通知分类 + 待办处置 | 对外动作等点名 |
| **每周一次** | ① 清 orphan（补引用）② 补 review-case 证据字段 ③ 重验 1–2 个 profile | 3 项各自有 diff | 三项目标数下降 |
| **每月一次** | 全量 `validate --strict --enforce-evidence` + 重审本方案目标是否还成立 | 一份门禁报告 | 两个门都真绿 |

### 建议的每周固定窗口

- **周三**：orphan 清理 + 证据字段补录（纯数据工作，不占思考带宽）
- **周日**：profile 重验 + 案例复盘（把本周踩的坑写成模式）

把"写案例"绑在**被拒/被纠错之后**而不是定期硬写——素材在那时最完整，硬写出来的多半是空话。

---

## 五、明确不做

1. **不为凑指标而批量生成案例。** 690 条 success-patterns 里若无 `source_url` 支撑，数量没有意义。
2. **不伪造 `analyzed_at` / `evidence_urls` / 测量数据。** 宁可 `--strict` 红着。
3. **不把"只改版本号"当成完成。** 状态文档的内容必须逐行可举证。
4. **不删除失败记录。** 撤回帖保留原帖，反模式保留来源 PR。

---

## 六、一句话版本

> **让证据门覆盖它现在看不见的 302 条记录，把孤儿压到 0，把 6 个过期画像销账；
> 案例靠"被拒后 harvest"产生而不是定期硬写；每天扫待办、每周清债务、每月验门禁。**
