/**
 * 界面真数据测试 —— 走真实路径，不走自造假设。
 *
 * 真实路径 = 本测试实际执行的东西：
 *   1. apply() 用真 cordis Context 加载插件（用户装包后的同一入口）；
 *   2. 取数经 service.callTool → 真 MCP stdio 子进程（python3 -m prgenius.mcp）
 *      → 真 Python 分析引擎（prgenius/src/prgenius/，本 worktree 的代码）；
 *   3. 交叉验证：同一工具在 Python 直调与经 MCP 传输后结果一致（传输不改数据）；
 *   4. 渲染用真 React renderToStaticMarkup，断言真值出现在标记里。
 *
 * 这些断言不证明 DSH 宿主会挂载组件（本机无 DEEPSEEK_API_KEY，未跑 DSH）；
 * 宿主挂载是剩余诚实边界。数字永远来自工具输出，测试不写死计数。
 */
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { afterAll, beforeAll, describe, it } from 'vitest'
import { Context } from '@deepseek-ai/cordis'
import * as prGenius from '../src/index.ts'
import { parseConfig } from '../src/config.ts'
import { defaultKbRoot, readPackageMeta, resolveKbRoot } from '../src/kb.ts'
import { createMcpInvoker, type McpInvoker } from '../src/mcp-client.ts'
import type { PrGeniusService } from '../src/index.ts'
import {
  AdvisorView,
  DashboardView,
  PreferencesView,
  surfaceComponents,
  type AdvisorFace,
} from '../src/client/AdvisorPanel.tsx'
import {
  loadCases,
  loadDashboard,
  loadStatus,
  runCoach,
  type CoachVerdict,
  type DashboardData,
} from '../src/client/data.ts'
import { slotRegisterDef } from '../src/client/slots.ts'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const PY_SRC = join(ROOT, 'prgenius', 'src')

const PY_ENV = {
  ...process.env,
  PYTHONPATH: PY_SRC,
  PRGENIUS_REPO_ROOT: ROOT,
}

/** 直调 Python 引擎（不走 MCP）—— 与 MCP 路径交叉验证用的第二条真实路径。 */
function pythonDirect(script: string): unknown {
  const out = execFileSync('python3', ['-c', script], {
    cwd: ROOT,
    env: PY_ENV,
    encoding: 'utf8',
    timeout: 120_000,
  })
  return JSON.parse(out)
}

let invoker: McpInvoker
let service: PrGeniusService

beforeAll(async () => {
  // 子进程继承 vitest 的 env —— 必须先让 python3 找到本 worktree 的 prgenius 包与知识库。
  process.env.PYTHONPATH = PY_SRC
  process.env.PRGENIUS_REPO_ROOT = ROOT
  invoker = createMcpInvoker({
    transport: 'stdio',
    command: 'python3',
    args: ['-m', 'prgenius.mcp'],
    url: 'http://127.0.0.1:1/mcp',
    timeoutMs: 120_000,
    protocolVersion: '2025-06-18',
    clientName: 'pr-genius-surface-test',
    clientVersion: '0.0.0',
  })
  const config = parseConfig({})
  // 走与 apply() 同一个 service 构造（kb 解析 + describe 投影 + callTool 透传）。
  service = prGenius.createPrGeniusService({
    config,
    kb: resolveKbRoot(config.kbRoot),
    version: readPackageMeta(defaultKbRoot()).version,
    invoker,
  })
})

afterAll(async () => {
  await service?.close()
})

