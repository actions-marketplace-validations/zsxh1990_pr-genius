/**
 * pr-genius — DSH (Cordis) 插件本体。
 *
 * 契约（dsh plugin add pr-genius 后由 ctx.use 实例化为带生命周期的 fiber）：
 *   - name / Config(schema) / inject / apply
 *   - 加载即生效、卸载即还原：apply() 里注册的都是 effect，框架卸载时自动清理。
 *
 * 架构：TS 只是壳与投影 —— 直读知识库静态数据文件，分析一律调用现有 Python
 * FastMCP 服务 (prgenius/src/prgenius/mcp.py)。绝不重写分析逻辑。
 *
 * 诚实边界：本机没有 DEEPSEEK_API_KEY，未跑真 DSH。本文件只保证 TypeScript
 * 编译、单元测试与静态契约自洽；渲染与运行时行为需 DSH 运行时验证，本机未执行。
 */
import type { Context } from 'cordis'
import { planRegistrations, SURFACE_IDS } from './ui/surfaces.ts'
import {
  Config,
  PrGeniusConfigError,
  parseConfig,
  type ContributorAction,
  type MaintainerAction,
  type RiskTier,
} from './config.ts'
import { defaultKbRoot, readPackageMeta, resolveKbRoot, type KbLayout } from './kb.ts'
import { createMcpInvoker, type McpInvoker } from './mcp-client.ts'

export const name = 'pr-genius'

export { Config, PrGeniusConfigError, parseConfig }
export type { Config as ConfigType, ContributorAction, MaintainerAction, RiskTier }

/** 无外部服务依赖；logger/effect 由 Context 自带，不需要 inject。 */
// `inject` = 我需要什么（契约三件套之一）。本插件不**依赖**任何宿主服务：分析走
// 自带的 MCP 客户端、知识库是静态文件。命令面与 UI slot 面是**可选贡献**，不是依赖。
//
// 这里刻意不把 `command` / `slots` 写进 inject：Cordis 的 ReflectService 在属性
// 不在 target 上时会直接抛 `cannot get property "X" without inject`，而把它们写成
// 必填注入又会让没有 web 宿主的环境加载失败 —— 把「界面缺失」升级成「插件不可用」。
// 所以 inject 为空，取用时用 Reflect.has 探测（见 apply()）。
export const inject: string[] = []

/** 本插件向宿主提供的服务名，其他插件/UI 可通过 inject: ['prGenius'] 使用。 */
export const provide = 'prGenius'

/** 描述插件运行时形态 —— 供 UI 投影与诊断读取。 */
export interface PrGeniusRuntimeInfo {
  name: string
  version: string
  kbRoot: string
  mcp: {
    transport: string
    /** stdio 时为 `${command} ${args.join(' ')}`，http 时为 url。 */
    endpoint: string
    timeoutMs: number
    protocolVersion: string
  }
  sidebar: { defaultView: string }
  maintainer: {
    enabled: boolean
    actions: MaintainerAction[]
    confidenceMin: number
    staleDays: number
  }
  locale: string
  riskFilter: RiskTier
}

/** 插件服务：配置投影 + 通往 Python 分析引擎的调用口。 */
export interface PrGeniusService {
  readonly config: ReturnType<typeof parseConfig>
  readonly kb: KbLayout
  /** 运行时形态描述（纯函数，无副作用）。 */
  describe(): PrGeniusRuntimeInfo
  /**
   * 调用 Python FastMCP 工具（analyze_pr / coach_pr / maintainer_view / ...）。
   * 工具名与参数原样透传 prgenius/src/prgenius/mcp.py，TS 不做任何再加工。
   */
  callTool(tool: string, args?: Record<string, unknown>): Promise<unknown>
  /** 释放传输层。由插件卸载自动调用；也可显式调用，幂等。 */
  close(): Promise<void>
}

export interface PrGeniusServiceDeps {
  config: ReturnType<typeof parseConfig>
  kb: KbLayout
  version: string
  invoker: McpInvoker
}

export function createPrGeniusService(deps: PrGeniusServiceDeps): PrGeniusService {
  const { config, kb, version, invoker } = deps
  return {
    config,
    kb,
    describe(): PrGeniusRuntimeInfo {
      return {
        name,
        version,
        kbRoot: kb.root,
        mcp: {
          transport: config.mcp.transport,
          endpoint:
            config.mcp.transport === 'http'
              ? config.mcp.url
              : [config.mcp.command, ...config.mcp.args].join(' '),
          timeoutMs: config.mcp.timeoutMs,
          protocolVersion: config.mcp.protocolVersion,
        },
        sidebar: { defaultView: config.sidebar.defaultView },
        maintainer: {
          enabled: config.maintainer.enabled,
          actions: [...config.maintainer.actions],
          confidenceMin: config.maintainer.confidenceMin,
          staleDays: config.maintainer.staleDays,
        },
        locale: config.locale,
        riskFilter: config.riskFilter,
      }
    },
    callTool(tool: string, args: Record<string, unknown> = {}) {
      return invoker.callTool(tool, args)
    },
    close() {
      return invoker.close()
    },
  }
}

