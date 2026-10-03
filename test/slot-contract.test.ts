/**
 * slot 契约测试 —— 对照 DSH SDK slot-catalog 的实抓快照，不对照任何自造假设。
 *
 * 权威源：deepseek-ai/deepseek-harness
 *   packages/extensions/cordis-client-runner/src/client/slot-catalog.ts
 * 2026-10-03 gh api 实抓，机械抽取为 docs/slot-catalog-evidence.json（92 keys）。
 * 注意：deepseek-ai/deepseek-harness-sdk 这个仓库不存在（404），catalog 在
 * deepseek-harness 里；`details` 不是 slot key（root doc 里的 AppFrame 座位名）。
 *
 * 这些断言不证明宿主会渲染我们的组件（需 DSH 运行时），只证明：
 *   1. 我们注册的 key 在权威 catalog 里真实存在；
 *   2. kind/scope 与 catalog 一致；
 *   3. register() 参数形状与 catalog example 一致（list→id，keyed→key）；
 *   4. 未核对的 key 会被保守拒绝（不注册）。
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, it } from 'vitest'
import {
  SLOT_DECLARATIONS,
  VERIFIED_SLOT_CONTRACTS,
  slotRegisterDef,
} from '../src/client/slots.ts'
import { SURFACE_IDS, planRegistrations } from '../src/ui/surfaces.ts'

interface CatalogEntry {
  key: string
  kind: string
  scope: string
  replaceRisk: string
  declaredBy: string
  summary: string
}

interface CatalogSnapshot {
  provenance: Record<string, string>
  entries: CatalogEntry[]
}

const snapshot = JSON.parse(
  readFileSync(
    fileURLToPath(new URL('../docs/slot-catalog-evidence.json', import.meta.url)),
    'utf8',
  ),
) as CatalogSnapshot

const byKey = new Map(snapshot.entries.map((e) => [e.key, e]))

describe('slot catalog evidence', () => {
  it('snapshot carries its provenance and a non-trivial key set', () => {
    assert.equal(snapshot.provenance.source, 'deepseek-ai/deepseek-harness')
    assert.ok(snapshot.entries.length >= 50, `catalog snapshot too small: ${snapshot.entries.length}`)
    // 反证两条流传过的说法，判据只能是 catalog 本身：
    assert.equal(byKey.has('details'), false, 'details must not be a slot key (AppFrame seat name only)')
    assert.equal(byKey.has('sidebar.right.pane.tab'), true, 'sidebar.right.pane.tab is a real key')
    assert.equal(byKey.get('sidebar.right.pane.tab')?.kind, 'keyed')
    assert.equal(byKey.get('sidebar.right.pane.tab')?.replaceRisk, 'none')
    assert.equal(byKey.get('conversation.view')?.kind, 'list')
    assert.equal(byKey.get('sidebar.footer.action')?.kind, 'list')
    assert.equal(byKey.get('settings.plugins.tab')?.kind, 'list')
  })
})

describe('registered slots match the catalog', () => {
  it('every VERIFIED_SLOT_CONTRACTS entry exists in the catalog with the same kind/scope', () => {
    for (const [slot, contract] of Object.entries(VERIFIED_SLOT_CONTRACTS)) {
      const entry = byKey.get(slot)
      assert.ok(entry, `slot ${slot} is not in the authoritative catalog`)
      assert.equal(contract.kind, entry.kind, `kind mismatch for ${slot}`)
      assert.equal(contract.scope, entry.scope, `scope mismatch for ${slot}`)
      assert.equal(
        contract.entryShape,
        entry.kind === 'keyed' ? 'key' : 'id',
        `entry shape mismatch for ${slot}`,
      )
    }
  })

  it('every surface in SURFACE_PLAN lands on a catalog-verified slot', () => {
    for (const surface of planRegistrations()) {
      if (surface.kind === 'command') {
        // ctx.command 是 cordis 命令面，不是 slot key —— catalog 里查无此项是预期。
        assert.equal(byKey.has('ctx.command'), false)
        continue
      }
      assert.ok(
        Object.hasOwn(VERIFIED_SLOT_CONTRACTS, surface.slot),
        `surface ${surface.id} planned on unverified slot ${surface.slot}`,
      )
      assert.ok(byKey.has(surface.slot))
    }
  })

  it('SLOT_DECLARATIONS kinds match the catalog', () => {
    for (const [slot, def] of Object.entries(SLOT_DECLARATIONS)) {
      const entry = byKey.get(slot)
      assert.ok(entry, `SLOT_DECLARATIONS has unknown slot ${slot}`)
      assert.equal(def.kind, entry.kind, `declaration kind mismatch for ${slot}`)
      assert.equal(def.scope, entry.scope, `declaration scope mismatch for ${slot}`)
    }
  })

  it('register() defs follow the catalog example shape (list→id, keyed→key)', () => {
    const footer = slotRegisterDef('sidebar.footer.action', SURFACE_IDS.dashboard, 'PR Genius')
    assert.deepEqual(footer, {
      name: 'sidebar.footer.action',
      id: SURFACE_IDS.dashboard,
      label: 'PR Genius',
    })
    const tab = slotRegisterDef('conversation.view', SURFACE_IDS.advisorTab, 'Advisor')
    assert.deepEqual(tab, { name: 'conversation.view', id: SURFACE_IDS.advisorTab, label: 'Advisor' })
    const panel = slotRegisterDef('sidebar.right.pane.tab', SURFACE_IDS.advisorPanel)
    assert.deepEqual(panel, { name: 'sidebar.right.pane.tab', key: SURFACE_IDS.advisorPanel })
    const prefs = slotRegisterDef('settings.plugins.tab', SURFACE_IDS.preferences, 'pr-genius')
    assert.deepEqual(prefs, {
      name: 'settings.plugins.tab',
      id: SURFACE_IDS.preferences,
      label: 'pr-genius',
    })
  })

  it('conservative degrade: an unverified slot key is refused (no guessed registration)', () => {
    assert.equal(slotRegisterDef('details', 'pr-genius.x'), null)
    assert.equal(slotRegisterDef('sidebar.right.pane.tab.title', 'pr-genius.x'), null)
    assert.equal(slotRegisterDef('rightbar.session', 'pr-genius.x'), null)
  })
})
