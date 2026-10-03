/**
 * 发版 smoke gate 自身的测试（issue #96）。
 *
 * 为什么 gate 也要有测试：gate 是发版前最后一道关，它自己悄悄坏掉比没有 gate
 * 更糟——会把坏的发版放行成绿的。这里锁三件事：
 *   1. catalog 解析器在「marker 里带类型标注」时不被 `[]` 骗走（真的踩过）
 *   2. 反循环自检真能抓到「把 slot 名种进代码」，也不会被注释误报
 *   3. 本仓库 gate 源码里此刻没有任何硬编码 slot 名 —— 防止后来的人又写死一张表
 *
 * 刻意不在此处断言任何具体 slot 名的「应该存在」：那正是循环验证。
 * slot 名的事实只来自 DSH SDK，测试只验「取表的管道是通的、来源是外部的」。
 */
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it } from 'vitest'
import {
  assertNoHardcodedSlotKeys,
  extractArrayLiteral,
  loadSlotCatalog,
  UPSTREAM,
} from '../scripts/release-smoke/slot-catalog.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = join(HERE, '..')

describe('extractArrayLiteral', () => {
  it('slices and evaluates a plain array literal', () => {
    const src = 'const X = [1, 2, 3]\nconst Y = 4'
    assert.deepEqual(extractArrayLiteral(src, 'const X = ['), [1, 2, 3])
  })

  it('is not fooled by `[]` inside the marker type annotation', () => {
    // 真实踩坑：`ClientSlotEntry[]` 里的那对方括号是空数组，
    // 拿 marker 后的第一个 '[' 起算会切出空表，让 gate 误以为 catalog 是空的。
    const src = "export const API: readonly Entry[] = [\n  { key: 'a' },\n  { key: 'b' },\n]\n"
    const out = extractArrayLiteral(src, 'export const API: readonly Entry[] = [')
    assert.equal(out.length, 2)
    assert.deepEqual(out.map((e) => (e as { key: string }).key), ['a', 'b'])
  })

  it('throws on an absent marker', () => {
    assert.throws(() => extractArrayLiteral('const A = []', 'const MISSING = ['), /marker not found/)
  })

  it('throws on unbalanced brackets', () => {
    assert.throws(() => extractArrayLiteral('const A = [1, 2', 'const A = ['), /unbalanced/)
  })
})

describe('loadSlotCatalog — 管道是通的，来源是外部的', () => {
  it('loads the pinned SDK catalog from the installed package', async () => {
    const r = await loadSlotCatalog({ source: 'npm', cwd: REPO_ROOT })
    assert.equal(r.ok, true, `npm catalog should load, got: ${r.error ?? ''}`)
    assert.ok(r.primary, 'primary must be set')
    // 出处必须是「从 SDK 包里取」，不是本仓库写的表 —— 反循环的前提。
    assert.equal(r.primary.provenance.kind, 'installed-sdk-bundle')
    assert.equal(r.primary.provenance.package, UPSTREAM.npmPackage)
    assert.ok(
      typeof r.primary.provenance.packageVersion === 'string' &&
        r.primary.provenance.packageVersion.length > 0,
      'provenance must pin the SDK version — otherwise「验的是哪一版」无从对账',
    )
    // 表必须是张真表，不是解析坏了剩两三条。这个下界不是 slot 名，只是「解析没塌」。
    assert.ok(r.primary.entries.length >= 30, `catalog too small: ${r.primary.entries.length}`)
    for (const e of r.primary.entries) {
      assert.equal(typeof e.key, 'string')
      assert.ok(e.key.length > 0)
      assert.ok(['single', 'list', 'keyed', 'chain'].includes(e.kind), `bad kind on ${e.key}: ${e.kind}`)
      assert.ok(['root', 'session', 'session-maybe'].includes(e.scope), `bad scope on ${e.key}: ${e.scope}`)
      assert.ok(Array.isArray(e.registerOptions))
    }
    // 唯一性：重复 key 意味着解析切错了，会让「在不在表里」的判定失真。
    const keys = r.primary.entries.map((e) => e.key)
    assert.equal(new Set(keys).size, keys.length, 'catalog keys must be unique')
  })

  it('names the upstream source module so a reader can chase it', async () => {
    const r = await loadSlotCatalog({ source: 'npm', cwd: REPO_ROOT })
    assert.ok(r.primary)
    assert.ok(
      (r.primary.provenance.upstreamModule ?? '').includes(UPSTREAM.repo),
      `provenance must point at ${UPSTREAM.repo}, got ${r.primary.provenance.upstreamModule}`,
    )
    assert.ok(
      (r.primary.provenance.upstreamModule ?? '').includes(UPSTREAM.path),
      `provenance must name ${UPSTREAM.path}`,
    )
  })
})

