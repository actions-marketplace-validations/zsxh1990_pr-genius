---
type: Anti-Pattern
key: state-derived-from-nonexistent-source
tags: [data-source, silent-default, status-lookup, schema-drift]
description: "对着不存在的数据源查状态 → 永远返回默认值而非报错，功能看起来正常但永不生效"
symptom: "status lookup returns the same value for every input"
trigger_keywords:
  - "always pending"
  - "never updates"
  - "returns empty"
  - "works locally but not in CI"
  - "file not found but no error"
  - "key missing"
fix_action: "1) 先拿真实数据量命中率：grep 语料统计每个字段的出现次数、git cat-file -e <branch>:<path> 验文件；2) 命中为 0 的字段/文件不能驱动状态；3) 把「查不到」与「尚未发生」分成两个可区分的返回；4) 复用仓里已有的 lookup helper，别另写匹配器"
source_pr: "Ikalus1988/MisakaNet PR #2494 (comment 5927372088)"
severity: high
evidence:
  - "PR #2494 用 meta.intake_id / contrib_id / source_issue / related_issues 判定转换：461 条 lesson 实测命中 0/0/0/0，而真实存在的 provenance 命中 428"
  - "同一 PR 的更早版本读 data/contribution_queue.jsonl 与 data/intake_receipts.jsonl，两个文件在 upstream/main 上都不存在（git cat-file -e 确认 ABSENT）"
  - "两种形态都不抛异常：缺文件是正常 miss，缺 key 也是正常 miss，于是落入默认返回"
  - "同文件里已有正确实现 lookupIntakeConversion()（intake_receipt.py 的忠实移植），却从未被调用"
  - "结果 100% 一致：每个输入都答 pending，没有任何报错"
created: 2026-10-01
learned_at: 2026-10-01
source_url: https://github.com/Ikalus1988/MisakaNet/pull/2494
updated: 2026-10-01
confidence: high

---

## 反模式说明

"从数据源 X 推导状态"这个功能，在 X 不存在时**不会失败**，只会永远返回默认状态。
审查者读代码看到的是一个合理的 fallback，于是放行。

### 触发条件

- 状态查询对所有输入返回同一个值（尤其是"待处理"/"未找到"）
- 代码里出现 `repo / "data" / "something.jsonl"` 这类路径，但没人验证过它在默认分支上存在
- 从 frontmatter / JSON 取字段，但没人统计过这些字段在真实语料里的命中率
- 本地跑"正常"，CI 或生产上永远是默认值（本地有未跟踪的残留文件）

### 为什么会发生

设计文档说字段叫 `contrib_id`，实现照着写了，但语料里真正存在的是 `provenance.issue`。
**规格与数据脱节，而代码对脱节是静默的。**

同理，一个 `data/*.jsonl` 可能只存在于开发者的工作树（未跟踪），于是"本地测试通过"
掩盖了"仓库里根本没有这个文件"。

### 修复动作

**先测量，再设计查询：**

```bash
# 字段命中率（真实语料，不是规格）
grep -rh '^\s*<field>:' lessons/ | wc -l
# 文件是否真在目标分支上
git cat-file -e upstream/main:data/<file>.jsonl && echo EXISTS || echo ABSENT
```

**把 miss 与 not-yet 分开：**

```python
# 坏：miss 与未开始同一个返回
if not row: return {"status": "pending"}

# 好：查不到要说"无法判定"，并说明为什么
if not row:
    return {"status": "unknown",
            "note": "corpus carries no backlink; absence is not evidence of absence"}
```

**优先复用仓里已有的 lookup helper**——本次那个正确的实现就在同一文件里，只是没人调用。

### 判据（可自动化）

- 任一"驱动状态"的字段，全量命中数必须 > 0，且写进 PR 描述
- 任一"驱动状态"的文件路径，必须有 `git cat-file -e` 的 EXISTS 证据
- fall-through 的返回值必须与每一个真实状态**可区分**（不能等于某个合法状态）

**一句话评审信号**：*这个功能是不是太一致了？100% 同一状态 = 它没有在工作。*
