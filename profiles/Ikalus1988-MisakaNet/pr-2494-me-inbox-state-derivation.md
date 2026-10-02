---
type: PR Case Study
title: "MisakaNet #2494 — me_inbox 转换判定对着不存在的数据源查状态"
description: "misakanet_me_inbox 的转换判定读不存在的 JSONL 与 0 命中的 meta 字段，永远答 pending 且不报错；被维护者点出文件缺失后复核出同类字段问题——state-derived-from-nonexistent-source 的实例"
repo: Ikalus1988/MisakaNet
pr_number: 2494
pr_url: https://github.com/Ikalus1988/MisakaNet/pull/2494
author: zsxh1990
final_status: open
opened_at: '2026-09-30T07:08:28Z'
schema_version: rounds-v0.5.0
verified_at: '2026-10-01T13:48:14Z'
evidence_urls:
  - https://github.com/Ikalus1988/MisakaNet/pull/2494
  - https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5911941644
  - https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5926891078
  - https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5927372088
confidence: high
tags: [pr-case-study, misakanet, data-source, silent-default, status-lookup, design-feedback]
rounds:
  - round: 1
    action: open
    delta:
      kind: code_change
      value: "新增 misakanet_me_inbox（本地 server）：读 data/contribution_queue.jsonl + data/intake_receipts.jsonl，及 meta.intake_id/contrib_id/source_issue/related_issues 判定转换状态"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/pull/2494
      confidence: high
    timestamp: '2026-09-30T07:08:28Z'
  - round: 2
    action: human_review
    delta:
      kind: no_code_change
      value: "维护者 comment 5911941644：想法接受但按现状合并跑不起来——工具没进托管端 /mcp；两个 JSONL 在 main 上不存在，永远答 pending；submit_intake 的 answered 通道已通，缺的是入口+告知"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5911941644
      confidence: high
    maintainer_action: "逐条指出 3 个硬问题（位置/数据源/已有通道），给出更小做法"
    timestamp: '2026-09-30T13:08:26Z'
  - round: 3
    action: amend
    delta:
      kind: code_change
      value: "comment 5926891078：逐条复核认错（git cat-file -e 两个 ABSENT）；同类 bug 扩展修复——meta 四字段 461 条命中 0/0/0/0 而 provenance 428；fall-through not_found→unknown"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5926891078
      confidence: high
    timestamp: '2026-10-01T07:34:10Z'
  - round: 4
    action: decision
    delta:
      kind: code_change
      value: "comment 5927372088：委托既有 lookupIntakeConversion()（intake_receipt.py 忠实移植、此前从未被调用）；三套响应契约并存 → 列对照表 + 候选形状，把 canonical 选择抛回维护者，不猜着重写测试"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5927372088
      confidence: high
    timestamp: '2026-10-01T08:05:31Z'
close_decision:
  status: pending
  reason: "PR 仍 open；canonical 响应契约等维护者拍板，拍板前不重写 tests（见 success-patterns/ask-when-contracts-fork.md）"
  decided_at: null
  actor: zsxh1990
links:
  - type: anti-pattern
    target: anti-patterns/state-derived-from-nonexistent-source.md
  - type: success-pattern
    target: success-patterns/ask-when-contracts-fork.md
---

## Case #2494: me_inbox 的状态判定对着不存在的源查询

**PR**: Ikalus1988/MisakaNet#2494 — feat(mcp): add misakanet_me_inbox for agent-readable inbox (#2056)

**失败（round 1）**：`misakanet_me_inbox` 的转换判定从不存在的数据源推导状态，而且两种形态都不抛异常：

1. **文件形态**：读 `data/contribution_queue.jsonl` 与 `data/intake_receipts.jsonl`——
   维护者核过 `origin/main`，两个文件都不存在（本地工作树里那个是未跟踪残留）。
   缺文件 = 正常 miss → 落默认返回，于是**永远答 `pending`**，无任何报错；
2. **字段形态**（round 3 复核出的同类 bug）：转换判定扫
   `meta.intake_id` / `contrib_id` / `source_issue` / `related_issues`——
   461 条 lesson 实测命中 0/0/0/0，而真实存在的 `provenance` 命中 428。
   缺 key = 正常 miss → 同样落入默认返回。

**为什么是 `state-derived-from-nonexistent-source` 的实例**：
「从数据源 X 推导状态」的功能在 X 不存在时不失败、只永远返回默认状态；
`if not row: return {"status": "pending"}` 把「查不到」和「尚未发生」混成同一个返回，
功能看起来正常但永不生效。本例把该反模式的两种触发形态都占了——
不存在的文件、0 命中的字段——而且**正确的实现在同文件里就有**
（`lookupIntakeConversion()`，`scripts/intake_receipt.py` 的忠实移植），只是没人调用。

**修复方向（round 3/4）**：删掉 JSONL 依赖；委托 `lookupIntakeConversion()` 读真实存在的
`provenance.issue/related/source`；fall-through 从 `not_found` 改 `unknown` 并带 note
（已转化的 intake 多数不留 backlink，absence 不是 evidence of absence）；
契约分叉按 `ask-when-contracts-fork` 处理。

**Key Learning**：
1. 驱动状态的字段/文件先测命中率再设计查询：`grep -rh '^\s*<field>:' lessons/ | wc -l`、
   `git cat-file -e <branch>:<path>`（本次用 GitHub contents API 404 复核）；
2. 命中为 0 的字段不能驱动状态；查不到与尚未发生必须是两个可区分的返回；
3. 一句话评审信号：*这个功能是不是太一致了？100% 同一状态 = 它没有在工作。*

**Verification（2026-10-01 真跑）**：

```bash
# 文件在 main 上确实不存在（GitHub contents API）
gh api repos/Ikalus1988/MisakaNet/contents/data/contribution_queue.jsonl 2>&1 | head -1
# → {"message":"Not Found", ... "status":"404"}gh: Not Found (HTTP 404)

# （在 MisakaNet 检出根目录）字段命中率复测：四个判定字段仍 0，provenance 433 / 470 篇
for f in intake_id contrib_id source_issue related_issues provenance; do printf "%s " "$f"; grep -rh "^[[:space:]]*$f:" lessons | wc -l; done
# → intake_id 0 / contrib_id 0 / source_issue 0 / related_issues 0 / provenance 433
```
