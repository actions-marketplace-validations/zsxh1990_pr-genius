/**
 * 四个界面 —— 真数据投影（issue #98）。
 *
 * 分工（架构约束）：TS 只是壳与投影。取数走 data.ts → service.callTool →
 * Python FastMCP；本文件不写分析逻辑，只把工具返回的真实字段渲染出来。
 *
 * 组件分两层：
 *   - 纯视图 XxxView(props)：同步渲染，可被 renderToStaticMarkup 验证；
 *   - 薄壳 Xxx(face)：useState/useEffect 取数后交给纯视图。
 * 验证走真实路径：真 MCP 子进程取数 + 真 React 渲染（test/surface-data.test.ts），
 * 不是「文件里写了 251」。
 *
 * 诚实边界：本机无 DEEPSEEK_API_KEY，未在 DSH 宿主里挂载过。渲染语义由
 * renderToStaticMarkup + 真实工具输出验证；宿主挂载形态需 DSH 运行时验证。
 */
import { useCallback, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { PrGeniusService } from '../index.ts'
import { SURFACE_IDS } from '../ui/surfaces.ts'
import {
  PREFERENCES_SLOT,
  ADVISOR_TAB_SLOT,
  ADVISOR_PANEL_SLOT,
  DASHBOARD_SLOT,
} from './slots.ts'
import {
  loadCases,
  loadDashboard,
  loadPatterns,
  runCoach,
  type CaseBrief,
  type CoachVerdict,
  type DashboardData,
  type PatternHit,
} from './data.ts'

/** 宿主注入给组件的最小面 + 本插件 apply() 注入的真实数据源。 */
export interface AdvisorFace {
  readonly service: PrGeniusService
  readonly locale: 'en' | 'zh-CN'
  readonly workMode: 'contributor' | 'maintainer'
  readonly riskFilter: 'low_risk' | 'medium_risk' | 'high_risk'
  /** status_prs 的作者；来自 PRGENIUS_GITHUB_AUTHOR/GH_USER，无则工具自己报缺参。 */
  readonly githubAuthor?: string
}

const T = {
  en: {
    advisorTab: 'Advisor',
    dashboard: 'PR Genius',
    preferences: 'pr-genius · effective config',
    contributor: 'Contributor',
    maintainer: 'Maintainer',
    empty: 'No verdict yet — fill in the PR fields and run the coach.',
    run: 'Run coach',
    running: 'Running…',
    kb: 'Knowledge base',
    anti: 'anti-patterns',
    success: 'success patterns',
    profiles: 'profiles',
    cases: 'case studies',
    policies: 'policies',
    health: 'Install health',
    tools: 'MCP tools',
    gh: 'gh CLI',
    unavailable: 'unavailable',
    inFlight: 'In-flight PRs',
    noAuthor: 'in-flight PRs need an author — set PRGENIUS_GITHUB_AUTHOR',
    warnings: 'Warnings',
    casesSeen: 'Recent case studies (local records)',
    patterns: 'Knowledge base hits',
    verdict: 'Verdict',
    pass: 'PASS',
    fail: 'FAIL',
    mergeProbability: 'merge probability',
    checklist: 'Checklist',
    signalsPos: 'Positive signals',
    signalsNeg: 'Negative signals',
    signalsNeutral: 'Neutral signals',
    coverage: 'rule coverage',
    loaded: 'loaded',
    eligible: 'eligible',
    fired: 'fired',
    title: 'PR title',
    repo: 'repo (org/name)',
    body: 'PR body',
    diffStat: 'diff --stat',
    effective: 'Effective values (from the plugin config)',
    editViaConfig: 'Change these via plugin config — the surface is a readout, not a settings writer.',
  },
  'zh-CN': {
    advisorTab: '顾问',
    dashboard: 'PR Genius',
    preferences: 'pr-genius · 生效配置',
    contributor: '贡献者',
    maintainer: '维护者',
    empty: '尚无结论 —— 填写 PR 字段后运行 coach。',
    run: '运行 coach',
    running: '运行中…',
    kb: '知识库',
    anti: '反模式',
    success: '成功模式',
    profiles: '仓库画像',
    cases: '案例',
    policies: '策略',
    health: '安装自检',
    tools: 'MCP 工具',
    gh: 'gh CLI',
    unavailable: '不可用',
    inFlight: '在飞 PR',
    noAuthor: '在飞 PR 需要 author —— 设置 PRGENIUS_GITHUB_AUTHOR',
    warnings: '警告',
    casesSeen: '最近案例（本地记录）',
    patterns: '知识库命中',
    verdict: '结论',
    pass: '通过',
    fail: '不通过',
    mergeProbability: '合并概率',
    checklist: '检查清单',
    signalsPos: '正向信号',
    signalsNeg: '负向信号',
    signalsNeutral: '中性信号',
    coverage: '规则覆盖',
    loaded: '已加载',
    eligible: '可参与',
    fired: '已命中',
    title: 'PR 标题',
    repo: '仓库 (org/name)',
    body: 'PR 描述',
    diffStat: 'diff --stat',
    effective: '生效值（来自插件配置）',
    editViaConfig: '修改请走插件配置 —— 本界面是只读投影，不写配置。',
  },
} as const

type Dict = { [K in keyof (typeof T)['en']]: string }

function num(n: number | null): string {
  return n === null ? '—' : String(n)
}

// ── Dashboard ─────────────────────────────────────────────────────────────

export interface DashboardViewProps {
  data: DashboardData | null
  loading: boolean
  cases: CaseBrief[]
  locale: AdvisorFace['locale']
}

/** Dashboard 纯视图：知识库规模 + 自检 + 在飞 PR。数字全部来自 doctor/status_prs。 */
export function DashboardView({ data, loading, cases, locale }: DashboardViewProps) {
  const t: Dict = T[locale]
  const doctor = data?.doctor ?? null
  return (
    <section data-slot={DASHBOARD_SLOT} data-surface="dashboard">
      <h2>{t.dashboard}</h2>
      {loading && doctor === null && data?.doctorError === null ? <p>…</p> : null}
      {data?.doctorError !== null && data?.doctorError !== undefined ? (
        <p data-field="doctor-error">{data.doctorError}</p>
      ) : null}
      {doctor !== null ? (
        <div>
          <h3>{t.kb}</h3>
          <ul data-field="kb-scale">
            <li data-kb="anti-patterns">
              {doctor.kb.antiPatterns} {t.anti}
            </li>
            <li data-kb="success-patterns">
              {doctor.kb.successPatterns} {t.success}
            </li>
            <li data-kb="profiles">
              {doctor.kb.profiles} {t.profiles}
            </li>
            <li data-kb="case-studies">
              {doctor.kb.caseStudies} {t.cases}
            </li>
            <li data-kb="policies">
              {doctor.kb.policies} {t.policies}
            </li>
          </ul>
          <h3>{t.health}</h3>
          <ul data-field="health">
            <li data-health="version">prgenius {doctor.prgeniusVersion}</li>
            <li data-health="mcp">
              {t.tools}: {doctor.mcpToolsRegistered} ({doctor.mcpOk ? 'ok' : t.unavailable})
            </li>
            <li data-health="gh">
              {t.gh}: {doctor.ghAvailable ? doctor.ghVersion || 'ok' : t.unavailable}
            </li>
          </ul>
          {doctor.warnings.length > 0 ? (
            <ul data-field="warnings">
              {doctor.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      <h3>{t.inFlight}</h3>
      {data?.status !== null && data?.status !== undefined ? (
        <div data-field="in-flight">
          <ul data-field="status-summary">
            {Object.entries(data.status.summary).map(([key, count]) => (
              <li key={key} data-status={key}>
                {key}: {count}
              </li>
            ))}
          </ul>
          <ul data-field="pr-table">
            {data.status.prs.map((pr) => (
              <li key={`${pr.repo}#${pr.number}`} data-pr-status={pr.status}>
                <span data-pr="id">
                  {pr.repo}#{pr.number}
                </span>{' '}
                <span data-pr="status">{pr.status}</span>{' '}
                <span data-pr="days">d{num(pr.daysSinceUpdate)}</span>{' '}
                <span data-pr="action">{pr.suggestedAction}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p data-field="status-error">{data?.statusError ?? t.noAuthor}</p>
      )}
      {cases.length > 0 ? (
        <div data-field="cases">
          <h3>{t.casesSeen}</h3>
          <ul>
            {cases.map((c) => (
              <li key={`${c.repo}#${c.prNumber}`}>
                {c.repo}#{c.prNumber}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

/** Dashboard 壳：挂载即取数（doctor + status_prs + list_open_prs）。 */
export function Dashboard(face: AdvisorFace) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [cases, setCases] = useState<CaseBrief[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let alive = true
    void (async () => {
      const [dashboard, caseResult] = await Promise.all([
        loadDashboard(face.service, { author: face.githubAuthor }),
        loadCases(face.service, 5),
      ])
      if (!alive) return
      setData(dashboard)
      if (caseResult.ok) setCases(caseResult.data)
      setLoading(false)
    })()
    return () => {
      alive = false
    }
  }, [face.service, face.githubAuthor])
  return <DashboardView data={data} loading={loading} cases={cases} locale={face.locale} />
}

// ── Advisor（会话 Tab 与右栏 Panel 共用） ─────────────────────────────────

export interface AdvisorViewProps {
  verdict: CoachVerdict | null
  patterns: PatternHit[]
  error: string | null
  running: boolean
  locale: AdvisorFace['locale']
  workMode: AdvisorFace['workMode']
  onRun?: (input: { title: string; repo: string; body: string; diffStat: string }) => void
}

/** 顾问纯视图：coach_pr 结论 + 知识库命中。无结论时是表单，不是假占位文案。 */
export function AdvisorView({
  verdict,
  patterns,
  error,
  running,
  locale,
  workMode,
  onRun,
}: AdvisorViewProps) {
  const t: Dict = T[locale]
  return (
    <section data-slot={ADVISOR_TAB_SLOT} data-mode={workMode}>
      <h2>{workMode === 'maintainer' ? t.maintainer : t.advisorTab}</h2>
      {verdict === null ? (
        <form
          data-field="coach-form"
          onSubmit={(event) => {
            event.preventDefault()
            const form = event.currentTarget
            const read = (name: string) =>
              (form.elements.namedItem(name) as HTMLInputElement | HTMLTextAreaElement | null)
                ?.value ?? ''
            onRun?.({
              title: read('title'),
              repo: read('repo'),
              body: read('body'),
              diffStat: read('diffStat'),
            })
          }}
        >
          <label>
            {t.title}
            <input name="title" type="text" />
          </label>
          <label>
            {t.repo}
            <input name="repo" type="text" />
          </label>
          <label>
            {t.body}
            <textarea name="body" />
          </label>
          <label>
            {t.diffStat}
            <textarea name="diffStat" />
          </label>
          <button type="submit" disabled={running}>
            {running ? t.running : t.run}
          </button>
          {error !== null ? <p data-field="coach-error">{error}</p> : null}
          {error === null && !running ? <p data-field="empty">{t.empty}</p> : null}
        </form>
      ) : (
        <div data-field="verdict">
          <p data-field="verdict-line">
            <strong data-verdict="pass">{verdict.pass ? t.pass : t.fail}</strong>{' '}
            <span data-verdict="tier">{verdict.tier}</span>{' '}
            <span data-verdict="merge-probability">
              {t.mergeProbability} {num(verdict.mergeProbability)}
            </span>
          </p>
          {verdict.summary !== '' ? <p data-verdict="summary">{verdict.summary}</p> : null}
          <h3>{t.signalsPos}</h3>
          <ul data-field="signals-positive">
            {verdict.signals.positive.map((s) => (
              <li key={s.key}>{s.description}</li>
            ))}
          </ul>
          {verdict.signals.negative.length > 0 ? (
            <>
              <h3>{t.signalsNeg}</h3>
              <ul data-field="signals-negative">
                {verdict.signals.negative.map((s) => (
                  <li key={s.key}>{s.description}</li>
                ))}
              </ul>
            </>
          ) : null}
          {verdict.signals.neutral.length > 0 ? (
            <>
              <h3>{t.signalsNeutral}</h3>
              <ul data-field="signals-neutral">
                {verdict.signals.neutral.map((s) => (
                  <li key={s.key}>{s.description}</li>
                ))}
              </ul>
            </>
          ) : null}
          <h3>{t.checklist}</h3>
          <ul data-field="checklist">
            {verdict.checklist.map((item) => (
              <li key={item.action} data-done={String(item.done)}>
                [{item.priority}] {item.action} — {item.hint}
              </li>
            ))}
          </ul>
          <p data-field="coverage">
            {t.coverage}: {verdict.coverage.antiPatternsFired}/{verdict.coverage.antiPatternsEligible}{' '}
            ({t.loaded} {verdict.coverage.antiPatternsLoaded})
          </p>
          {error !== null ? <p data-field="coach-error">{error}</p> : null}
        </div>
      )}
      {patterns.length > 0 ? (
        <div data-field="patterns">
          <h3>{t.patterns}</h3>
          <ul>
            {patterns.map((p) => (
              <li key={`${p.type}:${p.file}:${p.key}`}>
                <span data-pattern="type">{p.type}</span> {p.title || p.key}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

/** 顾问壳：表单提交 → coach_pr；顺带 search_patterns 标题关键词。 */
export function Advisor(face: AdvisorFace) {
  const [verdict, setVerdict] = useState<CoachVerdict | null>(null)
  const [patterns, setPatterns] = useState<PatternHit[]>([])
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const onRun = useCallback(
    (input: { title: string; repo: string; body: string; diffStat: string }) => {
      setRunning(true)
      setError(null)
      void (async () => {
        const result = await runCoach(face.service, {
          title: input.title,
          repo: input.repo,
          body: input.body,
          diffStat: input.diffStat,
        })
        if (result.ok) {
          setVerdict(result.data)
          const hits = await loadPatterns(face.service, input.title || input.repo, 5)
          if (hits.ok) setPatterns(hits.data)
        } else {
          setError(result.error)
        }
        setRunning(false)
      })()
    },
    [face.service],
  )
  return (
    <AdvisorView
      verdict={verdict}
      patterns={patterns}
      error={error}
      running={running}
      locale={face.locale}
      workMode={face.workMode}
      onRun={onRun}
    />
  )
}

/** 右栏投影 —— 与 Advisor 同一套数据与逻辑，只是挂在另一个 slot。 */
export function AdvisorPanel(face: AdvisorFace) {
  return (
    <div data-slot={ADVISOR_PANEL_SLOT} data-surface="advisor-panel">
      <Advisor {...face} />
    </div>
  )
}

// ── Preferences：生效配置只读投影 ─────────────────────────────────────────

export interface PreferencesViewProps {
  face: AdvisorFace
}

/**
 * 偏好卡：service.describe() 的生效值原样展示。
 * 刻意不做假表单 —— 当前服务层没有持久化写口（无 applyPatch），
 * 画一个存不回去的「Save」比只读投影更糟。
 */
export function PreferencesView({ face }: PreferencesViewProps) {
  const t: Dict = T[face.locale]
  const info = face.service.describe()
  const rows: Array<[string, string]> = [
    ['kbRoot', info.kbRoot],
    ['mcp.transport', info.mcp.transport],
    ['mcp.endpoint', info.mcp.endpoint],
    ['mcp.timeoutMs', String(info.mcp.timeoutMs)],
    ['mcp.protocolVersion', info.mcp.protocolVersion],
    ['sidebar.defaultView', info.sidebar.defaultView],
    ['maintainer.enabled', String(info.maintainer.enabled)],
    ['maintainer.actions', info.maintainer.actions.join(', ')],
    ['maintainer.confidenceMin', String(info.maintainer.confidenceMin)],
    ['maintainer.staleDays', String(info.maintainer.staleDays)],
    ['locale', info.locale],
    ['riskFilter', info.riskFilter],
  ]
  return (
    <section data-slot={PREFERENCES_SLOT} data-surface="preferences">
      <h2>{t.preferences}</h2>
      <p data-field="config-note">{t.editViaConfig}</p>
      <h3>{t.effective}</h3>
      <dl data-field="effective-config">
        {rows.map(([key, value]) => (
          <div key={key} data-config={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export function Preferences(face: AdvisorFace) {
  return <PreferencesView face={face} />
}

// ── 注册层用的组件表 ─────────────────────────────────────────────────────

export type SurfaceComponent = (hostProps?: unknown) => ReactNode

/**
 * 组件工厂：把 apply() 里的真 service 与配置投影闭包进组件。
 * 宿主传下来的 slot props 不会带我们的 service —— 不注入的话组件永远拿不到数据
 * （issue #98 的「每个组件都忽略 service」多半根因在此）。
 */
export function surfaceComponents(face: AdvisorFace): Record<string, SurfaceComponent> {
  return {
    [SURFACE_IDS.dashboard]: () => <Dashboard {...face} />,
    [SURFACE_IDS.advisorTab]: () => <Advisor {...face} />,
    [SURFACE_IDS.advisorPanel]: () => <AdvisorPanel {...face} />,
    [SURFACE_IDS.preferences]: () => <Preferences {...face} />,
  }
}
