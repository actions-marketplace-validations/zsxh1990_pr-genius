/**
 * 界面数据层 —— 四个界面的取数口，全部走 service.callTool 透传 Python FastMCP。
 *
 * 铁律（issue #98）：渲染的每个数字都必须来自真实工具输出或真实配置值，绝不编造。
 * 本文件不产生数据，只搬运与校验：字段缺失/形状不符 → ok:false，界面显示错误态，
 * 而不是补一个 0 或占位数。分析逻辑只有一份，在 Python 侧。
 *
 * 真实工具名（以 prgenius/src/prgenius/mcp.py 为准，不是文档里的别名）：
 *   prgenius_doctor / coach_pr / status_prs / search_patterns / list_open_prs
 *
 * FastMCP tools/call 的真实返回信封（本机实测）：
 *   { content: [{ type: 'text', text: '<工具返回值的 JSON 文本>' }], isError: false }
 * 没有 structuredContent —— 所以这里显式解信封，不假设工具 dict 直接可读。
 */
import type { PrGeniusService } from '../index.ts'

export type ToolResult<T> = { ok: true; data: T } | { ok: false; error: string }

function fail<T>(error: string): ToolResult<T> {
  return { ok: false, error }
}

/**
 * 解 tools/call 信封。真实形态（本机实测 FastMCP）：
 *   1. dict 返回 → { content: [{ type:'text', text: '<json object>' }], isError }
 *   2. list 返回 → content[] 一项一个元素（每项 text 是一个 JSON 对象）——
 *      所以多项 content 要逐项 JSON.parse 成数组，只取第一项会把列表砍成单条
 *      （实测 list_open_prs：11 条记录 = 11 个 content 项）。
 *   3. structuredContent 直出（若宿主/服务端提供）
 *   4. 裸对象（测试假服务端）
 * 解不出工具值时报错 —— 界面拿不到数据就显示拿不到，不猜字段。
 */
export function unwrapToolPayload(result: unknown): unknown {
  if (result === null || result === undefined) return result
  if (typeof result !== 'object') return result
  const envelope = result as {
    content?: Array<{ type?: string; text?: string }>
    structuredContent?: unknown
    isError?: boolean
  }
  if (Array.isArray(envelope.content) && envelope.content.length > 0) {
    if (envelope.isError === true) {
      throw new Error(envelope.content[0]?.text ?? 'tools/call returned isError')
    }
    const parsed = envelope.content.map((item) => {
      if (item?.type !== 'text' || typeof item.text !== 'string') {
        throw new Error('tools/call content item is not text')
      }
      try {
        return JSON.parse(item.text)
      } catch (cause) {
        throw new Error(`tools/call text payload is not JSON: ${item.text.slice(0, 120)}`, { cause })
      }
    })
    return parsed.length === 1 ? parsed[0] : parsed
  }
  if (envelope.structuredContent !== undefined) return envelope.structuredContent
  return result
}

async function callToolPayload(
  service: PrGeniusService,
  tool: string,
  args: Record<string, unknown>,
): Promise<unknown> {
  return unwrapToolPayload(await service.callTool(tool, args))
}

