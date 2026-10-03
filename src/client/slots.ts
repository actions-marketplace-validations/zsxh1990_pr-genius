/**
 * 侧边栏 / 会话界面的 slot 声明 —— 编译期契约，不是运行时注册。
 *
 * 真实形态（读 @deepseek-ai/dsh-client-ui-slots 的类型得来，不是猜的）：
 *   - slot 通过 **模块增强 `SlotMap`** 声明，`register` 才把组件贡献进已声明的空位
 *   - kind: 'single' | 'list' | 'keyed' | 'chain'；scope: 'root' | 'session-maybe' | 'session'
 *   - i18n 同样走模块增强 `LocaleNamespaceMap`
 *   - 组件是 React，props 是「Face」（hooks + 生命周期动词），如 CordisPanelFace
 *
 * 诚实边界：本机没有 DEEPSEEK_API_KEY，未在 DSH 运行时里加载过。这里保证的是
 * **类型契约正确**（编译能过、slot 名与 kind/scope 与平台约定一致），渲染需真宿主验证。
 */
import type { SlotEntryDef } from '@deepseek-ai/dsh-client-ui-slots'

/** 侧边栏脚部的跨会话总览 —— 对应 dsh-context 的 Context Dashboard。 */
export { SETTINGS_SURFACES } from '../ui/surfaces.ts'
import { SETTINGS_SURFACES } from '../ui/surfaces.ts'

/** 落点全部来自 ui/surfaces.ts —— 一张表，不再各写各的（issue #95 的根因） */
export const DASHBOARD_SLOT = SETTINGS_SURFACES.sidebar
export const ADVISOR_TAB_SLOT = SETTINGS_SURFACES.tab
export const ADVISOR_PANEL_SLOT = SETTINGS_SURFACES.panel
export const PREFERENCES_SLOT = SETTINGS_SURFACES.plugins

declare module '@deepseek-ai/dsh-client-ui-slots' {
  interface SlotMap {
    /**
     * 跨会话总览：在飞 PR 健康、风险分布、知识库规模。挂在侧边栏脚部。
     * root 作用域 —— 它不依赖某个会话。
     */
    // 同一个 list slot 里 Dashboard 与 Preferences 各占一项。
    'sidebar.footer.action': { kind: 'list'; scope: 'root' }
    /**
     * 顾问 Tab：当前 diff 的实时诊断。挂在会话视图，因此必须是 session 作用域。
     */
    'conversation.view': { kind: 'single'; scope: 'session' }
    /** 同一诊断的右栏投影 —— 共用一套数据，只换落点。 */
    'sidebar.right.pane.tab': { kind: 'single'; scope: 'session' }
    /** 插件偏好卡：落点、语言、维护者模式、风险过滤。 */
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
 * 注意 slot 名是**键**，不在 entry 里：SlotEntryDef 只有 kind/scope/owner/
 * keyProps/hookContext/inject，没有 name/key 字段。
 */
export const SLOT_DECLARATIONS = {
  [DASHBOARD_SLOT]: { kind: 'list', scope: 'root' },
  [ADVISOR_TAB_SLOT]: { kind: 'single', scope: 'session' },
  [ADVISOR_PANEL_SLOT]: { kind: 'single', scope: 'session' },
} as const satisfies Record<string, SlotEntryDef>
