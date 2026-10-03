/**
 * 四个界面 + 维护者模式的注册层。
 *
 * 落点依据 DSH SDK 源码 slot-catalog（deepseek-ai/deepseek-harness 的
 * packages/extensions/cordis-client-runner/src/client/slot-catalog.ts，2026-10-03
 * gh api 实抓；注意 deepseek-ai/deepseek-harness-sdk 不存在，404）。快照见
 * docs/slot-catalog-evidence.json（92 个 key，机械抽取）：
 *   - `sidebar.footer.action` — list/root，侧边栏脚部动作区（Dashboard）
 *   - `conversation.view`     — list/session，会话视图标签页（顾问 Tab）
 *   - `sidebar.right.pane.tab`— keyed/session，右栏标签页正文（顾问 Panel，注册带 key）
 *   - `settings.plugins.tab`  — list/root，插件设置页（Preferences）
 *   - `ctx.command`           — 不是 slot key，是 cordis 命令面
 *
 * 注册形态（slot-catalog example 的形状）：
 *   ctx.slots.inject(slot, () => ctx.slots.register({ name: slot, id|key: cell }, Component))
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

/**
 * 落点 = 真实 DSH slot 名（slot-catalog.ts 逐字核对，不是文档、不是参考插件用法）：
 *   sidebar.footer.action    list  / root     —— 侧边栏脚部动作区
 *   conversation.view        list  / session  —— 会话视图标签页，与 Chat/Trajectory 并列
 *   sidebar.right.pane.tab   keyed / session  —— 右栏标签页正文（注册带 key）
 *   settings.plugins.tab     list  / root     —— 插件设置页
 * 早期版本用过两个不存在的键（照教程散文臆造），shipped catalog 里查无此项——已废弃（issue #86/#95）。
 * 「sidebar.right.pane.tab 不存在」的说法同样以 catalog 证伪：它存在，是 keyed；
 * 不存在的是 `details` —— 那是 root doc 里 AppFrame 的内部座位名，不是可注册 key。
 */
export const SETTINGS_SURFACES = {
  plugins: 'settings.plugins.tab',
  pluginInventory: 'settings.plugins.tab',
  sidebar: 'sidebar.footer.action',
  panel: 'sidebar.right.pane.tab',
  tab: 'conversation.view',
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
    slot: SETTINGS_SURFACES.panel,
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