function str(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function num(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function strList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : []
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

// ── Dashboard：知识库规模 + 安装自检（prgenius_doctor）+ 在飞 PR（status_prs） ──

/** 知识库规模 —— 数字全部来自 doctor 的 knowledge_base 字段，与 CLI `prgenius doctor` 同源。 */
export interface KbScale {
  antiPatterns: number
  antiPatternsTriggerKeywords: number
  successPatterns: number
  profiles: number
  caseStudies: number
  policies: number
}

export interface DoctorReport {
  ok: boolean
  prgeniusVersion: string
  pythonVersion: string
  platform: string
  kb: KbScale
  ghAvailable: boolean
  ghVersion: string
  mcpToolsRegistered: number
  mcpOk: boolean
  warnings: string[]
}

/** 在飞 PR 行 —— 字段来自 status_prs 的 prs[]，不补全、不美化。 */
export interface InFlightPr {
  repo: string
  number: number
  title: string
  status: string
  severity: string
  daysSinceUpdate: number | null
  suggestedAction: string
  url: string
}

export interface StatusReport {
  author: string
  repo: string
  checkedAt: string
  staleDays: number | null
  /** 状态 → 条数，键名原样取自工具的 summary（NEEDS_REBASE / CLEAN / ...）。 */
  summary: Record<string, number>
  prs: InFlightPr[]
  actions: string[]
}

export interface DashboardData {
  doctor: DoctorReport | null
  doctorError: string | null
  status: StatusReport | null
  statusError: string | null
}

/**
 * Dashboard 取数：doctor（必答）+ status_prs（有 author/repo 才问）。
 * 两者独立失败 —— 一个挂了另一个照常显示。
 */
export async function loadDashboard(
  service: PrGeniusService,
  opts: { author?: string; repo?: string } = {},
): Promise<DashboardData> {
  const [doctor, status] = await Promise.all([
    loadDoctor(service),
    opts.author || opts.repo
      ? loadStatus(service, { author: opts.author, repo: opts.repo })
      : Promise.resolve(
          fail<StatusReport>('in-flight PRs need an author — set PRGENIUS_GITHUB_AUTHOR (or pass repo)'),
        ),
  ])
  return {
    doctor: doctor.ok ? doctor.data : null,
    doctorError: doctor.ok ? null : doctor.error,
    status: status.ok ? status.data : null,
    statusError: status.ok ? null : status.error,
  }
}

/** prgenius_doctor —— 与 `prgenius doctor --format json` 同一实现（doctor.run_doctor）。 */
export async function loadDoctor(service: PrGeniusService): Promise<ToolResult<DoctorReport>> {
  let payload: unknown
  try {
    payload = await callToolPayload(service, 'prgenius_doctor', {})
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error))
  }
  if (!isRecord(payload)) return fail('prgenius_doctor returned a non-object payload')
  const kbRaw = payload.knowledge_base
  if (!isRecord(kbRaw)) return fail('prgenius_doctor payload missing knowledge_base')
  const needed: Array<keyof KbScale> = [
    'antiPatterns',
    'successPatterns',
    'profiles',
    'caseStudies',
    'policies',
  ]
  const kb: KbScale = {
    antiPatterns: num(kbRaw.anti_patterns) ?? -1,
    antiPatternsTriggerKeywords: num(kbRaw.anti_patterns_with_trigger_keywords) ?? -1,
    successPatterns: num(kbRaw.success_patterns) ?? -1,
    profiles: num(kbRaw.profiles) ?? -1,
    caseStudies: num(kbRaw.case_studies) ?? -1,
    policies: num(kbRaw.policies) ?? -1,
  }
  for (const field of needed) {
    if (kb[field] < 0) return fail(`prgenius_doctor knowledge_base.${field} missing`)
  }
  const gh = isRecord(payload.gh) ? payload.gh : {}
  const mcp = isRecord(payload.mcp) ? payload.mcp : {}
  return {
    ok: true,
    data: {
      ok: payload.ok === true,
      prgeniusVersion: str(payload.prgenius_version),
      pythonVersion: str(payload.python_version),
      platform: str(payload.platform),
      kb,
      ghAvailable: gh.available === true,
      ghVersion: str(gh.version),
      mcpToolsRegistered: num(mcp.tools_registered) ?? 0,
      mcpOk: mcp.ok === true,
      warnings: strList(payload.warnings),
    },
  }
}

/** status_prs —— 在飞 PR 健康。需要 author 或 repo，否则工具自己报错（原样透出）。 */
export async function loadStatus(
  service: PrGeniusService,
  opts: { author?: string; repo?: string; staleDays?: number },
): Promise<ToolResult<StatusReport>> {
  const args: Record<string, unknown> = {}
  if (opts.author) args.author = opts.author
  if (opts.repo) args.repo = opts.repo
  if (opts.staleDays !== undefined) args.stale_days = opts.staleDays
  let payload: unknown
  try {
    payload = await callToolPayload(service, 'status_prs', args)
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error))
  }
  if (!isRecord(payload)) return fail('status_prs returned a non-object payload')
  if (typeof payload.error === 'string') return fail(payload.error)
  const prsRaw = Array.isArray(payload.prs) ? payload.prs : null
  if (prsRaw === null) return fail('status_prs payload missing prs[]')
  const summary: Record<string, number> = {}
  if (isRecord(payload.summary)) {
    for (const [key, value] of Object.entries(payload.summary)) {
      const n = num(value)
      if (n !== null) summary[key] = n
    }
  }
  return {
    ok: true,
    data: {
      author: str(payload.author),
      repo: str(payload.repo),
      checkedAt: str(payload.checked_at),
      staleDays: num(payload.stale_days),
      summary,
      prs: prsRaw.filter(isRecord).map((p) => ({
        repo: str(p.repo),
        number: num(p.number) ?? 0,
        title: str(p.title),
        status: str(p.status),
        severity: str(p.severity),
        daysSinceUpdate: num(p.days_since_update),
        suggestedAction: str(p.suggested_action),
        url: str(p.url),
      })),
      actions: strList(payload.actions),
    },
  }
}

// ── Advisor：coach_pr 结论 + search_patterns 命中 ──

export interface CoachInput {
  title: string
  repo: string
  body?: string
  description?: string
  author?: string
  labels?: string[]
  diffStat?: string
}

