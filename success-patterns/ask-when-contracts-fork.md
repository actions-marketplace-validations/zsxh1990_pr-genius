---
type: Success Pattern
key: ask-when-contracts-fork
tags: [design-feedback, rework, contracts, maintainer, tests, self-audit]
description: "维护者给设计意见后的返工：同一个响应有三套契约并存（测试 / 处理器 / 评审意见）时，先列对照表把 canonical 选择抛回维护者，而不是猜一个去重写测试"
success_factors:
  - "对维护者每条意见先逐条复核再认错：git cat-file -e 查文件是否存在、grep 统计字段命中率，用证据说话"
  - "复核时发现同类 bug 就一并修：被点名的是两个 JSONL 缺失，扫出的是 meta 字段 0/461 命中——同一个「对着不存在的源查状态」"
  - "复用仓里已有的正确实现（lookupIntakeConversion()，intake_receipt.py 的忠实移植），不重写匹配器"
  - "契约分叉时列出三方词表对照 + 给出候选响应形状，把选择权交回维护者；canonical 未定前不重写测试"
  - "无争议的正确性修复先推（fall-through not_found→unknown，让 miss 与 not-yet 可区分），有争议的留下一轮"
repo_requirements:
  - "DCO sign-off (git commit -s)"
  - "对已指出的每条缺陷给出可复核证据（命令 + 真实输出）"
source_pr: Ikalus1988/MisakaNet#2494
created: 2026-10-01
learned_at: 2026-10-01
source_url: https://github.com/Ikalus1988/MisakaNet/pull/2494#issuecomment-5927372088
updated: 2026-10-01
confidence: high
---

## 成功案例

### PR #2494: me_inbox 的返工——先测量，再问 canonical

**背景**：维护者对 #2494 给出设计意见（comment 5911941644）：想法接受，但按现状合并跑不起来——
工具没进托管端 `/mcp`；`data/contribution_queue.jsonl` 与 `data/intake_receipts.jsonl`
在 main 上不存在，所以永远答 `pending`；现成的 `submit_intake` answered 通道已经通了。

**返工动作**（comment 5926891078 / 5927372088）：

1. **逐条复核而不是口头认错**：`git cat-file -e upstream/main:data/*.jsonl` → 两个 ABSENT，
   本地工作树里那个是未跟踪残留；依赖删掉。
2. **同 bug 类扩展修**：被点名的是 JSONL 文件，扫出 meta 字段命中率
   `intake_id / contrib_id / source_issue / related_issues = 0/0/0/0`，真实存在的 `provenance = 428`
   （2026-10-01 本地检出复测 470 篇 / 433，同一形态）——「对着不存在的源查状态」不止一处。
3. **复用已有正确实现**：`lookupIntakeConversion()` 就在同一文件里且从未被调用，
   它是 `scripts/intake_receipt.py` 的忠实移植，读真实存在的 citation 字段。
4. **契约分叉就抛回去**：tests / handler / 维护者评审各有一套 status 词表
   （`pending|resolved` vs `answered|pending|converted|unknown|not_found` vs
   `answered|converted|accepted|lesson_published`）。三套并存时**不猜**——
   列对照表 + 提一个候选响应形状 + 问哪套是 canonical，等拍板再重写测试。

**成功因素**：测量先行、同类扩展修、复用既有 helper、把选择权交回维护者。
截至 2026-10-01 维护者对 canonical 尚未回复，因此「成功」限定为——
没有对着猜出来的契约做会作废的测试重写，返工留下的每条结论都可复核。

## 可复用模式

1. 维护者给了设计意见 → 先把每条意见变成一条可复跑的检查，再逐条回应；
2. 复核发现同类缺陷 → 一并修，不只修被点名的那一处；
3. 仓里已有正确 helper → 复用，别写第二个匹配器；
4. 响应契约出现两套以上说法 → 列表 + 给候选 + 问 canonical，**不要用猜的方案重写测试**。

## 判据（每条都在 2026-10-01 真跑过）

```bash
# 决策点证据存在，且没跑偏日期
gh api repos/Ikalus1988/MisakaNet/issues/comments/5927372088 --jq '.created_at'
# → 2026-10-01T08:05:31Z

# （在 MisakaNet 检出根目录）字段命中率复测——四个声称字段依旧 0 命中
for f in intake_id contrib_id source_issue related_issues provenance; do printf "%s " "$f"; grep -rh "^[[:space:]]*$f:" lessons | wc -l; done
# → intake_id 0 / contrib_id 0 / source_issue 0 / related_issues 0 / provenance 433
```
