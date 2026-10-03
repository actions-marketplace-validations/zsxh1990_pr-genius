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
 * catalog 实测结论（与此前的口头/文档说法冲突处以 catalog 为准）：
 *   - 不存在名为 `details` 的 slot key —— `details` 只是 `root` 的 doc 里
 *     AppFrame 内部座位名（sidebar / conversation / details / shell.overlay），
 *     不是可注册的 SlotMap key。右栏内容的可注册 key 是
 *     `sidebar.right.pane.tab`（keyed, session, additive）。
 *   - `sidebar.right.pane.tab` 是 **keyed**（不是 single），注册必须带 `key`；
 *   - `conversation.view` 是 **list**（不是 single），注册必须带 `id`；
 *   - `sidebar.footer.action` 是 list / root（与此前一致）；
 *   - `settings.plugins.tab` 是 list / root（Preferences 的落点）。
 *
 * 保守降级：注册只走下表 VERIFIED_SLOT_CONTRACTS 里 catalog 核对过的槽位；
 * 不在表里的落点一律不注册、只记 warn —— 绝不用猜测的 key 注册。
 */
import type { SlotEntryDef } from '@deepseek-ai/dsh-client-ui-slots'

/** 落点全部来自 ui/surfaces.ts —— 一张表，不再各写各的（issue #95 的根因） */
export { SETTINGS_SURFACES } from '../ui/surfaces.ts'
import { SETTINGS_SURFACES } from '../ui/surfaces.ts'

export const DASHBOARD_SLOT = SETTINGS_SURFACES.sidebar
export const ADVISOR_TAB_SLOT = SETTINGS_SURFACES.tab
export const ADVISOR_PANEL_SLOT = SETTINGS_SURFACES.panel
export const PREFERENCES_SLOT = SETTINGS_SURFACES.plugins

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
    /** 侧边栏脚部动作区（list / root）：Dashboard 与维护入口的落点。 */
    'sidebar.footer.action': { kind: 'list'; scope: 'root' }
    /** 会话视图标签页（list / session）：顾问 Tab 与 Chat/Trajectory 并列。 */
    'conversation.view': { kind: 'list'; scope: 'session' }
    /**
     * 右栏标签页正文（keyed / session）：owner 以 key 分派。
     * 保守声明：仅在 owner 分派到我们注册的 key 时渲染；不做右栏整体接管
     * （rightbar.session 是 single + shadows-shipped-ui，会顶掉宿主自带右栏）。
     */
    'sidebar.right.pane.tab': { kind: 'keyed'; scope: 'session' }
    /** 插件设置页（list / root）：Preferences 落点。 */
    'settings.plugins.tab': { kind: 'list'; scope: 'root' }
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

/**
 * 供 register() 的 children 声明表 —— 形状是「slot 名 → kind/scope」。
 * SlotEntryDef 没有 name/key 字段：slot 名是键，cell 形状见 VERIFIED_SLOT_CONTRACTS。
 */
export const SLOT_DECLARATIONS = {
  [DASHBOARD_SLOT]: { kind: 'list', scope: 'root' },
  [ADVISOR_TAB_SLOT]: { kind: 'list', scope: 'session' },
  [ADVISOR_PANEL_SLOT]: { kind: 'keyed', scope: 'session' },
  [PREFERENCES_SLOT]: { kind: 'list', scope: 'root' },
} as const satisfies Record<string, SlotEntryDef>
