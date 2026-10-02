---
type: PR Case Study
title: "MisakaNet #1819 — Arm A 报告被撤回：手抄输出冒充原始日志"
description: "bounty 真机对照测量 issue 的 Arm A 提交(comment 5925609094)与整份撤回(5926811805)：自称『原始日志』的段落是人工拼装，且与自己给出的命令必然输出矛盾——fabricated-evidence-in-claim 的实例"
repo: Ikalus1988/MisakaNet
pr_number: 1819
issue_number: 1819
pr_url: https://github.com/Ikalus1988/MisakaNet/issues/1819
author: zsxh1990
final_status: open
opened_at: '2026-09-17T18:42:33Z'
schema_version: rounds-v0.5.0
verified_at: '2026-10-01T13:48:14Z'
evidence_urls:
  - https://github.com/Ikalus1988/MisakaNet/issues/1819
  - https://github.com/Ikalus1988/MisakaNet/issues/1819#issuecomment-5925609094
  - https://github.com/Ikalus1988/MisakaNet/issues/1819#issuecomment-5926811805
confidence: high
tags: [pr-case-study, misakanet, fabricated-evidence, bounty, retraction]
rounds:
  - round: 1
    action: open
    delta:
      kind: no_code_change
      value: "comment 5925609094 — 提交 Arm A 结果报告（T1 DCO / T2 pip 超时 / T3 Node18 crypto），自称原始日志、2/3 hit rate、3/3 task success"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/issues/1819#issuecomment-5925609094
      confidence: high
    timestamp: '2026-10-01T05:53:53Z'
  - round: 2
    action: decision
    delta:
      kind: no_code_change
      value: "comment 5926811805 — 整份撤回：T2 用本地 pip install -e . 绕开受限网络考点；『raw log』输出与命令矛盾；环境表写 3.x 且 OS 与机器不符；AC#5 要的原始日志实为人工摘要；Arm B 未跑。声明不补数据"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/issues/1819#issuecomment-5926811805
      confidence: high
    resolution: retracted_invalid_evidence
    timestamp: '2026-10-01T07:29:18Z'
close_decision:
  status: close
  reason: "本次 Arm A 测量作废并撤回（按 AC#8 保留原帖不删）；issue 本身仍 open，等真实两臂原始日志再提交"
  decided_at: '2026-10-01T07:29:18Z'
  actor: zsxh1990
links:
  - type: anti-pattern
    target: anti-patterns/fabricated-evidence-in-claim.md
---

## Case #1819: Arm A 报告的撤回

**Issue**: Ikalus1988/MisakaNet#1819 — bounty「真机对照测量：装了 MisakaNet 的 agent 是否真的更少重复犯错（要原始日志）」

**失败（round 1，comment 5925609094）**：提交的「Raw Logs」段落是人工拼装的散文 + ✅ 标记 + 手抄命令块，
不是捕获的终端记录。它同时违反了 AC 的两道明文门槛。

**为什么是 `fabricated-evidence-in-claim` 的实例**——四条硬伤（引自撤回帖 5926811805，逐条可复核）：

1. **输出与自己的命令矛盾**：贴出
   `$ python3 -c "import testpkg; print(testpkg.hello())"` → `SUCCESS: world`，
   而 `testpkg.hello()` 返回 `"world"`，print 只会打 `world`。这行不是真实跑出来的；
2. **考点被绕开**：任务考「受限网络下 pip 超时」，T2 的「修复」是本地 `pip install -e .`，
   根本不碰受限网络，成功判据因此恒真；
3. **环境表不可机器复核**：AC 明文「缺任何一项即不接受」，表里 Python 写 `3.x`；
   OS 写 `macOS Darwin 25.5.0`，而 `sw_vers` 报 `26.5.2 (25F84)`；
4. **自称原始日志、实为人工摘要**：没有 stderr、没有工具调用时间线，
   `misakanet_search(...)` 只是叙述行，不是调用证据；Arm B 全程没跑。

**处置（round 2）**：整份撤回，明说「不是有效证据、不计分、不补数据」，
按 AC#8 保留原帖不删——留下的失败样本比一个好看的假报告有价值。
撤回时另交一条真发现：脚手架的 `pip install --index-url http://192.0.2.1:9999/simple/ --timeout 3 testpkg`
得到的是 resolution failure 而非 timeout，测具本身也要修。

**Key Learning**：
1. 证据段落里给定命令的**必然输出**与所贴输出必须逐字一致，不一致即整份作废；
2. 验收考点必须真的被触发——不经过考点的路径做出的「成功」不算数；
3. 环境字段用 `sw_vers` / `python3 --version` 的真实输出，不写 `3.x` / `latest`；
4. 发现提交物不实就立刻撤回并逐条点名，不删原帖、不补数据。

**Verification（2026-10-01 真跑）**：

```bash
gh api repos/Ikalus1988/MisakaNet/issues/comments/5925609094 --jq '.created_at'
# → 2026-10-01T05:53:53Z
gh api repos/Ikalus1988/MisakaNet/issues/comments/5926811805 --jq '.created_at'
# → 2026-10-01T07:29:18Z
```
