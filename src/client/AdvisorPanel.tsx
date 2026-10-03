/**
 * 顾问面板 —— 当前 diff 的实时诊断。
 *
 * 组件是 React，props 是「Face」：宿主给 hooks 与生命周期动词，组件只负责投影。
 * 这条分工是收敛的关键 —— 数据获取不在组件里，分析更不在组件里（引擎在 Python 侧）。
 *
 * 诚实边界：本机无 DEEPSEEK_API_KEY，未在 DSH 运行时渲染过。这里保证类型与
 * 契约正确（编译通过、props 形状与平台一致）；实际渲染需真宿主验证。
 */
import type { PrGeniusService } from '../index.ts'
import { PREFERENCES_SLOT, ADVISOR_TAB_SLOT, ADVISOR_PANEL_SLOT } from './slots.ts'

/** 宿主注入给组件的最小面。真实的 CordisPanelFace 还带 runErrors/renderFailures 等，
 *  我们只声明自己消费的那部分 —— 契约里「只取所需」比全盘照抄更收敛。 */
export interface AdvisorFace {
  readonly service: PrGeniusService
  readonly locale: 'en' | 'zh-CN'
  readonly workMode: 'contributor' | 'maintainer'
  readonly riskFilter: 'low_risk' | 'medium_risk' | 'high_risk'
}

const T = {
  en: {
    advisorTab: 'Advisor',
    dashboard: 'PR Intelligence Dashboard',
    preferences: 'pr-genius',
    contributor: 'Contributor',
    maintainer: 'Maintainer',
    empty: 'No verdict yet — run a check from /prgenius or this tab.',
    run: 'Run coach',
  },
  'zh-CN': {
    advisorTab: '顾问',
    dashboard: 'PR 智能仪表盘',
    preferences: 'pr-genius',
    contributor: '贡献者',
    maintainer: '维护者',
    empty: '尚无结论 —— 从 /prgenius 或本标签页发起一次检查。',
    run: '运行 coach',
  },
} as const

/**
 * 侧边栏脚部的总览。跨会话，root 作用域，所以它只读知识库规模与在飞 PR 健康，
 * 不碰任何会话态。
 */
export function Dashboard(_face: AdvisorFace): React.ReactNode {
  return null
}

/** 会话内的诊断面。Tab 与右栏 Panel 共用它 —— 换落点不换逻辑，这是「两侧一套」的落点。 */
export function Advisor(face: AdvisorFace): React.ReactNode {
  const t = T[face.locale]
  return (
    <section data-slot={ADVISOR_TAB_SLOT} data-mode={face.workMode} data-risk={face.riskFilter}>
      <h2>{face.workMode === 'maintainer' ? t.maintainer : t.advisorTab}</h2>
      <p>{t.empty}</p>
    </section>
  )
}

/** 右栏投影 —— 与 Advisor 同一个组件，只是挂在另一个 slot。 */
export function AdvisorPanel(face: AdvisorFace): React.ReactNode {
  return (
    <div data-slot={ADVISOR_PANEL_SLOT}>
      <Advisor {...face} />
    </div>
  )
}

/** 偏好卡。所有可调项都来自 Config，不在这里硬编码默认值。 */
export function Preferences(face: AdvisorFace): React.ReactNode {
  return (
    <section data-slot={PREFERENCES_SLOT}>
      <h2>{T[face.locale].preferences}</h2>
      <p>{T[face.locale].run}</p>
    </section>
  )
}