/**
 * 插件入口：注册服务 + 挂好清理。返回 void，卸载时由 fiber 自动还原。
 *
 * 配置非法 → 抛 PrGeniusConfigError（字段路径见 message），加载即失败，不带病运行。
 * kbRoot 布局缺失 → 同样抛错，响亮失败。
 */
export function apply(ctx: Context, config: Config): void {
  // 防御性再校验：框架已按 schema 校验过，这里保证直接调用 apply() 时同样响亮。
  const resolved = parseConfig(config)
  const logger = ctx.logger('pr-genius')
  const kb = resolveKbRoot(resolved.kbRoot)
  const meta = readPackageMeta(defaultKbRoot())
  const invoker = createMcpInvoker(
    {
      transport: resolved.mcp.transport,
      command: resolved.mcp.command,
      args: resolved.mcp.args,
      url: resolved.mcp.url,
      timeoutMs: resolved.mcp.timeoutMs,
      protocolVersion: resolved.mcp.protocolVersion,
      clientName: name,
      clientVersion: meta.version,
    },
    (line) => logger.warn('[mcp:stderr] %s', line),
  )
  const service = createPrGeniusService({
    config: resolved,
    kb,
    version: meta.version,
    invoker,
  })

  // provide 返回的 disposable 会随 fiber 卸载自动撤销服务注册。
  const disposeService = ctx.provide('prGenius', service)

  // ── 四个界面 ──────────────────────────────────────────────────────────
  // 落点来自 docs/dsh-ui-slot-api.md 的权威 slot 表，四个界面的 slot 归属收敛在
  // SURFACE_PLAN 一处，可被测试断言（assertSlotPlacement），不靠渲染验证。
  //
  // 命令面走 ctx.command（教程明文 API）。UI slot 面走能力探测：ui-slots 的
  // 组件形态与 renderer 约定属于运行时契约，本机无 DEEPSEEK_API_KEY 跑不起 DSH，
  // 所以这里只在宿主真的提供 slots 服务时才注册，并把组件实现留给 UI 层注入。
  // 宁可少注册一个面，也不假称「已渲染」。
  const surfaceDisposers: Array<() => void> = []

  // Reflect.has 而不是 `typeof ctx.command === 'function'`：直接读不存在的属性会被
  // Cordis 的 ReflectService 拦截并抛错，探测也走不到。
  const commandCtx = ctx as unknown as {
    command?: (name: string) => {
      action?: (fn: () => unknown) => unknown
      option?: unknown
    }
  }
  if (Reflect.has(commandCtx, 'command') && typeof commandCtx.command === 'function') {
    const cmd = commandCtx.command(SURFACE_IDS.command)
    cmd.action?.(() => {
      // 快查弹窗：不离开聊天就得到「能不能提 PR」的结论 + 阻塞项。
      // 分析逻辑在 Python 侧（coach_pr），TS 只透传 —— 见架构约束注释。
      void service
        .callTool('coach_pr', { title: '', body: '', repo: '' })
        .then(
          (verdict: unknown) =>
            logger.info('[%s] %s', SURFACE_IDS.command, JSON.stringify(verdict).slice(0, 400)),
          (err: unknown) => logger.error('[%s] failed: %s', SURFACE_IDS.command, String(err)),
        )
    })
    surfaceDisposers.push(() => logger.info('command %s unregistered', SURFACE_IDS.command))
    logger.info('surface ready: %s (slash command)', SURFACE_IDS.command)
  } else {
    logger.warn('ctx.command unavailable — slash surface not registered')
  }

  const slotsCtx = ctx as unknown as {
    slots?: {
      inject?: (slot: string, factory: () => unknown) => () => void
      register?: (def: unknown, component: unknown) => () => void
    }
  }
  if (
    Reflect.has(slotsCtx, 'slots') &&
    slotsCtx.slots?.inject &&
    slotsCtx.slots?.register
  ) {
    for (const surface of planRegistrations()) {
      if (surface.kind === 'command') continue
      try {
        const dispose = slotsCtx.slots.inject(surface.slot, () =>
          slotsCtx.slots!.register!(
            { name: surface.id, kind: surface.kind },
            // 组件由 UI 层注入；这里只负责把落点挂对。真实渲染需 DSH 运行时验证。
            null,
          ),
        )
        surfaceDisposers.push(dispose)
        logger.info('surface registered: %s -> %s', surface.id, surface.slot)
      } catch (err) {
        logger.warn('surface %s not registered on %s: %s', surface.id, surface.slot, String(err))
      }
    }
  } else {
    logger.warn(
      'ctx.slots unavailable — dashboard / tab / panel / settings surfaces not registered ' +
        '(need a DSH web host; this session has no runtime)',
    )
  }

  ctx.effect(() => [
    disposeService,
    ...surfaceDisposers,
    () => {
      void service.close()
    },
    () => {
      logger.info('pr-genius unloaded')
    },
  ])

  logger.info(
    'pr-genius loaded: kb=%s mcp=%s/%s locale=%s maintainer=%s',
    kb.root,
    resolved.mcp.transport,
    service.describe().mcp.endpoint,
    resolved.locale,
    String(resolved.maintainer.enabled),
  )
}