describe('diffCatalogs — 漂移必须两侧都算得出来', () => {
  const mk = (source: string, keys: Array<[string, string, string]>) =>
    ({
      ok: true,
      source: 'npm' as const,
      provenance: { kind: 'installed-sdk-bundle' as const, note: source },
      entries: keys.map(([key, kind, scope]) => ({
        key,
        kind,
        scope,
        registerOptions: [],
        replaceRisk: null,
        declaredBy: null,
        occupants: [],
        source: null,
        summary: null,
      })),
    })

  it('reports keys present on each side and kind/scope changes', async () => {
    const { diffCatalogs } = await import('../scripts/release-smoke/slot-catalog.mjs')
    const a = mk('a', [['shared', 'list', 'root'], ['only-a', 'single', 'session'], ['moved', 'single', 'root']])
    const b = mk('b', [['shared', 'list', 'root'], ['only-b', 'keyed', 'session'], ['only-b2', 'list', 'root'], ['moved', 'single', 'session']])
    const d = diffCatalogs(a, b)
    assert.equal(d.aCount, 3)
    assert.equal(d.bCount, 4)
    // 回归锁：曾经把 onlyInB 写成「在 B 里却不在 B 里」，恒为空——上游多出来的 50+ 个 key
    // 被静默吞掉，漂移报告看起来「没多少变化」。两侧必须都真的算。
    assert.deepEqual(d.onlyInA, ['only-a'])
    assert.deepEqual(d.onlyInB, ['only-b', 'only-b2'])
    assert.deepEqual(d.kindOrScopeChanged, [{ key: 'moved', a: 'single/root', b: 'single/session' }])
  })
})

describe('assertNoHardcodedSlotKeys — 反循环自检', () => {
  const keys = ['sidebar.footer.action', 'conversation.view', 'details']

  it('flags a slot key planted in code', () => {
    const src = "const ALLOW = new Set(['sidebar.footer.action'])\n"
    const r = assertNoHardcodedSlotKeys([{ file: 'x.mjs', source: src }], keys)
    assert.equal(r.ok, false)
    assert.equal(r.offenders.length, 1)
    assert.equal(r.offenders[0].key, 'sidebar.footer.action')
    assert.equal(r.offenders[0].line, 1)
  })

  it('does not flag a slot key that only appears in a comment', () => {
    const src = "/** 例如 'sidebar.footer.action'。 */\nconst X = 1\n"
    const r = assertNoHardcodedSlotKeys([{ file: 'x.mjs', source: src }], keys)
    assert.equal(r.ok, true, JSON.stringify(r.offenders))
  })

  it('does not flag ordinary non-slot strings', () => {
    const src = "const A = 'npm'\nconst B = 'auto'\nconst C = 'lib/client.js'\n"
    const r = assertNoHardcodedSlotKeys([{ file: 'x.mjs', source: src }], keys)
    assert.equal(r.ok, true)
  })
})

describe('本仓库 gate 源码当前不得含硬编码 slot 名', () => {
  it('scan of the shipped gate sources is clean against the live SDK catalog', async () => {
    const r = await loadSlotCatalog({ source: 'npm', cwd: REPO_ROOT })
    assert.ok(r.ok && r.primary, 'need a live catalog to run the anti-circular scan')
    const files = ['scripts/release-smoke/slot-catalog.mjs', 'scripts/release-smoke/runtime-smoke-gate.mjs']
    const scan = assertNoHardcodedSlotKeys(
      files.map((f) => ({ file: f, source: readFileSync(join(REPO_ROOT, f), 'utf8') })),
      r.primary.entries.map((e) => e.key),
    )
    assert.deepEqual(
      scan.offenders,
      [],
      `gate 源码里出现了权威 catalog 的 slot 名字面量 —— 那就是循环验证：` +
        `自己出题自己批卷，只能确认错误，无法证伪。命中：${JSON.stringify(scan.offenders)}`,
    )
    assert.equal(scan.ok, true)
  })

  it('the gate never treats a non-SDK provenance as authoritative', () => {
    const src = readFileSync(join(REPO_ROOT, 'scripts/release-smoke/runtime-smoke-gate.mjs'), 'utf8')
    assert.ok(
      src.includes('ALLOWED_PROVENANCE'),
      'gate 必须校验 catalog 出处是 SDK 侧，否则本地写一张表也能冒充权威',
    )
    assert.ok(
      src.includes('installed-sdk-bundle'),
      'gate 必须接受「已安装 SDK 包」这种出处',
    )
    assert.ok(
      !/ALLOWED_PROVENANCE\s*=\s*new Set\(\[\s*['"]inline['"]/.test(src),
      "gate 不得把 'inline' 当作合法 catalog 出处",
    )
  })
})
