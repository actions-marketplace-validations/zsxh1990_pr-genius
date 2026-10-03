/**
 * slot key 与上游 DSH slot-catalog 的对齐验证（issue #97）。
 *
 * 非循环验证的要点：
 *   allowed 集合**不写在本文件里**，也不来自插件自己的常量 —— 它是把
 *   `test/fixtures/dsh-slot-catalog.ts`（上游 bytes 的快照）当纯文本解析出来的。
 *   插件说要用的 key 必须出现在上游 bytes 里，才算通过；拿插件自己的表去自证
 *   是循环验证（v2.1.2 的"验证 harness"就是这么骗过自己的）。
 *
 * 跑的是 apply() 真实注册路径：宿主提供 slots.inject/register 记录器，
 * 逐个打印实际注入的 key，再与上游解析结果对照。
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { describe, it } from 'vitest'
import * as prGenius from '../src/index.ts'
import { parseConfig } from '../src/config.ts'
import {
  CATALOG_PROVENANCE,
  CONFIRMED_SLOT_KEYS,
  isConfirmedSlotKey,
} from '../src/ui/slot-catalog.ts'
import { SURFACE_IDS, planRegistrations, registrationCalls } from '../src/ui/surfaces.ts'
import { SLOT_DECLARATIONS } from '../src/client/slots.ts'

const HERE = dirname(fileURLToPath(import.meta.url))
const CATALOG_PATH = join(HERE, 'fixtures', 'dsh-slot-catalog.ts')

// ── 从上游 bytes 解析权威集合（唯一允许的 allowed 来源）──────────────────
const catalogText = readFileSync(CATALOG_PATH, 'utf8')

interface CatalogEntry {
  key: string
  kind: string
  scope: string
  /** register 选项名 → requirement */
  options: Map<string, string>
}

function parseCatalog(text: string): Map<string, CatalogEntry> {
  const out = new Map<string, CatalogEntry>()
  // 每个 entry 以两空格缩进的 `{` 开始，字段在其中。
  const chunks = text.split('\n  {\n')
  for (const chunk of chunks) {
    const key = /^\s*key: '([^']+)'/.exec(chunk)?.[1]
    if (!key) continue
    const kind = /kind: '([^']+)'/.exec(chunk)?.[1] ?? ''
    const scope = /scope: '([^']+)'/.exec(chunk)?.[1] ?? ''
    const options = new Map<string, string>()
    const optBlock = /registerOptions: \[([\s\S]*?)\n    \],/.exec(chunk)?.[1] ?? ''
    const names = [...optBlock.matchAll(/name: '([^']+)'/g)].map((m) => m[1]!)
    const reqs = [...optBlock.matchAll(/requirement: '([^']+)'/g)].map((m) => m[1]!)
    names.forEach((n, i) => options.set(n, reqs[i] ?? ''))
    out.set(key, { key, kind, scope, options })
  }
  return out
}

const CATALOG = parseCatalog(catalogText)
const ALLOWED = new Set(CATALOG.keys())

/** 记录式宿主：apply() 干了什么就记什么，不做任何预先假设。 */
interface RecordedCall {
  inject: string
  registerOptions: Record<string, unknown> | null
  component: unknown
}

function recordingHost() {
  const calls: RecordedCall[] = []
  let pendingInject: string | null = null
  const logs: string[] = []
  const logger = {
    info: (...a: unknown[]) => logs.push(a.map(String).join(' ')),
    warn: (...a: unknown[]) => logs.push(a.map(String).join(' ')),
    error: (...a: unknown[]) => logs.push(a.map(String).join(' ')),
    debug: () => {},
    trace: () => {},
  }
  const ctx = {
    logger: () => logger,
    provide: () => () => {},
    effect: () => {},
    slots: {
      inject: (key: string, factory: () => unknown) => {
        pendingInject = key
        calls.push({ inject: key, registerOptions: null, component: undefined })
        try {
          factory()
        } finally {
          pendingInject = null
        }
        return () => {}
      },
      register: (options: Record<string, unknown>, component: unknown) => {
        const hit = calls.find((c) => c.inject === pendingInject && c.registerOptions === null)
        if (hit) {
          hit.registerOptions = options
          hit.component = component
        }
        return () => {}
      },
    },
  }
  return { ctx, calls, logs }
}

