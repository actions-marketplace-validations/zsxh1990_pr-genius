/**
 * pr-genius DSH 插件 — 配置契约 (design principle ①: 无硬编码可调参数).
 *
 * 检验标准：「能否在 cordis.yml 里改这个值而不用改代码？」不能就提成这里的字段。
 * 每个字段都带 `.default(...)`，schema 在加载时校验（design principle ②: 配置错误要响亮）。
 *
 * 分析逻辑只有一份，在 Python 侧 (prgenius/src/prgenius/)。本文件中的阈值只作用于
 * TS 壳层的投影/透传，绝不重写 route_action 等 Python 路由逻辑 —— 注释里标明每个
 * 旋钮由哪一侧消费。
 */
import Schema from 'schemastery'

/** Python 侧维护者 5-action 词表 (prgenius/src/prgenius/maintainer_view.py::MaintainerAction)。 */
/**
 * Schemastery 的 `.default()` 在类型上要求完整对象，但嵌套字段各有自己的
 * `.default(...)`，所以 `{}` 在语义上是合法的「全部走嵌套默认」。这里用一个
 * 断言到 never 把这处类型/语义错位钉住，而不是把默认值抄一遍（抄一遍就会漂移）。
 */
const nestedDefault = {} as never

export const MAINTAINER_ACTIONS = [
  'READY_FOR_REVIEW',
  'WAIT_FOR_AUTHOR',
  'CLOSE_DUPLICATE',
  'CLOSE_STALE_OR_RISKY',
  'HOLD_MAINTAINER_DECISION',
] as const

export type MaintainerAction = (typeof MAINTAINER_ACTIONS)[number]

/** Python 侧贡献者 5-action 词表 (prgenius/src/prgenius/contributor_view.py::ContributorAction)。 */
export const CONTRIBUTOR_ACTIONS = [
  'READY_TO_SUBMIT',
  'FIX_BEFORE_SUBMIT',
  'NEEDS_DISCUSSION',
  'IMPROVE_CHANCE',
  'ASK_MAINTAINER',
] as const

export type ContributorAction = (typeof CONTRIBUTOR_ACTIONS)[number]

/** analyze_pr 返回的三档风险 (prgenius/src/prgenius/evaluator.py)。 */
export const RISK_TIERS = ['low_risk', 'medium_risk', 'high_risk'] as const

export type RiskTier = (typeof RISK_TIERS)[number]

/** 侧边栏落点。消费方：Web UI 插件层（后续里程碑），本里程碑由 describe() 透出。 */
export const SIDEBAR_VIEWS = ['dashboard', 'tab', 'panel'] as const

export type SidebarView = (typeof SIDEBAR_VIEWS)[number]

/** 显示语言。消费方：侧边栏投影层（后续里程碑）。 */
export const LOCALES = ['en', 'zh-CN'] as const

export type Locale = (typeof LOCALES)[number]

export const MCP_TRANSPORTS = ['stdio', 'http'] as const

export type McpTransport = (typeof MCP_TRANSPORTS)[number]

/**
 * 插件配置。类型与 schema 同名导出 (`export const Config`)，别导普通对象。
 * 所有字段都有默认值 —— 空的 cordis.yml 配置即可加载。
 */
export interface Config {
  /**
   * 知识库根路径。TS 直读其中的 anti-patterns/ success-patterns/ profiles/ docs/policies/
   * 静态数据文件；同一路径通过 `--repo-root` 透传给 Python 分析引擎。
   * 空字符串 = 包内知识库（默认）。
   */
  kbRoot: string
  /** 如何连到现有 Python FastMCP 分析服务。分析引擎只有一份，TS 只是壳与投影。 */
  mcp: {
    /** stdio: 拉起 `command + args`（默认 prgenius-core mcp serve）；http: 连 url 指定端点。 */
    transport: McpTransport
    /** stdio 传输的可执行文件。 */
    command: string
    /** stdio 传输的参数。 */
    args: string[]
    /** http 传输的 JSON-RPC 端点（FastMCP streamable-http 或等价实现）。 */
    url: string
    /** 单次 tools/call 超时（毫秒）。超时即拒绝，不带病等待。 */
    timeoutMs: number
    /** MCP initialize 握手声明的 protocolVersion。 */
    protocolVersion: string
  }
  /** 侧边栏默认落点。 */
  sidebar: {
    defaultView: SidebarView
  }
  /** 维护者模式（false = 贡献者模式）。两侧都在首版，用这个开关切换。 */
  maintainer: {
    enabled: boolean
    /**
     * 维护者 5-action 路由结果在侧边栏的展示白名单（TS 投影层过滤）。
     * 5-action 分类本身由 Python `maintainer_view` 工具计算，本插件不重写。
     */
    actions: MaintainerAction[]
    /**
     * 路由结果置信度下限 (0-1)，低于此值的建议不进侧边栏（TS 投影层过滤）。
     */
    confidenceMin: number
    /**
     * 陈旧天数窗口，透传给 Python `status_prs(stale_days=...)`；调用方未显式指定时使用。
     */
    staleDays: number
  }
  /** 侧边栏显示语言。 */
  locale: Locale
  /** 默认风险档位过滤：只展示 tier >= riskFilter 的条目（low_risk = 全部展示）。 */
  riskFilter: RiskTier
}

