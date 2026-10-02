---
type: Documentation
title: DSH 版本兼容矩阵
tags: [dsh, compatibility, cordis]
description: "pr-genius DSH 插件与 DeepSeek Harness 各版本的兼容性声明与验证状态"
created: 2026-10-03
updated: 2026-10-03
confidence: medium
---

# DSH 版本兼容矩阵

> **验证状态：契约声明，未跑运行时。** 本机没有 `DEEPSEEK_API_KEY`，从未在真实
> DeepSeek Harness 里加载过本插件。下表的「预期」来自对官方教程与 dsh-context
> 兼容性说明的对照；「已验证」列只填真跑过的组合——目前一格都没有。

| DSH 线 | 本插件预期 | 已验证 | 依据 |
|---|---|---|---|
| `0.1.5-rc.1+` | 命令面可用；右栏 Panel 可用 | ❌ 未跑 | dsh-context 把右栏 Panel 的下限定在这里 |
| `0.1.7-rc.2+` | Preferences 走侧边栏 `Plugins` → bundle 页 → `Configuration` | ❌ 未跑 | dsh-context 的设置落点分支 |
| `0.1.7-rc.2` 之前的 | Preferences 走 `Settings → Plugins → Plugin configuration` | ❌ 未跑 | 同上 |
| `0.2.0-rc.2+` | 同 `0.1.7` 线 | ❌ 未跑 | 同上 |

## 本插件实际用到的宿主能力

| 能力 | 何时会用 | 缺失时的行为 |
|---|---|---|
| `ctx.provide` / `ctx.effect` | 始终 | 必需；缺失则插件无法加载 |
| `ctx.logger` | 始终 | 必需 |
| `ctx.command` | 注册 `/prgenius` | **可选**——探测不到就跳过并记 warn |
| `ctx.slots.inject` / `register` | 注册四界面中的 UI 三面 | **可选**——探测不到就跳过并记 warn |

后两项刻意写成可选贡献而非依赖：`inject` 为空，所以没有 web UI 的宿主（纯命令行）
也能加载本插件，只是侧边栏与面板不出现。

## 一句话验证方式

装好后跑：

```bash
dsh plugin --profile <你的profile> add pr-genius
dsh plugin --profile <你的profile> update pr-genius@latest   # 升级
```

然后在 Web UI 侧边栏 `Plugins` 里找 `pr-genius` 的 `Configuration` 段；改任一字段后
**不需要重启**——它触发该插件的增量热替换。

> 这条命令本身也没在本机跑过（无 DSH）。跑通与否请以你的实际结果为准。