export interface Signal {
  key: string
  description: string
}

export interface ChecklistItem {
  action: string
  priority: string
  done: boolean
  hint: string
}

export interface CoachVerdict {
  pass: boolean
  tier: string
  riskDescription: string
  summary: string
  mergeProbability: number | null
  mergeProbabilityBasis: string
  signals: { positive: Signal[]; negative: Signal[]; neutral: Signal[] }
  checklist: ChecklistItem[]
  coverage: {
    antiPatternsLoaded: number
    antiPatternsEligible: number
    antiPatternsFired: number
  }
}

/** coach_pr —— Agent PR Dojo 的 pass/fail 门。tier/signals/checklist 全部原样投影。 */
export async function runCoach(
  service: PrGeniusService,
  input: CoachInput,
): Promise<ToolResult<CoachVerdict>> {
  const args: Record<string, unknown> = {
    title: input.title,
    repo: input.repo,
  }
  if (input.body) args.body = input.body
  if (input.description) args.description = input.description
  if (input.author) args.author = input.author
  if (input.labels && input.labels.length > 0) args.labels = input.labels
  if (input.diffStat) args.diff_stat = input.diffStat
  let payload: unknown
  try {
    payload = await callToolPayload(service, 'coach_pr', args)
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error))
  }
  if (!isRecord(payload)) return fail('coach_pr returned a non-object payload')
  if (typeof payload.error === 'string') return fail(payload.error)
  const tier = str(payload.tier)
  if (tier === '') return fail('coach_pr payload missing tier')
  const parseSignals = (value: unknown): Signal[] =>
    Array.isArray(value)
      ? value.filter(isRecord).map((s) => ({ key: str(s.key), description: str(s.description) }))
      : []
  const signalsRaw = isRecord(payload.signals) ? payload.signals : {}
  const checklistRaw = Array.isArray(payload.checklist) ? payload.checklist : []
  const coverageRaw = isRecord(payload.coverage) ? payload.coverage : {}
  return {
    ok: true,
    data: {
      pass: payload.pass === true,
      tier,
      riskDescription: str(payload.risk_description),
      summary: str(payload.summary),
      mergeProbability: num(payload.merge_probability),
      mergeProbabilityBasis: str(payload.merge_probability_basis),
      signals: {
        positive: parseSignals(signalsRaw.positive),
        negative: parseSignals(signalsRaw.negative),
        neutral: parseSignals(signalsRaw.neutral),
      },
      checklist: checklistRaw.filter(isRecord).map((c) => ({
        action: str(c.action),
        priority: str(c.priority),
        done: c.done === true,
        hint: str(c.hint),
      })),
      coverage: {
        antiPatternsLoaded: num(coverageRaw.anti_patterns_loaded) ?? -1,
        antiPatternsEligible: num(coverageRaw.anti_patterns_eligible) ?? -1,
        antiPatternsFired: num(coverageRaw.anti_patterns_fired) ?? -1,
      },
    },
  }
}

export interface PatternHit {
  key: string
  title: string
  type: string
  file: string
  symptom: string
  fixAction: string
}

/** search_patterns —— 知识库命中。query 来自用户输入或 PR 标题，不内置假关键词。 */
export async function loadPatterns(
  service: PrGeniusService,
  query: string,
  limit = 5,
): Promise<ToolResult<PatternHit[]>> {
  let payload: unknown
  try {
    payload = await callToolPayload(service, 'search_patterns', {
      query,
      pattern_type: 'all',
      limit,
    })
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error))
  }
  if (!Array.isArray(payload)) return fail('search_patterns returned a non-list payload')
  return {
    ok: true,
    data: payload.filter(isRecord).map((p) => ({
      key: str(p.key),
      title: str(p.title),
      type: str(p.type),
      file: str(p.file),
      symptom: str(p.symptom),
      fixAction: str(p.fix_action),
    })),
  }
}

export interface CaseBrief {
  repo: string
  prNumber: number
  author: string
  folder: string
}

/** list_open_prs —— 本地 case-study 记录（工具文档明说不是 GitHub 实时 PR）。 */
export async function loadCases(
  service: PrGeniusService,
  limit = 5,
): Promise<ToolResult<CaseBrief[]>> {
  let payload: unknown
  try {
    payload = await callToolPayload(service, 'list_open_prs', {})
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error))
  }
  if (!Array.isArray(payload)) return fail('list_open_prs returned a non-list payload')
  return {
    ok: true,
    data: payload
      .filter(isRecord)
      .slice(0, limit)
      .map((c) => ({
        repo: str(c.repo),
        prNumber: num(c.pr_number) ?? 0,
        author: str(c.author),
        folder: str(c.folder),
      })),
  }
}
