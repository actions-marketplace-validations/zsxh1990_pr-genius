/**
 * 侧边栏 / 会话界面的 slot 声明 —— 编译期契约，不是运行时注册。
 *
 * 真实形态（读 @deepseek-ai/dsh-client-ui-slots 的类型得来，不是猜的）：
 *   - slot 通过 **模块增强 `SlotMap`** 声明，`register` 才把组件贡献进已声明的空位
 *   - kind: 'single' | 'list' | 'keyed' | 'chain'；scope: 'root' | 'session-maybe' | 'session'
 *   - i18n 同样走模块增强 `LocaleNamespaceMap`
 *   - 组件是 React，props 是「Face」（hooks + 生命周期动词），如 CordisPanelFace
 *
 * slot 名 / kind / scope 的**唯一真相源是 `../ui/slot-catalog.ts`**（上游
 * DSH slot-catalog 快照的座位表）。本文件只做类型增强与派生常量，不再各写各的。
 * `declare module` 里的字面 key 是 TypeScript 的语法限制（模块增强必须写字面键），
 * 下面的 `DeclaredSeatKeysMatchCatalog` 断言保证它们与真相源一致；不一致就编译不过。
 *
 * 诚实边界：本机没有 DEEPSEEK_API_KEY，未在 DSH 运行时里加载过。这里保证的是
 * **类型契约正确**（编译能过、slot 名与 kind/scope 与平台约定一致），渲染需真宿主验证。
 */
import type { SlotEntryDef } from '@deepseek-ai/dsh-client-ui-slots'
import { REGISTERED_SLOTS, type SlotSeat } from '../ui/slot-catalog.ts'

/** 落点全部来自 ui/slot-catalog.ts —— 一张表，不再各写各的（issue #95 的根因） */
export const DASHBOARD_SLOT = REGISTERED_SLOTS.sidebarFooterAction.key
export const ADVISOR_TAB_SLOT = REGISTERED_SLOTS.conversationView.key
export const ADVISOR_PANEL_SLOT = REGISTERED_SLOTS.sidebarRightPaneTab.key
export const PREFERENCES_SLOT = REGISTERED_SLOTS.settingsSection.key

declare module '@deepseek-ai/dsh-client-ui-slots' {
  interface SlotMap {
    /**
     * 跨会话总览：在飞 PR 健康、风险分布、知识库规模。挂在侧边栏脚部。
     * root 作用域 —— 它不依赖某个会话。list 基数：Dashboard 与 Preferences
     * 可以各占一项（register 用各自的 `id` 区分）。
     */
    'sidebar.footer.action': { kind: 'list'; scope: 'root' }
    /**
     * 顾问 Tab：当前 diff 的实时诊断。挂在会话视图，因此必须是 session 作用域。
     * list 基数（不是 single）：与 Chat/Trajectory 并列，register 需带 `id`。
     */
    'conversation.view': { kind: 'list'; scope: 'session' }
    /**
     * 同一诊断的右栏投影 —— 共用一套数据，只换落点。
     * keyed 基数（不是 single）：register 必须带 `key`，keyDomain 开放
     * （"any string the owner dispatches"）。
     */
    'sidebar.right.pane.tab': { kind: 'keyed'; scope: 'session' }
    /** 右栏面板的标题席，与正文席成对（上游 occupants 均为 Body+Title）。 */
    'sidebar.right.pane.tab.title': { kind: 'keyed'; scope: 'session' }
    /** 插件偏好页：落点、语言、维护者模式、风险过滤。一列表项一页。 */
    'settings.section': { kind: 'list'; scope: 'root' }
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
 * 供 register() 的 children 声明表 —— 形状是「slot 名 → 运行时分派规格」。
 * kind/scope 从 REGISTERED_SLOTS 派生，不在此重抄一遍。
 * 注意 slot 名是**键**，不在 entry 里：SlotEntryDef 只有 kind/scope/owner/
 * keyProps/hookContext/inject，没有 name/key 字段。
 */
function specOf(seat: SlotSeat): SlotEntryDef {
  return { kind: seat.kind, scope: seat.scope }
}

export const SLOT_DECLARATIONS = {
  [DASHBOARD_SLOT]: specOf(REGISTERED_SLOTS.sidebarFooterAction),
  [ADVISOR_TAB_SLOT]: specOf(REGISTERED_SLOTS.conversationView),
  [ADVISOR_PANEL_SLOT]: specOf(REGISTERED_SLOTS.sidebarRightPaneTab),
  [REGISTERED_SLOTS.sidebarRightPaneTab.titleKey!]: specOf(
    REGISTERED_SLOTS.sidebarRightPaneTab,
  ),
  [PREFERENCES_SLOT]: specOf(REGISTERED_SLOTS.settingsSection),
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