describe('Dashboard renders analyzer truth', () => {
  it('loadDashboard over real MCP matches a direct Python doctor run, and the markup shows those numbers', async () => {
    const data = await loadDashboard(service)
    assert.equal(data.doctorError, null, `doctor failed over MCP: ${data.doctorError}`)
    assert.ok(data.doctor !== null)

    const direct = pythonDirect(
      'from prgenius.doctor import run_doctor; import json; print(json.dumps(run_doctor(".")))',
    ) as { knowledge_base: Record<string, number> }
    const kb = data.doctor.kb
    assert.equal(kb.antiPatterns, direct.knowledge_base.anti_patterns, 'MCP vs direct anti-patterns')
    assert.equal(kb.successPatterns, direct.knowledge_base.success_patterns, 'MCP vs direct success_patterns')
    assert.equal(kb.profiles, direct.knowledge_base.profiles, 'MCP vs direct profiles')
    assert.equal(kb.caseStudies, direct.knowledge_base.case_studies, 'MCP vs direct case_studies')
    assert.equal(kb.policies, direct.knowledge_base.policies, 'MCP vs direct policies')
    assert.ok(kb.antiPatterns > 0, 'shipped knowledge base must be non-empty')

    const cases = await loadCases(service, 5)
    assert.equal(cases.ok, true)
    const markup = renderToStaticMarkup(
      createElement(DashboardView, {
        data,
        loading: false,
        cases: cases.ok ? cases.data : [],
        locale: 'en',
      }),
    )
    for (const value of [kb.antiPatterns, kb.successPatterns, kb.profiles, kb.caseStudies, kb.policies]) {
      assert.ok(markup.includes(String(value)), `markup missing KB count ${value}`)
    }
    assert.ok(markup.includes('data-kb="anti-patterns"'))
    assert.ok(markup.includes(String(data.doctor.mcpToolsRegistered)), 'markup missing MCP tool count')
  }, 180_000)

  it('without an author the in-flight section shows the real tool-side gap, not invented rows', async () => {
    const data: DashboardData = await loadDashboard(service)
    const markup = renderToStaticMarkup(
      createElement(DashboardView, { data, loading: false, cases: [], locale: 'en' }),
    )
    assert.equal(data.status, null)
    assert.ok(data.statusError !== null && data.statusError.length > 0)
    assert.ok(markup.includes('data-field="status-error"'))
    assert.ok(markup.includes(data.statusError as string))
  }, 180_000)

  const liveAuthor = process.env.PG_TEST_STATUS_AUTHOR
  it.runIf(Boolean(liveAuthor))(
    'live status_prs (author from PG_TEST_STATUS_AUTHOR) renders real PR rows',
    async () => {
      const status = await loadStatus(service, { author: liveAuthor as string })
      assert.equal(status.ok, true, status.ok ? '' : status.error)
      if (!status.ok) return
      const data = await loadDashboard(service, { author: liveAuthor as string })
      const markup = renderToStaticMarkup(
        createElement(DashboardView, { data, loading: false, cases: [], locale: 'en' }),
      )
      assert.ok(data.status !== null)
      for (const key of Object.keys(data.status!.summary)) {
        assert.ok(markup.includes(`data-status="${key}"`), `summary key ${key} not rendered`)
      }
      const first = data.status!.prs[0]
      if (first) {
        assert.ok(markup.includes(`${first.repo}#${first.number}`), 'first PR row not rendered')
        assert.ok(markup.includes(first.status), 'first PR status not rendered')
      }
    },
    180_000,
  )
})

describe('Advisor renders coach_pr verdicts', () => {
  it('coach_pr over MCP matches a direct Python call, and the verdict markup shows it', async () => {
    const input = {
      title: 'fix: correct slot kinds in the declaration table',
      repo: 'zsxh1990/pr-genius',
      body: 'Fixes #98. Wires real analyzer data into the four surfaces.',
    }
    const result = await runCoach(service, input)
    assert.equal(result.ok, true, result.ok ? '' : result.error)
    if (!result.ok) return
    const verdict: CoachVerdict = result.data

    const direct = pythonDirect(
      `from prgenius.mcp import _load_tools; import json; s=_load_tools("."); print(json.dumps(s._tool_manager._tools["coach_pr"].fn(title=${JSON.stringify(input.title)}, repo=${JSON.stringify(input.repo)}, body=${JSON.stringify(input.body)})))`,
    ) as { tier: string; pass: boolean; merge_probability: number | null }
    assert.equal(verdict.tier, direct.tier, 'MCP vs direct tier')
    assert.equal(verdict.pass, direct.pass, 'MCP vs direct pass')
    assert.equal(verdict.mergeProbability, direct.merge_probability, 'MCP vs direct merge_probability')

    const markup = renderToStaticMarkup(
      createElement(AdvisorView, {
        verdict,
        patterns: [],
        error: null,
        running: false,
        locale: 'en',
        workMode: 'contributor',
      }),
    )
    assert.ok(markup.includes(`data-verdict="tier">${verdict.tier}`), 'tier not rendered')
    assert.ok(
      markup.includes(`data-verdict="pass">${verdict.pass ? 'PASS' : 'FAIL'}`),
      'pass/fail label not rendered',
    )
    if (verdict.mergeProbability !== null) {
      assert.ok(markup.includes(String(verdict.mergeProbability)), 'merge probability not rendered')
    }
    for (const item of verdict.checklist.slice(0, 3)) {
      assert.ok(markup.includes(item.action), `checklist action ${item.action} not rendered`)
    }
    for (const signal of verdict.signals.positive.slice(0, 3)) {
      assert.ok(markup.includes(signal.description), `signal ${signal.key} not rendered`)
    }
    // 覆盖数字同样来自工具输出，不是界面编的
    if (verdict.coverage.antiPatternsLoaded >= 0) {
      assert.ok(markup.includes(String(verdict.coverage.antiPatternsLoaded)), 'coverage not rendered')
    }
  }, 180_000)
})

