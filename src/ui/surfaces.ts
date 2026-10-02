/**
 * 四个界面 + 维护者模式的注册层。
 *
 * 落点依据 dshfind 官方教程抽取的权威 slot 清单（见 docs/dsh-ui-slot-api.md）：
 *   - `conversation.view` — 会话视图的标签页（dsh-context 的 Context tab 就在这里）
 *   - `ui-sidebar`        — Workspace 与会话导航（Dashboard 落这里，脚部 Settings 之上）
 *   - `ui-settings-plugins` — 插件设置（Preferences 卡落这里）
 *   - `ctx.command`       — 斜杠命令
 *
 * 注册形态：
 *   ctx.slots.inject(slotName, () => ctx.slots.register({ name, ...kind }, Component))
 * 「声明 = 渲染授权 = 运行时规范」，卸载时组件 / slot 条目 / store 一并递归撤销。
 *
 * 诚实边界：本机没有 DEEPSEEK_API_KEY，未跑真 DSH。这里只保证注册形状与契约一致、
 * TypeScript 编译通过；渲染与运行时行为需 DSH 运行时验证，本机未执行。
 */
/** 权威 slot 名（core/12-web-ui 的 slot 表）。 */
export const SLOTS = {
  /** 聊天流里的一行节点。 */
  chatNode: 'conversation.chat.node',
  /** 输入区上方的卡片栈。 */
  inputDock: 'conversation.input.dock',
  /** 会话视图的标签页 —— 顾问 Tab 的落点。 */
  view: 'conversation.view',
  /** 应用根。 */
  root: 'root',
} as const

/** 设置面（dsh 0.1.7+ 在侧边栏 Plugins → bundle 页 → Configuration）。 */
export const SETTINGS_SURFACES = {
  plugins: 'ui-settings-plugins',
  pluginInventory: 'ui-settings-plugin-inventory',
  sidebar: 'ui-sidebar',
} as const

/** 四个界面的稳定标识 —— 配置与测试都引用这些常量，不写字面量。 */
export const SURFACE_IDS = {
  dashboard: 'pr-genius.dashboard',
  advisorTab: 'pr-genius.advisor-tab',
  advisorPanel: 'pr-genius.advisor-panel',
  command: 'pr-genius',
  preferences: 'pr-genius.preferences',
} as const

/** 维护者模式：切换只换投影，不换数据层 —— 两侧共用 kb 与 mcp 桥。 */
export type WorkMode = 'contributor' | 'maintainer'

export interface SurfaceRegistration {
  id: string
  slot: string
  kind: 'dashboard' | 'tab' | 'panel' | 'command' | 'settings'
  mode: WorkMode | 'both'
}

/**
 * 要注册的界面清单。维护者模式不是第二套界面，而是同一组界面的另一投影，
 * 所以它标记为 `mode: 'both'` 并由一个开关决定渲染哪一侧的数据。
 */
export const SURFACE_PLAN: SurfaceRegistration[] = [
  {
    id: SURFACE_IDS.dashboard,
    slot: SETTINGS_SURFACES.sidebar,
    kind: 'dashboard',
    mode: 'both',
  },
  {
    id: SURFACE_IDS.advisorTab,
    slot: SLOTS.view,
    kind: 'tab',
    mode: 'both',
  },
  {
    id: SURFACE_IDS.advisorPanel,
    slot: SETTINGS_SURFACES.sidebar,
    kind: 'panel',
    mode: 'both',
  },
  {
    id: SURFACE_IDS.command,
    slot: 'ctx.command',
    kind: 'command',
    mode: 'both',
  },
  {
    id: SURFACE_IDS.preferences,
    slot: SETTINGS_SURFACES.plugins,
    kind: 'settings',
    mode: 'both',
  },
]

/**
 * 注册一个界面。返回 disposer —— Cordis 的「注册是可逆的副作用」，框架卸载时
 * 会调用它，贡献的组件 / slot 条目 / store 一并撤销。
 *
 * 这里刻意不写死组件实现：组件由调用方注入，本层只负责把「落点」这件事收敛到
 * 一处可核对的表里。好处是四个界面的 slot 归属能被测试断言，而不用渲染任何东西。
 */
export function planRegistrations(): SurfaceRegistration[] {
  return SURFACE_PLAN.map((r) => ({ ...r }))
}

/**
 * 断言某个界面挂在正确的 slot 上 —— 无需运行时即可验证「侧边栏安装配置架构」。
 * 契约或抄写出错时这里会红，而不是等到用户打开面板才发现空白。
 */
export function assertSlotPlacement(id: string, expectedSlot: string): void {
  const hit = SURFACE_PLAN.find((r) => r.id === id)
  if (!hit) throw new Error(`unknown surface id: ${id}`)
  if (hit.slot !== expectedSlot) {
    throw new Error(
      `surface ${id} is planned for slot ${hit.slot}, expected ${expectedSlot}`,
    )
  }
}
