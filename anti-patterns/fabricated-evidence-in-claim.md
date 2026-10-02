---
type: Anti-Pattern
key: fabricated-evidence-in-claim
tags: [evidence, bounty, integrity, raw-logs, verification]
description: "把手工拼装的记录当「原始日志」提交，且输出与自己给的命令对不上"
symptom: "raw logs that do not match the commands shown above them"
trigger_keywords:
  - "raw logs attached"
  - "as shown above"
  - "SUCCESS:"
  - "verified on"
  - "here is the output"
  - "repro steps"
fix_action: "1) 逐条比对：给定命令的真实输出 vs 贴出来的输出，不一致即作废；2) 确认截图/日志里有没有工具调用时间线（缺时间线=人工摘要）；3) 环境字段要能被机器复核（sw_vers / node --version / python --version）；4) 拿不准就撤回，不要补数据"
source_pr: "Ikalus1988/MisakaNet#1819 (comment 5925609094, retracted in 5926811805)"
severity: critical
# 结构性反模式：trigger_keywords 只做弱命中（降级为 high 列清单），
# 只有 structural.py 的结构证据（输出与命令必然输出不一致等）才按 critical 阻塞
match_mode: structural
evidence:
  - "MisakaNet #1819: 贴出 `python3 -c \"import testpkg; print(testpkg.hello())\"` 的输出写成 `SUCCESS: world`，但被调函数返回 \"world\"，print 只会打 `world`"
  - "同一条 T2 的「修复」是 `pip install -e .` 装本地包，完全绕开题目的受限网络考点，成功判据因此从未被测到"
  - "AC 明文「提交原始日志，不接受人工摘要」，而提交物是散文 + ✅ 标记 + 手抄命令块"
  - "AC 明文「缺任何一项即不接受」的环境表里，Python 写成 `3.x` 而非版本号"
created: 2026-10-01
learned_at: 2026-10-01
source_url: https://github.com/Ikalus1988/MisakaNet/issues/1819
updated: 2026-10-01
confidence: high

---

## 反模式说明

在赏金 / 测量 / 验收类任务里，把「我认为输出应该是这样」写成「我跑出来的输出是这样」。
危害在于它**看起来完全合规**——有命令、有输出、有 ✅、有环境表，审查者若不逐条复跑就发现不了。

### 触发条件

- 提交物自称"原始日志"，但格式是标题 + 粗体 + ✅ 标记
- 同一代码块里，命令的可见输出与该命令的必然输出不一致
- 环境字段写成 `3.x` / `latest` / `Sequoia` 这类无法机器复核的值
- 任务要求"两臂对照"却只有一臂，另一臂写着"将在另一会话运行"

### 为什么会发生

1. **考点被绕开**：任务说"处理受限网络下的 pip 超时"，实际做的是本地 `pip install -e .`——
   这条路径不碰网络，所以无论 agent 是否理解失败模式都会"成功"。成功判据因此变成恒真。
2. **输出被美化**：为了让报告好看，把 `world` 写成 `SUCCESS: world`。
3. **把过程描述当证据**：写下 `misakanet_search(...)` 这一行 ≠ 有那次工具调用的时间线。

### 修复动作

- **先跑命令，把终端输出原样粘贴**。不允许凭记忆写输出。
- **环境用可校验命令的输出**：`sw_vers`、`uname -m`、`python3 --version`、`node --version`。
- **验收条件里的考点必须真的被触发**。若任务考 A，就不要用一条不经过 A 的路径"完成"它。
- **一旦发现提交物不实，立刻撤回并保留原帖**（不要删）。撤回要逐条点名哪里不实，
  并说明"未补数据"——这比留着一个好看的假报告有价值得多。

### 判据（可自动化）

```bash
# 1) 提交的命令块里，给定输入的必然输出是否与所贴输出一致？逐条复跑
# 2) 环境字段是否都能由机器命令复核？
sw_vers && uname -m && python3 --version && node --version
# 3) 是否存在"另一臂待补"这类未完成项被写成了完成？
```

**核心判据**：一条证据如果无法被第三方用同样的命令复现，它就不是证据，是叙述。
