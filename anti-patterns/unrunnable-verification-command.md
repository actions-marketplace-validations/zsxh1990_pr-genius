---
type: Anti-Pattern
key: unrunnable-verification-command
tags: [verification, commands, cli, fact-error, self-audit, evidence]
description: "文档里写下的 Verification 命令根本跑不通：装错包、缺子命令、缺必需 flag；更糟的是 `|| echo PASS` 兜底让它在工具不存在时也打印 PASS"
symptom: "verification command exits 127, prints a usage banner, or prints PASS without the tool installed"
trigger_keywords:
  - "verify:"
  - "## Verification"
  - "&& echo 'FAIL' || echo 'PASS"
  - "agentcap verify"
  - "codesign --entitlements"
  - "Expected: no lines"
fix_action: |
  1) 写下任何 Verification 命令前，先在没有该工具的干净环境里跑一遍，把真实输出原样贴进文档；
  2) 逐层核实「安装来源 → 二进制名 → 子命令」：PyPI 包名 ≠ GitHub 项目名 ≠ CLI 命令名；
  3) 校验脚本禁止 `|| echo PASS` 式兜底——工具不存在时它照样打印 PASS（空转绿）；
  4) flag 组合以 usage 为准：`codesign --entitlements` 缺 `-d` 只打 Usage 横幅，
     `codesign -d --entitlements - <path>` 才输出内容；
  5) 自查脚本：把文档里每条命令抽出来在无该工具的环境跑一遍，能跑出 PASS 的全是嫌疑对象。
source_pr: "Ikalus1988/MisakaNet#2401 (lessons/contrib/agentcap-secret-safe-verification-failure.md 的 verify 字段与 ## Verification 节)"
severity: high
evidence:
  - "agentcap 实例：该 lesson 的 verify 字段与 Verification 节调用 `agentcap verify` / `agentcap export`；实测 PyPI `agentcap` 是 OliverIida/agentcap 0.1.1（成本护栏 Python 库），wheel 无 entry_points.txt，装完没有 agentcap 命令；huggingface/agentcap 是另一个 Rust 项目，`pip install agentcap` 到不了它"
  - "空转绿实测（2026-10-01，机器上没有任何 agentcap CLI）：`agentcap verify 2>&1 | grep -q 'secret-safe' && echo 'FAIL' || echo 'PASS: no secret-safe failures'` 打印 `PASS: no secret-safe failures` 且 exit 0——校验对象不存在也能通过"
  - "codesign 实例（实测 macOS 26.5.2 / 25F84 arm64）：裸 `codesign --entitlements /bin/ls` exit=2 且只打 Usage 横幅，不给任何 entitlement 内容；`codesign -d --entitlements - /bin/ls` 才有输出"
  - "两条都记在我方自审账上：docs/CASE_ENRICHMENT_PLAN.md G4「自己内容里的事实错误（agentcap/codesign 那两条：Verification 命令根本跑不通）」；codesign 那条的原始错误文本在本仓与 MisakaNet lessons/ 里没搜到（查不到），此处只保留可复测的行为事实"
created: 2026-10-01
learned_at: 2026-10-01
source_url: https://github.com/Ikalus1988/MisakaNet/blob/main/lessons/contrib/agentcap-secret-safe-verification-failure.md
updated: 2026-10-01
confidence: high

---

## 反模式说明

写文档时「应该会输出什么」和「实际输出什么」之间的差距，恰好都落在 Verification 段里——
读者和 CI 都默认这段是可信的，所以它是**唯一没人复跑**的地方。
三种典型形态：

1. **装错包**：写 `pip install agentcap`，指的却是另一个同名项目，CLI 根本不存在；
2. **缺 flag / 缺子命令**：命令存在但用法不对，只打 Usage 横幅（exit 2）；
3. **空转绿**：`cmd | grep -q ... && echo FAIL || echo PASS`——cmd 不存在时 grep 也查不到，
   于是打印 PASS。校验失败被兜底吃掉，看起来全绿。

危害：报告里每条 Verification 都「通过」，但没有一条真的测过它声称测的东西。

### 触发条件

- Verification 命令的二进制名与安装来源没核对过（PyPI 名 / GitHub 名 / CLI 名三者不一致）
- 命令输出里出现 Usage 横幅（说明 flag 不对，而不是环境问题）
- 校验语句带 `|| echo PASS` 兜底
- 文档说「Expected: no lines」这类**以缺失为通过**的判据，而工具缺失时同样"满足"

### 为什么会发生

写文档时在脑内模拟命令输出，从没在干净环境跑过；同名项目撞车时选了看起来顺眼的那个。
兜底 `|| echo PASS` 是为了脚本不中断，却把「没测到」洗成了「通过」。

### 判据（每条都在 2026-10-01 真跑过）

```bash
# 1) PyPI 身份：agentcap 到底是谁
curl -s https://pypi.org/pypi/agentcap/json | python3 -c "import json,sys; i=json.load(sys.stdin)['info']; print(i['name'], i['version'], i['author']); print(i['project_urls'])"
# → agentcap 0.1.1 Oliver Iida
# → {'Homepage': 'https://github.com/OliverIida/agentcap', ...}

# 2) wheel 里有没有 CLI 入口点
python3 -m pip download agentcap --no-deps -d /tmp/agentcap-wheel-check -q
python3 -m zipfile -l /tmp/agentcap-wheel-check/agentcap-0.1.1-py3-none-any.whl | grep entry_points || echo "NO entry_points.txt -> no console_scripts, no agentcap binary"
# → NO entry_points.txt -> no console_scripts, no agentcap binary

# 3) 空转绿：工具不存在，lesson 的校验照样 PASS
command -v agentcap || echo "agentcap: command not found"
agentcap verify 2>&1 | grep -q 'secret-safe' && echo 'FAIL' || echo 'PASS: no secret-safe failures'
# → agentcap: command not found
# → PASS: no secret-safe failures

# 4) codesign 缺 -d：只打 Usage（macOS 26.5.2 实测）
codesign --entitlements /bin/ls > /tmp/cs_bare.txt 2>&1; echo "exit=$?"; head -2 /tmp/cs_bare.txt
# → exit=2
# → Usage: codesign -s identity [-fv*] ...

# 5) 对照：带 -d 才有输出
codesign -d --entitlements - /bin/ls | head -3
# → Executable=/bin/ls
```

**核心判据**：一条 Verification 命令如果在干净环境跑不出它声称的输出，它不是验证，是装饰。