const DEFAULT_KB_ROOT = ''

/**
 * 配置 schema。非法值在加载时被拒绝，错误信息带字段路径（如 `$.mcp.timeoutMs`）。
 */
export const Config: Schema<any, Config> = Schema.object({
  kbRoot: Schema.string()
    .default(DEFAULT_KB_ROOT)
    .description('知识库根路径，空字符串表示包内知识库'),
  mcp: Schema.object({
    transport: Schema.union([...MCP_TRANSPORTS])
      .default('stdio')
      .description('MCP 传输：stdio 拉起 Python 服务，http 连已有端点'),
    command: Schema.string()
      .default('prgenius-core')
      .description('stdio 传输的可执行文件'),
    args: Schema.array(Schema.string())
      .default(['mcp', 'serve'])
      .description('stdio 传输的参数；kbRoot 非空时插件会追加 --repo-root <kbRoot>'),
    url: Schema.string()
      .default('http://127.0.0.1:8000/mcp')
      .description('http 传输的 JSON-RPC 端点'),
    timeoutMs: Schema.number()
      .min(1)
      .default(30_000)
      .description('单次 tools/call 超时（毫秒）'),
    protocolVersion: Schema.string()
      .default('2025-06-18')
      .description('MCP initialize 握手的 protocolVersion'),
  })
    .default(nestedDefault)
    .description('现有 Python FastMCP 分析服务的连接方式'),
  sidebar: Schema.object({
    defaultView: Schema.union([...SIDEBAR_VIEWS])
      .default('dashboard')
      .description('侧边栏默认落点'),
  })
    .default(nestedDefault)
    .description('侧边栏布局'),
  maintainer: Schema.object({
    enabled: Schema.boolean()
      .default(false)
      .description('维护者模式开关（false = 贡献者模式）'),
    actions: Schema.array(Schema.union([...MAINTAINER_ACTIONS]))
      .default([...MAINTAINER_ACTIONS])
      .description('维护者 5-action 展示白名单'),
    confidenceMin: Schema.number()
      .min(0)
      .max(1)
      .default(0)
      .description('路由结果置信度下限 (0-1)'),
    staleDays: Schema.number()
      .min(1)
      .default(14)
      .description('透传给 status_prs 的陈旧天数窗口'),
  })
    .default(nestedDefault)
    .description('维护者模式'),
  locale: Schema.union([...LOCALES])
    .default('en')
    .description('侧边栏显示语言'),
  riskFilter: Schema.union([...RISK_TIERS])
    .default('low_risk')
    .description('默认风险档位过滤（low_risk = 全部展示）'),
})

/** 配置非法时抛出：信息一眼能看出哪个字段错了。 */
export class PrGeniusConfigError extends Error {
  readonly field: string

  constructor(field: string, message: string, cause?: unknown) {
    super(`pr-genius config invalid at ${field}: ${message}`)
    this.name = 'PrGeniusConfigError'
    this.field = field
    if (cause !== undefined) {
      ;(this as { cause?: unknown }).cause = cause
    }
  }
}

/**
 * 校验并填充默认值。schema 拒绝非法值；错误包装成 PrGeniusConfigError 并点名字段。
 */
export function parseConfig(data: unknown): Config {
  try {
    return Config(data as never)
  } catch (error) {
    const path = (error as { options?: { path?: unknown[] } }).options?.path
    const field = Array.isArray(path) && path.length > 0
      ? path.map(String).join('.')
      : '(top level)'
    const detail = error instanceof Error ? error.message : String(error)
    throw new PrGeniusConfigError(field, detail, error)
  }
}
