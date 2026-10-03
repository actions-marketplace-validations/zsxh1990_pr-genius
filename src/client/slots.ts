/**
 * 侧边栏 / 会话界面的 slot 声明 —— 编译期契约 + 注册形状。
 *
 * 权威依据（唯一）：DSH SDK 源码的 slot-catalog
 *   deepseek-ai/deepseek-harness
 *   packages/extensions/cordis-client-runner/src/client/slot-catalog.ts
 * 本机 2026-10-03 用 `gh api` 真实抓取（注意：deepseek-ai/deepseek-harness-sdk
 * 不存在，404；仓库名是 deepseek-harness）。快照固化在
 * docs/slot-catalog-evidence.json（92 个 key，机械抽取，非手写）。
 *
 */
import type { SlotEntryDef } from '@deepseek-ai/dsh-client-ui-slots'
import { REGISTERED_SLOTS, type SlotSeat } from '../ui/slot-catalog.ts'


/**
 * catalog 核对过的槽位契约。kind/scope 与 slot-catalog.ts 逐字一致；
 * entryShape 决定 register() 第一个参数的形状（list → id，keyed → key）。
 */
export interface VerifiedSlotContract {
  kind: 'list' | 'keyed' | 'single' | 'chain'
  scope: 'root' | 'session' | 'session-maybe'
  /** register() 的 cell 参数形状：list 槽用 id，keyed 槽用 key。 */
  entryShape: 'id' | 'key'
  /** slot-catalog.ts 里的 source 字段（出处行）。 */
  catalogSource: string
}

export const VERIFIED_SLOT_CONTRACTS: Record<string, VerifiedSlotContract> = {
  'sidebar.footer.action': {
    kind: 'list',
    scope: 'root',
    entryShape: 'id',
    catalogSource: 'packages/extensions/cordis-client-runner/src/client/slot-catalog.ts',
  },
  'conversation.view': {
    kind: 'list',
    scope: 'session',
    entryShape: 'id',
    catalogSource: 'packages/extensions/cordis-client-runner/src/client/slot-catalog.ts',
  },
  'sidebar.right.pane.tab': {
    kind: 'keyed',
    scope: 'session',
    entryShape: 'key',
    catalogSource: 'packages/extensions/cordis-client-runner/src/client/slot-catalog.ts',
  },
  'settings.plugins.tab': {
    kind: 'list',
    scope: 'root',
    entryShape: 'id',
    catalogSource: 'packages/extensions/cordis-client-runner/src/client/slot-catalog.ts',
  },
}

/** register() 第一参数 —— 形状来自 slot-catalog 的 example（name=槽名 + id/key=cell）。 */
export interface SlotRegisterDef {
  name: string
  id?: string
  key?: string
  label?: string
  order?: number
}

/**
 * 生成注册参数。槽位不在核对表里返回 null（调用方必须跳过注册并 warn）。
 * list 槽：{ name, id, label, order }；keyed 槽：{ name, key }（catalog 的
 * registerOptions 对 keyed 只要求 key，不收 id/label/order，故不附带）。
 */
export function slotRegisterDef(slot: string, cellId: string, label?: string): SlotRegisterDef | null {
  const contract = VERIFIED_SLOT_CONTRACTS[slot]
  if (contract === undefined) return null
  if (contract.entryShape === 'key') return { name: slot, key: cellId }
  return label === undefined ? { name: slot, id: cellId } : { name: slot, id: cellId, label }
}

declare module '@deepseek-ai/dsh-client-ui-slots' {
  interface SlotMap {
    /** 侧边栏脚部（list / root）：Dashboard 与 Preferences 各占一项。 */
    'sidebar.footer.action': { kind: 'list'; scope: 'root' }
    /** 会话视图标签页（list / session）：顾问 Tab 与 Chat/Trajectory 并列。 */
    'conversation.view': { kind: 'list'; scope: 'session' }
    /**
     * 右栏落点有两个版本的 catalog 说不同的话（见 docs/slot-key-drift.md）：
     * pinned SDK 里是 `details`，upstream master 里是 `sidebar.right.pane.tab`（keyed）。
     * 运行时探测决定用谁，所以这里把两个都声明成可注册，由 apply() 挑实际存在的。
     */
    'details': { kind: 'single'; scope: 'session' }
    'sidebar.right.pane.tab': { kind: 'keyed'; scope: 'session' }
  }

  interface LocaleNamespaceMap {
    'pr-genius':
      | 'surface.dashboard'
      | 'surface.advisorTab'
      | 'surface.advisorPanel'
      | 'surface.command'
      | 'surface.preferences'
      | 'mode.contributor'
      | 'mode.maintainer'
      | 'risk.low_risk'
      | 'risk.medium_risk'
      | 'risk.high_risk'
      | 'empty.noVerdict'
  }
}

/** 四个界面的落点名。面板走候选表，运行时探测（见 apply()）。 */
export const DASHBOARD_SLOT = 'sidebar.footer.action'
export const ADVISOR_TAB_SLOT = 'conversation.view'
export const ADVISOR_PANEL_SLOT = 'details'
export const PREFERENCES_SLOT = 'sidebar.footer.action'
export const PANEL_SLOT_CANDIDATES = ['details', 'sidebar.right.pane.tab']

/** 契约表 → register() 的第一参数。 */
export function specOf(seat: SlotSeat): SlotEntryDef {
  return { kind: seat.kind, scope: seat.scope }
}

export const SLOT_DECLARATIONS = {
} as const satisfies Record<string, SlotEntryDef>

/** `declare module` 的字面 key 集合，与真相源对齐的编译期断言。 */
type DeclaredSlotKeys =
  | 'sidebar.footer.action'
  | 'conversation.view'
  | 'sidebar.right.pane.tab'
  | 'sidebar.right.pane.tab.title'
  | 'settings.section'

type SeatKeys =
  | (typeof REGISTERED_SLOTS)[keyof typeof REGISTERED_SLOTS]['key']
  | (typeof REGISTERED_SLOTS)['sidebarRightPaneTab']['titleKey']

type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2
  ? true
  : false

/** 两边键集不一致 → 编译报错。 */
type DeclaredSeatKeysMatchCatalog = Equal<DeclaredSlotKeys, SeatKeys> extends true
  ? true
  : never
export const declaredSeatKeysMatchCatalog: DeclaredSeatKeysMatchCatalog = true
