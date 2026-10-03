/**
 * denyRead 语义的宿主 mock —— 专治「gate 看绿、真宿主是坏的」这一类假通过。
 *
 * 为什么需要它：此前的测试/门禁把 `slots` 当**字面量属性**挂在 ctx 上，于是
 * `Reflect.has(ctx, 'slots')` 恒真、`ctx.slots` 直读恒通 —— 绕开了真宿主的 guard。
 * 真宿主里 apply() 收到的是 dynamicCordisContext 的白名单 facade，直读未声明的
 * 名字会 **抛错**（issue #100 的真根因）。这个 mock 按那个 facade 的语义构造，
 * 让「重新引入 Reflect.has + 直读」在测试/发版门禁里立刻红。
 *
 * 权威依据（逐条对照 node_modules/@deepseek-ai/dsh-cordis-client-runner/lib/client.js
 * 的 dynamicCordisContext，约 314-350 行）：
 *   1. declared = new Set(Object.keys(ctx.fiber.inject))；本插件 inject 为 []。
 *   2. 直读未声明名 → readService(prop, true) → denyRead **抛错**。消息两段：
 *      服务其实存在时说「Declare it on the plugin …」，不存在时说
 *      「dynamic ctx does not expose "…"」—— denyRead() 里是原文照抄。
 *   3. has trap 只答 declared.has(prop)（外加 get / CTX_VERBS）—— 不抛，但恒 false。
 *   4. ctx.get(name) → readService(name, false)：**可选查找，不需要 inject 声明**
 *      （同上文件 get trap；语义来自 cordis ReflectService.get 的 docstring：
 *      "Read a service from the store without the inject requirement."）。
 *      未提供时返回 undefined，不抛。
 *
 * 诚实边界（不装作比真 guard 更真）：
 *   - `logger` 也走 denyRead，本 mock **不**放行它。真 guard 的 CTX_VERBS =
 *     effect/on/once/provide/timer 系，不含 logger（client.js 205-216、upstream
 *     guard.ts 22-24 两处一致，upstream 全文 0 次提到 logger），且 LoggerService
 *     不在 service store（Context 构造器里 `this.logger = new LoggerService(self)`
 *     只是属性赋值，不调 provide()）—— 所以真宿主上 `ctx.logger` 直读会抛、
 *     `ctx.get('logger')` 取不到、写进 `inject` 会让 fiber 永久挂起。apply() 用
 *     `resolveLogger()` 分流（`Reflect.has` 为真才直读，否则 console 兜底），
 *     见 test/surface-data.test.ts 的 logger 用例。
 *   - 本 mock 只覆盖 apply() 实际触碰的面（provide/effect/get + 可选
 *     slots/command）；guard 的 ledger、guardedSlots 包装、theme 特例都不在这里。
 */

/**
 * 按 dynamicCordisContext 的 denyRead 语义抛错。消息两段照抄 client.js 原文
 * （`service "X" is not declared by your plugin. …` / `dynamic ctx does not expose "X". …`），
 * 勿改写 —— 改了就不是「同语义」了。
 * `present` = 该名字在宿主服务表里其实存在（对应 client.js 里 `ctx.get(prop) !== void 0`）。
 */
export function denyRead(prop: string, present: boolean): never {
  if (present) {
    throw new Error(
      `service "${prop}" is not declared by your plugin. Declare it on the plugin you return: ` +
        `{ inject: ['${prop}', …], apply(ctx) { … } } — a plain \`function\` has no ` +
        'declaration site, so use the object form. The runtime then parks the package ' +
        'if the provider unloads.',
    )
  }
  throw new Error(
    `dynamic ctx does not expose "${prop}". Available: ctx.on / ctx.provide / timer ` +
      'helpers after injecting timer, and any service your returned plugin declared in ' +
      'inject (slots and theme are the usual UI seats). Framework internals are withheld ' +
      'by design.',
  )
}

/** 真 guard 的 CTX_VERBS（client.js 205-216 行）+ 本 mock 额外放行的 logger（见文件头）。 */
const CTX_VERBS = new Set([
  'effect',
  'on',
  'once',
  'provide',
  'timeout',
  'interval',
  'setTimeout',
  'setInterval',
  'throttle',
  'debounce',
])

export interface GuardedHostOptions {
  /**
   * 宿主服务表：`ctx.get(name)` 从这里取。**不要**把它同时挂成 ctx 的字面量属性
   * ——那正是旧 mock 绕开 guard 的做法。slots/command 走这里才算数。
   */
  services?: Record<string, unknown>
  /** plugin 的 declared inject；本插件应为 []。 */
  declaredInject?: readonly string[]
}

export interface GuardedHost {
  ctx: object
  /** 记录 ctx.get 被调用的名字，供断言「确实走了 get 路径」。 */
  getLog: string[]
}

/**
 * 构造 denyRead 语义的宿主 ctx。apply() 必须只经 ctx.get 取可选服务，
 * 否则这里会抛（或 has 为 false 导致静默不注册），测试立刻红。
 */
export function makeGuardedHost(opts: GuardedHostOptions = {}): GuardedHost {
  const services = { ...(opts.services ?? {}) }
  const declared = new Set(opts.declaredInject ?? [])
  const getLog: string[] = []

  const readService = (name: string, requireDeclaration: boolean): unknown => {
    if (requireDeclaration && !declared.has(name)) {
      // 直读未声明名 —— 与真 guard 同效：抛，不返回 undefined
      denyRead(name, name in services)
    }
    return services[name]
  }

  const target: Record<string, unknown> = {}
  // apply() 实际触碰的 Context 动词 —— 真 guard 里这些走 CTX_VERBS 转发。
  // **logger 不在这里**：真 guard 的 CTX_VERBS 不含 logger（client.js 205-216、
  // upstream guard.ts 22-24 两处一致，upstream 全文 0 次提到 logger），而
  // LoggerService 又不在 service store（Context 构造器里只是属性赋值，不 provide）。
  // 所以本 mock 也不给 logger —— apply() 必须自己降级到 console 兜底，
  // 否则真宿主上 `ctx.logger` 会 denyRead 抛错在第一行。
  target.provide = (_name: string, _service: unknown) => () => {}
  target.effect = (_fn: () => unknown) => {}

  const ctx = new Proxy(target, {
    get(t, prop, receiver) {
      if (prop === 'get') {
        return (name: string) => {
          getLog.push(name)
          return readService(name, false)
        }
      }
      if (typeof prop !== 'string') return Reflect.get(t, prop, receiver)
      if (prop in t) return Reflect.get(t, prop, receiver)
      if (CTX_VERBS.has(prop)) return Reflect.get(t, prop, receiver)
      // 未声明的服务名 → denyRead 抛（与真 guard 的 readService(prop, true) 同效）
      return readService(prop, true)
    },
    has(_t, prop) {
      // 真 guard 的 has trap：只答 get / CTX_VERBS / declared，恒不抛
      return prop === 'get' || (typeof prop === 'string' && (CTX_VERBS.has(prop) || declared.has(prop)))
    },
    set() {
      throw new Error('dynamic ctx is read-only')
    },
  })

  return { ctx, getLog }
}
