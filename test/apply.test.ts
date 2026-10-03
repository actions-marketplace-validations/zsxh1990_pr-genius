/**
 * apply() 生命周期测试：加载注册服务、卸载还原、非法配置/缺失知识库响亮失败。
 *
 * 用真实 cordis Context 驱动 fiber（加载即生效、卸载即还原）。不启动 DSH ——
 * 这里只验证插件契约与生命周期，渲染需 DSH 运行时验证，本机未执行。
 */
import assert from 'node:assert/strict'
import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, it } from 'vitest'
import { Context } from '@deepseek-ai/cordis'
import * as prGenius from '../src/index.ts'
import { parseConfig, PrGeniusConfigError } from '../src/config.ts'
import { defaultKbRoot, resolveKbRoot } from '../src/kb.ts'
import type { PrGeniusService } from '../src/index.ts'

function asService(value: unknown): PrGeniusService {
  assert.ok(value !== undefined && value !== null, 'prGenius service should be registered')
  return value as PrGeniusService
}

describe('apply() lifecycle', () => {
  it('registers the prGenius service on load and restores on unload', async () => {
    const ctx = new Context()
    const fiber = ctx.plugin(prGenius, parseConfig({}))
    await fiber

    const service = asService(ctx.get('prGenius'))
    assert.equal(typeof service.describe, 'function')
    assert.equal(typeof service.callTool, 'function')
    assert.equal(typeof service.close, 'function')
    assert.equal(service.describe().name, 'pr-genius')
    assert.equal(service.describe().mcp.transport, 'stdio')
    assert.equal(service.describe().kbRoot, defaultKbRoot())

    await fiber.dispose()
    assert.equal(ctx.get('prGenius'), undefined, 'service must be gone after unload')
  })

  it('describe() reflects config overrides (maintainer mode, locale, risk filter, sidebar)', async () => {
    const ctx = new Context()
    const config = parseConfig({
      sidebar: { defaultView: 'panel' },
      maintainer: {
        enabled: true,
        actions: ['READY_FOR_REVIEW', 'HOLD_MAINTAINER_DECISION'],
        confidenceMin: 0.5,
        staleDays: 7,
      },
      locale: 'zh-CN',
      riskFilter: 'high_risk',
      mcp: { transport: 'http', url: 'http://127.0.0.1:9999/mcp' },
    })
    const fiber = ctx.plugin(prGenius, config)
    await fiber

    const info = asService(ctx.get('prGenius')).describe()
    assert.equal(info.sidebar.defaultView, 'panel')
    assert.equal(info.maintainer.enabled, true)
    assert.deepEqual(info.maintainer.actions, ['READY_FOR_REVIEW', 'HOLD_MAINTAINER_DECISION'])
    assert.equal(info.maintainer.confidenceMin, 0.5)
    assert.equal(info.maintainer.staleDays, 7)
    assert.equal(info.locale, 'zh-CN')
    assert.equal(info.riskFilter, 'high_risk')
    assert.equal(info.mcp.transport, 'http')
    assert.equal(info.mcp.endpoint, 'http://127.0.0.1:9999/mcp')

    await fiber.dispose()
    assert.equal(ctx.get('prGenius'), undefined)
  })

  it('fails load loudly when config is invalid (no half-mounted service)', async () => {
    const ctx = new Context()
    const fiber = ctx.plugin(prGenius, { locale: 'fr' } as never)
    await assert.rejects(() => Promise.resolve(fiber))
    assert.equal(ctx.get('prGenius'), undefined, 'invalid config must not leave a service registered')
  })

  it('fails load loudly when kbRoot has no knowledge base layout', async () => {
    const emptyRoot = mkdtempSync(join(tmpdir(), 'pr-genius-empty-kb-'))
    const ctx = new Context()
    const fiber = ctx.plugin(prGenius, parseConfig({ kbRoot: emptyRoot }))
    await assert.rejects(() => Promise.resolve(fiber), (error: unknown) => {
      assert.ok(error instanceof PrGeniusConfigError || error instanceof Error)
      assert.match(String(error), /kbRoot/)
      return true
    })
    assert.equal(ctx.get('prGenius'), undefined)
  })

  it('is idempotent across load/unload cycles', async () => {
    const ctx = new Context()
    for (let i = 0; i < 3; i++) {
      const fiber = ctx.plugin(prGenius, parseConfig({}))
      await fiber
      assert.ok(ctx.get('prGenius') !== undefined, `cycle ${i}: service registered`)
      await fiber.dispose()
      assert.equal(ctx.get('prGenius'), undefined, `cycle ${i}: service removed`)
    }
  })
})

describe('knowledge base layout', () => {
  it('defaultKbRoot points at the package root with the shipped knowledge base', () => {
    const layout = resolveKbRoot('')
    assert.equal(layout.root, defaultKbRoot())
    for (const dir of [layout.antiPatterns, layout.successPatterns, layout.profiles, layout.policies]) {
      assert.ok(dir.startsWith(layout.root), `${dir} should live under ${layout.root}`)
    }
  })

  it('resolves an explicit kbRoot and rejects one without the layout', () => {
    const fakeKb = mkdtempSync(join(tmpdir(), 'pr-genius-fake-kb-'))
    for (const sub of ['anti-patterns', 'success-patterns', 'profiles', join('docs', 'policies')]) {
      mkdirSync(join(fakeKb, sub), { recursive: true })
    }
    writeFileSync(join(fakeKb, 'anti-patterns', 'sample.yml'), 'key: sample\n')
    const layout = resolveKbRoot(fakeKb)
    assert.equal(layout.root, fakeKb)

    assert.throws(
      () => resolveKbRoot(mkdtempSync(join(tmpdir(), 'pr-genius-no-kb-'))),
      (error: unknown) => {
        assert.ok(error instanceof PrGeniusConfigError)
        assert.equal(error.field, 'kbRoot')
        return true
      },
    )
  })
})
