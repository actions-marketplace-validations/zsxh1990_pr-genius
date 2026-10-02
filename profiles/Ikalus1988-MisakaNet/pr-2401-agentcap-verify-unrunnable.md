---
type: PR Case Study
title: "MisakaNet #2401 — 合入的 lesson 里 Verification 命令跑不通（自审发现）"
description: "五篇 bounty lesson 合入后，自审发现 agentcap 篇的 verify 字段与 Verification 节调用的 CLI 根本不存在于 pip 安装来源，且 || echo PASS 兜底让它空转绿——unrunnable-verification-command 的实例"
repo: Ikalus1988/MisakaNet
pr_number: 2401
pr_url: https://github.com/Ikalus1988/MisakaNet/pull/2401
author: zsxh1990
final_status: closed-merged
merged_at: '2026-09-28T13:09:12Z'
schema_version: rounds-v0.5.0
verified_at: '2026-10-01T13:48:14Z'
evidence_urls:
  - https://github.com/Ikalus1988/MisakaNet/pull/2401
  - https://github.com/Ikalus1988/MisakaNet/blob/main/lessons/contrib/agentcap-secret-safe-verification-failure.md
confidence: high
tags: [pr-case-study, misakanet, verification, fact-error, self-audit]
rounds:
  - round: 1
    action: merge
    delta:
      kind: code_change
      value: "PR #2401 合入 5 篇 bounty lesson，其中 agentcap-secret-safe-verification-failure.md 的 verify 字段与 ## Verification 节写 `agentcap verify` / `agentcap export`"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/pull/2401
      confidence: high
    resolution: merged
    timestamp: '2026-09-28T13:09:12Z'
  - round: 2
    action: decision
    delta:
      kind: no_code_change
      value: "2026-10-01 自审（docs/CASE_ENRICHMENT_PLAN.md G4）：Verification 命令跑不通——PyPI agentcap 是 OliverIida/agentcap 0.1.1、wheel 无 entry_points.txt，装完没有 agentcap 命令；huggingface/agentcap 是另一个 Rust 项目；|| echo PASS 兜底在无工具时打印 PASS（实测）。上游修正 PR 待提"
      verified_at: '2026-10-01T13:48:14Z'
      evidence_urls:
        - https://github.com/Ikalus1988/MisakaNet/blob/main/lessons/contrib/agentcap-secret-safe-verification-failure.md
      confidence: high
    resolution: defect_confirmed_by_measurement
    timestamp: '2026-10-01T13:48:14Z'
close_decision:
  status: pending
  reason: "缺陷已复测确认；上游修正 PR 尚未提交（只做本地草稿，对外动作待主会话复核）"
  decided_at: null
  actor: zsxh1990
links:
  - type: anti-pattern
    target: anti-patterns/unrunnable-verification-command.md
---

## Case #2401: 合入 lesson 的 Verification 命令跑不通

**PR**: Ikalus1988/MisakaNet#2401 — feat(lessons): land five bounty lessons cleanly

**失败（round 2，自审 2026-10-01）**：
`lessons/contrib/agentcap-secret-safe-verification-failure.md` 的
`verify:` 字段与 `## Verification` 节教读者跑 `agentcap verify` / `agentcap export`。
这条 Verification 是**装饰而不是验证**：

1. **装错包**：`pip install agentcap` 装的是 OliverIida/agentcap 0.1.1（成本护栏 Python 库），
   wheel 里没有 entry_points.txt，装完不存在 `agentcap` 命令；
   读者想要的 huggingface/agentcap 是另一个 Rust 项目，从 PyPI 那条安装路径到不了它；
2. **空转绿**：frontmatter 的
   `agentcap verify 2>&1 | grep -q 'secret-safe' && echo 'FAIL' || echo 'PASS: no secret-safe failures'`
   在工具不存在时照样打印 `PASS: no secret-safe failures` 并 exit 0——
   校验对象不存在也能「通过」，在 CI 里同样全绿。

**为什么是 `unrunnable-verification-command` 的实例**：
文档里的 Verification 命令在干净环境跑不出它声称的输出（exit 127 → 被兜底洗成 PASS），
恰好落在「写文档时在脑内模拟输出、从没真跑」的三个形态里（装错包 + 空转绿）。
判据与实测输出见 `anti-patterns/unrunnable-verification-command.md`。

**同批记录的第二实例**：裸 `codesign --entitlements <path>`（缺 `-d`）在 macOS 26.5.2 上
只打 Usage 横幅（exit 2），不给任何 entitlement 内容；`codesign -d --entitlements - <path>` 才有输出。
该条的原始错误文本在本仓与 MisakaNet lessons/ 里没搜到（查不到），只保留可复测的行为事实。

**Key Learning**：
1. Verification 命令写进文档前先在没有该工具的干净环境跑一遍；
2. 核实「安装来源 → 二进制名 → 子命令」三层，PyPI 名 ≠ GitHub 名 ≠ CLI 名；
3. 校验脚本禁止 `|| echo PASS` 兜底——它把「没测到」洗成「通过」。

**处置**：上游修正（改安装来源指向、或删掉跑不通的命令段）待提 PR；
本 case 只做本地草稿，对外动作留给主会话复核。