describe('Preferences renders the effective config', () => {
  it('shows every describe() value, not placeholder text', async () => {
    const face: AdvisorFace = {
      service,
      locale: 'en',
      workMode: 'contributor',
      riskFilter: 'low_risk',
    }
    const info = service.describe()
    const markup = renderToStaticMarkup(createElement(PreferencesView, { face }))
    assert.ok(markup.includes(info.kbRoot), 'kbRoot not rendered')
    assert.ok(markup.includes(info.mcp.endpoint), 'mcp endpoint not rendered')
    assert.ok(markup.includes(info.mcp.transport), 'transport not rendered')
    assert.ok(markup.includes(info.locale), 'locale not rendered')
    assert.ok(markup.includes(info.riskFilter), 'riskFilter not rendered')
    assert.ok(markup.includes(String(info.maintainer.staleDays)), 'staleDays not rendered')
    assert.ok(markup.includes('data-field="effective-config"'))
  })
})

describe('apply() wires the real service into real components', () => {
  it('loads on a cordis Context, registers catalog-shaped slot entries, injects service data sources', async () => {
    const registered: Array<{ slot: string; def: Record<string, unknown>; component: unknown }> = []
    const fakeSlots = {
      inject: (_slot: string, factory: () => unknown) => {
        factory()
        return () => undefined
      },
      register: (def: unknown, component: unknown) => {
        const d = def as { name: string; id?: string; key?: string }
        registered.push({ slot: d.name, def: d as Record<string, unknown>, component })
        return () => undefined
      },
    }
    const ctx = new Context()
    ctx.provide('slots', fakeSlots)
    const fiber = ctx.plugin(prGenius, parseConfig({}))
    await fiber
    const serviceFromCtx = ctx.get('prGenius') as PrGeniusService | undefined
    assert.ok(serviceFromCtx !== undefined, 'service must be registered by apply()')

    // 四个界面都拿到了真组件（不是 null）与 catalog 形状的注册参数
    assert.equal(registered.length, 4, `expected 4 registrations, got ${registered.length}`)
    for (const entry of registered) {
      assert.equal(typeof entry.component, 'function', `component for ${entry.slot} is not a function`)
      const expected = slotRegisterDef(entry.slot, String(entry.def.id ?? entry.def.key))
      assert.ok(expected, `apply() registered an unverified slot: ${entry.slot}`)
      assert.equal(entry.def.name, expected.name)
      if (expected.key !== undefined) assert.equal(entry.def.key, expected.key)
      if (expected.id !== undefined) assert.equal(entry.def.id, expected.id)
    }

    // 组件工厂把 service 闭包进组件：渲染壳时不再依赖宿主传 service
    const face: AdvisorFace = {
      service: serviceFromCtx,
      locale: 'zh-CN',
      workMode: 'maintainer',
      riskFilter: 'high_risk',
    }
    const components = surfaceComponents(face)
    assert.equal(typeof components['pr-genius.dashboard'], 'function')
    const dashShell = renderToStaticMarkup(createElement(components['pr-genius.dashboard']))
    assert.ok(dashShell.includes('data-surface="dashboard"'))
    const advisorShell = renderToStaticMarkup(createElement(components['pr-genius.advisor-tab']))
    assert.ok(advisorShell.includes('data-mode="maintainer"'))
    const prefsShell = renderToStaticMarkup(createElement(components['pr-genius.preferences']))
    assert.ok(prefsShell.includes('data-surface="preferences"'))

    await fiber.dispose()
  }, 180_000)
})
