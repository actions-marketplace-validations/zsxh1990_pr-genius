/**
 * Config schema 单元测试：默认值填充、非法配置被拒、错误信息点名字段。
 * 纯静态/内存测试 —— 不启动 DSH，不调用 Python 引擎。
 */
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  Config,
  CONTRIBUTOR_ACTIONS,
  MAINTAINER_ACTIONS,
  PrGeniusConfigError,
  parseConfig,
} from '../src/config.ts'

describe('Config schema defaults', () => {
  it('fills every field with a default for an empty object', () => {
    const resolved = parseConfig({})
    assert.equal(resolved.kbRoot, '')
    assert.equal(resolved.mcp.transport, 'stdio')
    assert.equal(resolved.mcp.command, 'prgenius-core')
    assert.deepEqual(resolved.mcp.args, ['mcp', 'serve'])
    assert.equal(resolved.mcp.url, 'http://127.0.0.1:8000/mcp')
    assert.equal(resolved.mcp.timeoutMs, 30_000)
    assert.equal(resolved.mcp.protocolVersion, '2025-06-18')
    assert.equal(resolved.sidebar.defaultView, 'dashboard')
    assert.equal(resolved.maintainer.enabled, false)
    assert.deepEqual(resolved.maintainer.actions, [...MAINTAINER_ACTIONS])
    assert.equal(resolved.maintainer.confidenceMin, 0)
    assert.equal(resolved.maintainer.staleDays, 14)
    assert.equal(resolved.locale, 'en')
    assert.equal(resolved.riskFilter, 'low_risk')
  })

  it('keeps provided values and fills the rest (partial nested config)', () => {
    const resolved = parseConfig({
      kbRoot: '/tmp/kb',
      mcp: { transport: 'http', url: 'http://127.0.0.1:9000/mcp' },
      maintainer: { enabled: true, confidenceMin: 0.8 },
      locale: 'zh-CN',
      riskFilter: 'medium_risk',
    })
    assert.equal(resolved.kbRoot, '/tmp/kb')
    assert.equal(resolved.mcp.transport, 'http')
    assert.equal(resolved.mcp.url, 'http://127.0.0.1:9000/mcp')
    // 未提供的兄弟字段仍取默认值
    assert.equal(resolved.mcp.timeoutMs, 30_000)
    assert.equal(resolved.mcp.command, 'prgenius-core')
    assert.equal(resolved.maintainer.enabled, true)
    assert.equal(resolved.maintainer.confidenceMin, 0.8)
    assert.equal(resolved.maintainer.staleDays, 14)
    assert.deepEqual(resolved.maintainer.actions, [...MAINTAINER_ACTIONS])
    assert.equal(resolved.locale, 'zh-CN')
    assert.equal(resolved.riskFilter, 'medium_risk')
  })

  it('accepts a subset of maintainer actions', () => {
    const resolved = parseConfig({
      maintainer: { actions: ['READY_FOR_REVIEW', 'WAIT_FOR_AUTHOR'] },
    })
    assert.deepEqual(resolved.maintainer.actions, ['READY_FOR_REVIEW', 'WAIT_FOR_AUTHOR'])
    // 词表本身不被 schema 改写
    assert.equal(MAINTAINER_ACTIONS.length, 5)
    assert.equal(CONTRIBUTOR_ACTIONS.length, 5)
  })

  it('exposes a callable schema with the same name as the Config type', () => {
    assert.equal(typeof Config, 'function')
    assert.deepEqual(Config({}).locale, 'en')
  })
})

describe('Config schema rejects invalid input loudly', () => {
  const cases: Array<{ label: string; input: unknown; field: string }> = [
    { label: 'kbRoot wrong type', input: { kbRoot: 42 }, field: 'kbRoot' },
    {
      label: 'unknown transport',
      input: { mcp: { transport: 'carrier-pigeon' } },
      field: 'mcp.transport',
    },
    {
      label: 'timeout below minimum',
      input: { mcp: { timeoutMs: 0 } },
      field: 'mcp.timeoutMs',
    },
    {
      label: 'url wrong type',
      input: { mcp: { url: 1234 } },
      field: 'mcp.url',
    },
    {
      label: 'args not a string array',
      input: { mcp: { args: ['ok', 7] } },
      field: 'mcp.args',
    },
    {
      label: 'sidebar view not in enum',
      input: { sidebar: { defaultView: 'popup' } },
      field: 'sidebar.defaultView',
    },
    {
      label: 'maintainer.enabled not boolean',
      input: { maintainer: { enabled: 'yes' } },
      field: 'maintainer.enabled',
    },
    {
      label: 'maintainer.actions unknown action',
      input: { maintainer: { actions: ['SHIP_IT'] } },
      field: 'maintainer.actions',
    },
    {
      label: 'confidenceMin above 1',
      input: { maintainer: { confidenceMin: 2 } },
      field: 'maintainer.confidenceMin',
    },
    {
      label: 'staleDays below 1',
      input: { maintainer: { staleDays: 0 } },
      field: 'maintainer.staleDays',
    },
    {
      label: 'locale not supported',
      input: { locale: 'fr' },
      field: 'locale',
    },
    {
      label: 'riskFilter not a tier',
      input: { riskFilter: 'catastrophic' },
      field: 'riskFilter',
    },
  ]

  for (const { label, input, field } of cases) {
    it(`rejects ${label} and names the field (${field})`, () => {
      assert.throws(
        () => parseConfig(input),
        (error: unknown) => {
          assert.ok(error instanceof PrGeniusConfigError, `expected PrGeniusConfigError, got ${error}`)
          // 数组/对象元素的错误会带上元素下标（`maintainer.actions.0`），比字段名更精确。
          // 这里断言的是「指对了字段」，所以用前缀匹配；精确到元素算加分，不算错。
          assert.ok(
            error.field === field || error.field.startsWith(field + '.'),
            `expected field ${field} (or a sub-path of it), got ${error.field}`,
          )
          assert.match(error.message, new RegExp(field.replace('.', '\\.')))
          return true
        },
      )
    })
  }

  it('reports field path from the underlying schema error', () => {
    try {
      parseConfig({ mcp: { timeoutMs: -5 } })
      assert.fail('should have thrown')
    } catch (error) {
      assert.ok(error instanceof PrGeniusConfigError)
      assert.equal(error.field, 'mcp.timeoutMs')
      assert.match(error.message, /mcp\.timeoutMs/)
    }
  })
})
