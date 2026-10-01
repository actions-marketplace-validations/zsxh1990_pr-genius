---
type: Anti-Pattern
key: pr-scope-collides-with-landed-work
tags: [scope, rebase, duplicate-work, pr-hygiene, review-burden]
description: "PR 的主体内容上游已合入，只剩一个真缺口，却按原范围提交 → 重复劳动 + 误导评审"
symptom: "reviewer points out most of the diff is already on main"
trigger_keywords:
  - "already merged"
  - "this is redundant"
  - "see #N"
  - "landed in"
  - "already done on main"
  - "please re-scope"
fix_action: "1) 开 PR 前 grep/git log 查上游是否已落地同一改动；2) 若已落地，把分支 reset 到 upstream/main 只留真缺口；3) PR 正文明确写「X 已在 main 干净，本 PR 只剩 Y」；4) 不要写 Closes #issue 除非真能整体关闭"
source_pr: "doobidoo/mcp-memory-service#1397"
severity: medium
evidence:
  - "mcp-memory-service #1397 最初要清 server/handlers/memory.py 的 27 处未脱敏 f-string logger，但 upstream/main 上该文件未脱敏计数已是 0，且已在 GUARDED_MODULES"
  - "真正残留的只有一个洞：同一调用带 exc_info=True，traceback 把原始 str(e) 带出，绕过所有包裹"
  - "把 PR 收缩为「1 文件 9+/2-」后从 CONFLICTING 变 MERGEABLE，且评审负担骤降"
  - "同仓库合作者的 #1394 已就同一 issue 清了 backup/scheduler.py——不先看进度就动手必撞"
created: 2026-10-01
learned_at: 2026-10-01
source_url: https://github.com/doobidoo/mcp-memory-service/pull/1397
updated: 2026-10-01
confidence: high

---

## 反模式说明

领了 issue 就开工，没先确认**当前进度**。结果提交的是别人已经做完的部分 + 一个真缺口，
评审者要从重复的 diff 里把真缺口找出来，或者直接以"重复"为由拒掉整个 PR。

### 触发条件

- issue 很老、合作者多、拆成"一次清一个文件"的渐进式任务
- PR diff 里大部分改动能在上游 `git log` 里找到等价 commit
- `git diff upstream/main` 很大，但 `git diff upstream/main -- <你真想改的那处>` 很小
- 出现 CONFLICTING 且冲突文件是生成物或共享清单（如 GUARDED_MODULES）

### 为什么会发生

1. **本地基点旧**：从过时的 main 拉出分支，看到的"未完成"其实是历史快照。
2. **清单式 issue**：issue 说"还有 573 处待清"，但那句话是开工时写的，不是现在的状态。
3. **并行协作者**：别人同一天清了相邻的文件，两边都改共享清单 → 必冲突。

### 修复动作

**开工前先量当前进度：**

```bash
git fetch upstream main
# 目标文件当前还有多少？
grep -cE 'logger\.\(f"' <target-file>
# 上游是不是已经进清单了？
grep -n '<target-file>' tests/.../guard.py
# 有没有人同日在做同一 issue？
gh issue view <n> --comments | tail -20
```

**已落地就收缩范围，而不是重做：**

```bash
git reset --hard upstream/main   # 丢掉重复部分
# 只应用真缺口
```

**PR 正文必须写清边界**：

> The N un-wrapped calls in this file are **already clean on main**. What is left is one hole:
> … 本 PR 只修这一个，并说明为什么不顺手改别的（避免 blast radius）。

**别顺手扩大**：一个安全修复不该裹挟"清理 ~25 处重复 helper"——那是另一个 PR。

### 判据

- PR 描述里有一段 **"Deliberately not in this PR"**，说明排除了什么、为什么
- diff 规模与"真缺口"匹配，而不是与"issue 原始描述"匹配
- 不写 `Closes #issue`，除非这个 PR 真的能整体关闭它（渐进式任务应写 `Refs #issue`）