describe('slot keys align with the upstream DSH slot catalog', () => {
  it('the fixture really is the upstream catalog (shape + provenance)', () => {
    assert.ok(catalogText.includes('CLIENT_SLOT_API'), 'fixture must be the upstream catalog module')
    assert.ok(
      catalogText.includes('@module @deepseek-ai/dsh-cordis-client-runner/client/slot-catalog'),
      'fixture must carry the upstream module marker',
    )
    assert.equal(CATALOG.size, ALLOWED.size)
    assert.equal(CATALOG_PROVENANCE.keyCount, CATALOG.size, 'provenance keyCount must match parsed entries')
    // 上游 catalog 自称 sorted by key
    const keys = [...ALLOWED]
    assert.deepEqual(keys, [...keys].sort(), 'upstream catalog is sorted by key')
  })

  it("the issue's claimed `details` key does NOT exist in the authority (premise of #97 is wrong)", () => {
    assert.equal(ALLOWED.has('details'), false, "`details` is not a key in the upstream catalog")
    // `sidebar.right.pane.tab` —— issue #97 断言"不存在"的 key —— 实际存在
    const pane = CATALOG.get('sidebar.right.pane.tab')
    assert.ok(pane, 'sidebar.right.pane.tab IS in the upstream catalog')
    assert.equal(pane.kind, 'keyed')
    assert.equal(pane.scope, 'session')
  })

  it('the plugin only ever registers keys that exist in the authority', () => {
    const { ctx, calls } = recordingHost()
    // 直接走 apply() —— 用户实际执行的注册路径
    prGenius.apply(ctx as never, parseConfig({}))
    assert.ok(calls.length > 0, 'apply() must actually attempt slot registrations')

    for (const call of calls) {
      const entry = CATALOG.get(call.inject)
      assert.ok(
        entry,
        `injected key "${call.inject}" is NOT in the upstream catalog — refusing an invented slot name`,
      )
      // register options 的 `name` 必须就是 slot key（上游 example 的形状）
      assert.equal(
        call.registerOptions?.name,
        call.inject,
        `register options.name must be the slot key (${call.inject})`,
      )
      // 基数要求的 cell 选项必须在场，且名字正确
      const required = [...entry.options.entries()].filter(([, r]) => r === 'required').map(([n]) => n)
      for (const opt of required) {
        assert.ok(
          call.registerOptions && opt in call.registerOptions,
          `${call.inject} is ${entry.kind} and requires register option "${opt}"`,
        )
      }
      // 一次也不该塞进臆造的 kind/scope 之类的非选项字段
      for (const field of ['kind', 'scope']) {
        assert.ok(
          !(call.registerOptions && field in call.registerOptions),
          `${field} is not a register option (it belongs to the children declaration)`,
        )
      }
      console.log(
        `  ✓ inject(${call.inject}) kind=${entry.kind}/${entry.scope} opts=${JSON.stringify(call.registerOptions)}`,
      )
    }
  })

  it('every planned surface seat exists in the authority, and unmatched surfaces are reported', () => {
    const withoutSeat: string[] = []
    for (const surface of planRegistrations()) {
      if (!surface.seat) {
        withoutSeat.push(surface.id)
        continue
      }
      assert.ok(
        ALLOWED.has(surface.seat.key),
        `surface ${surface.id} points at unknown slot ${surface.seat.key}`,
      )
      const entry = CATALOG.get(surface.seat.key)!
      assert.equal(surface.seat.kind, entry.kind, `${surface.seat.key} kind must match the catalog`)
      assert.equal(surface.seat.scope, entry.scope, `${surface.seat.key} scope must match the catalog`)
      if (surface.seat.titleKey) {
        assert.ok(ALLOWED.has(surface.seat.titleKey), `title seat ${surface.seat.titleKey} must exist`)
      }
    }
    // 没有 slot 落点的界面：命令面走 ctx.command（Cordis 命令 API，不是 slot）
    assert.deepEqual(withoutSeat, [SURFACE_IDS.command])
    console.log(`  surfaces without a slot landing (by design): ${withoutSeat.join(', ')}`)
  })

  it('conservative degradation: an unconfirmed key is skipped, never registered', () => {
    assert.equal(isConfirmedSlotKey('details'), false)
    assert.equal(isConfirmedSlotKey('sidebar.right.pane.tab'), true)
    const bogus = {
      id: 'pr-genius.bogus',
      seat: { key: 'sidebar.right.pane.tab.totally.invented', kind: 'list', scope: 'root', cellOption: 'id' },
      kind: 'panel',
      mode: 'both',
    } as never
    assert.deepEqual(registrationCalls(bogus), [], 'unconfirmed key must yield no registration calls')
  })

  it('kind/scope declarations match the catalog (the v2.1.2 single-vs-keyed bug class)', () => {
    for (const [key, spec] of Object.entries(SLOT_DECLARATIONS)) {
      const entry = CATALOG.get(key)
      assert.ok(entry, `SLOT_DECLARATIONS key ${key} must exist upstream`)
      assert.equal(spec.kind, entry.kind, `${key}: declared kind must match catalog`)
      assert.equal(spec.scope, entry.scope, `${key}: declared scope must match catalog`)
      console.log(`  ✓ declaration ${key} = ${spec.kind}/${spec.scope}`)
    }
  })

  it('generated CONFIRMED_SLOT_KEYS is exactly the parsed authority (no hand-typed drift)', () => {
    assert.equal(CONFIRMED_SLOT_KEYS.length, ALLOWED.size)
    for (const key of CONFIRMED_SLOT_KEYS) {
      assert.ok(ALLOWED.has(key), `generated list has key ${key} missing from the authority`)
    }
  })
})
