/**
 * 调用现有 Python FastMCP 分析服务的唯一通道（stdio / http 两种传输）。
 *
 * 架构约束：分析引擎只有一份（Python, prgenius/src/prgenius/）。本文件只做
 * JSON-RPC 传输与超时控制，不复制任何分析逻辑。工具名与参数直接透传。
 *
 * 需 DSH 运行时验证，本机未执行（无 DEEPSEEK_API_KEY、未起 DSH）。
 */
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import type { McpTransport } from './config.ts'

export interface McpClientOptions {
  transport: McpTransport
  /** stdio: 可执行文件。 */
  command: string
  /** stdio: 参数。 */
  args: string[]
  /** http: JSON-RPC 端点。 */
  url: string
  /** 单次请求超时（毫秒）。 */
  timeoutMs: number
  /** initialize 握手的 protocolVersion。 */
  protocolVersion: string
  /** initialize 握手的 clientInfo.name。 */
  clientName: string
  /** initialize 握手的 clientInfo.version。 */
  clientVersion: string
}

export interface McpInvoker {
  /** 调用 FastMCP 工具（tools/call），透传 name/arguments。 */
  callTool(name: string, args?: Record<string, unknown>): Promise<unknown>
  /** 释放传输层（杀掉子进程 / 中止在途请求）。幂等。 */
  close(): Promise<void>
}

export class McpCallError extends Error {
  readonly tool: string
  readonly code?: number

  constructor(tool: string, message: string, code?: number, cause?: unknown) {
    super(`pr-genius MCP call failed for tool ${tool}: ${message}`)
    this.name = 'McpCallError'
    this.tool = tool
    this.code = code
    if (cause !== undefined) {
      ;(this as { cause?: unknown }).cause = cause
    }
  }
}

interface JsonRpcSuccess {
  jsonrpc: '2.0'
  id: number | string
  result: unknown
  error?: undefined
}

interface JsonRpcFailure {
  jsonrpc: '2.0'
  id: number | string | null
  error: { code: number; message: string; data?: unknown }
  result?: undefined
}

type JsonRpcMessage = JsonRpcSuccess | JsonRpcFailure

function isJsonRpcMessage(value: unknown): value is JsonRpcMessage {
  return (
    typeof value === 'object' &&
    value !== null &&
    'jsonrpc' in value &&
    (value as { jsonrpc?: unknown }).jsonrpc === '2.0'
  )
}

/** 从 JSON 响应体或 SSE 事件流里取出与 id 匹配的那条响应。 */
export function extractRpcResponse(text: string, id: number | string): JsonRpcMessage | undefined {
  const trimmed = text.trim()
  if (trimmed === '') return undefined
  // SSE: 事件块以空行分隔，负载在 `data:` 行。
  const payloads: string[] = []
  if (trimmed.startsWith('event:') || trimmed.startsWith('data:') || trimmed.includes('\ndata:')) {
    for (const block of trimmed.split(/\n\n+/)) {
      const data = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice('data:'.length).trim())
        .join('')
      if (data !== '') payloads.push(data)
    }
  } else {
    payloads.push(trimmed)
  }
  for (const payload of payloads) {
    let parsed: unknown
    try {
      parsed = JSON.parse(payload)
    } catch {
      continue
    }
    const candidates = Array.isArray(parsed) ? parsed : [parsed]
    for (const candidate of candidates) {
      if (isJsonRpcMessage(candidate) && candidate.id === id) return candidate
    }
  }
  return undefined
}

function unwrapResult(tool: string, message: JsonRpcMessage | undefined): unknown {
  if (message === undefined) {
    throw new McpCallError(tool, 'no JSON-RPC response with matching id')
  }
  if (message.error !== undefined) {
    throw new McpCallError(tool, message.error.message, message.error.code)
  }
  return message.result
}

// ---------------------------------------------------------------------------
// http 传输：JSON-RPC over HTTP POST（FastMCP streamable-http 兼容：JSON 或 SSE 响应）
// ---------------------------------------------------------------------------

class HttpMcpInvoker implements McpInvoker {
  private nextId = 1
  private sessionId: string | undefined
  private initialized = false
  private readonly inflight = new Set<AbortController>()
  private closed = false
  // 显式字段声明，而不是 TypeScript 参数属性（`constructor(private readonly x)`）。
  // 参数属性要靠**转换**才能降级成 JS，而 Node 的 strip-only 类型剥离只删类型标注，
  // 遇到它直接 ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX。声明成普通字段则两种模式都能跑。
  private readonly options: McpClientOptions
  private readonly fetchImpl: typeof fetch

  constructor(options: McpClientOptions, fetchImpl: typeof fetch = fetch) {
    this.options = options
    this.fetchImpl = fetchImpl
  }

  async callTool(name: string, args: Record<string, unknown> = {}): Promise<unknown> {
    if (this.closed) throw new McpCallError(name, 'invoker already closed')
    await this.ensureSession()
    const id = this.nextId++
    const message = await this.send(
      { jsonrpc: '2.0', id, method: 'tools/call', params: { name, arguments: args } },
      name,
    )
    return unwrapResult(name, message)
  }

  async close(): Promise<void> {
    this.closed = true
    for (const controller of this.inflight) controller.abort()
    this.inflight.clear()
    this.initialized = false
    this.sessionId = undefined
  }

  private async ensureSession(): Promise<void> {
    if (this.initialized) return
    const id = this.nextId++
    await this.send(
      {
        jsonrpc: '2.0',
        id,
        method: 'initialize',
        params: {
          protocolVersion: this.options.protocolVersion,
          capabilities: {},
          clientInfo: {
            name: this.options.clientName,
            version: this.options.clientVersion,
          },
        },
      },
      'initialize',
    )
    await this.send({ jsonrpc: '2.0', method: 'notifications/initialized' }, 'initialize')
    this.initialized = true
  }

  private async send(payload: object, tool: string): Promise<JsonRpcMessage | undefined> {
    const controller = new AbortController()
    this.inflight.add(controller)
    const timer = setTimeout(() => controller.abort(), this.options.timeoutMs)
    try {
      const headers: Record<string, string> = {
        'content-type': 'application/json',
        accept: 'application/json, text/event-stream',
      }
      if (this.sessionId !== undefined) headers['mcp-session-id'] = this.sessionId
      const response = await this.fetchImpl(this.options.url, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      })
      const session = response.headers.get('mcp-session-id')
      if (session !== null) this.sessionId = session
      const text = await response.text()
      if (!response.ok) {
        throw new McpCallError(tool, `HTTP ${response.status} ${response.statusText}: ${text}`)
      }
      if ('id' in payload) {
        return extractRpcResponse(text, (payload as { id: number }).id)
      }
      return undefined
    } catch (error) {
      if (error instanceof McpCallError) throw error
      if (controller.signal.aborted) {
        throw new McpCallError(tool, `timed out after ${this.options.timeoutMs}ms`, undefined, error)
      }
      throw new McpCallError(tool, error instanceof Error ? error.message : String(error), undefined, error)
    } finally {
      clearTimeout(timer)
      this.inflight.delete(controller)
    }
  }
}

// ---------------------------------------------------------------------------
// stdio 传输：拉起 Python FastMCP 服务，换行分隔的 JSON-RPC
// ---------------------------------------------------------------------------

class StdioMcpInvoker implements McpInvoker {
  private child: ChildProcessWithoutNullStreams | undefined
  private nextId = 1
  private readonly pending = new Map<
    number,
    { resolve: (message: JsonRpcMessage) => void; reject: (error: Error) => void; timer: NodeJS.Timeout }
  >()
  private buffer = ''
  private initialized = false
  private closed = false

  // 同上：不用参数属性 —— strip-only 类型剥离不支持（ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX）。
  private readonly options: McpClientOptions
  private readonly onStderr: (line: string) => void

  constructor(options: McpClientOptions, onStderr: (line: string) => void = () => {}) {
    this.options = options
    this.onStderr = onStderr
  }

  async callTool(name: string, args: Record<string, unknown> = {}): Promise<unknown> {
    if (this.closed) throw new McpCallError(name, 'invoker already closed')
    await this.ensureSession()
    const message = await this.request(
      { method: 'tools/call', params: { name, arguments: args } },
      name,
    )
    return unwrapResult(name, message)
  }

  async close(): Promise<void> {
    if (this.closed) return
    this.closed = true
    for (const [, entry] of this.pending) {
      clearTimeout(entry.timer)
      entry.reject(new Error('pr-genius MCP invoker closed'))
    }
    this.pending.clear()
    const child = this.child
    this.child = undefined
    if (child !== undefined && child.exitCode === null && child.signalCode === null) {
      child.kill('SIGTERM')
    }
  }

  private ensureChild(): ChildProcessWithoutNullStreams {
    if (this.child !== undefined) return this.child
    const child = spawn(this.options.command, this.options.args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: false,
    })
    this.child = child
    child.stdout.setEncoding('utf8')
    child.stdout.on('data', (chunk: string) => this.onStdout(chunk))
    child.stderr.setEncoding('utf8')
    let stderrBuffer = ''
    child.stderr.on('data', (chunk: string) => {
      stderrBuffer += chunk
      const lines = stderrBuffer.split('\n')
      stderrBuffer = lines.pop() ?? ''
      for (const line of lines) if (line.trim() !== '') this.onStderr(line)
    })
    child.on('exit', (code, signal) => {
      const error = new Error(`pr-genius MCP server exited (code=${code}, signal=${signal})`)
      for (const [, entry] of this.pending) {
        clearTimeout(entry.timer)
        entry.reject(error)
      }
      this.pending.clear()
      this.child = undefined
      this.initialized = false
    })
    return child
  }

  private async ensureSession(): Promise<void> {
    if (this.initialized) return
    await this.request(
      {
        method: 'initialize',
        params: {
          protocolVersion: this.options.protocolVersion,
          capabilities: {},
          clientInfo: {
            name: this.options.clientName,
            version: this.options.clientVersion,
          },
        },
      },
      'initialize',
    )
    const child = this.ensureChild()
    child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' })}\n`)
    this.initialized = true
  }

  private request(
    payload: { method: string; params?: object },
    tool: string,
  ): Promise<JsonRpcMessage> {
    const child = this.ensureChild()
    const id = this.nextId++
    return new Promise<JsonRpcMessage>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new McpCallError(tool, `timed out after ${this.options.timeoutMs}ms`))
      }, this.options.timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      child.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', id, ...payload })}\n`, (error) => {
        if (error !== null && error !== undefined) {
          clearTimeout(timer)
          this.pending.delete(id)
          reject(new McpCallError(tool, `stdin write failed: ${error.message}`, undefined, error))
        }
      })
    })
  }

  private onStdout(chunk: string): void {
    this.buffer += chunk
    const lines = this.buffer.split('\n')
    this.buffer = lines.pop() ?? ''
    for (const line of lines) {
      const text = line.trim()
      if (text === '') continue
      let parsed: unknown
      try {
        parsed = JSON.parse(text)
      } catch {
        continue
      }
      if (!isJsonRpcMessage(parsed) || parsed.id === null) continue
      const id = parsed.id
      if (typeof id !== 'number') continue
      const entry = this.pending.get(id)
      if (entry === undefined) continue
      this.pending.delete(id)
      clearTimeout(entry.timer)
      entry.resolve(parsed)
    }
  }
}

/**
 * 按配置创建传输层。stdio 会拉起 `command + args`（默认 prgenius-core mcp serve）。
 * 创建不产生副作用，真正 spawn 在首次 callTool。
 */
export function createMcpInvoker(
  options: McpClientOptions,
  onStderr: (line: string) => void = () => {},
  fetchImpl: typeof fetch = fetch,
): McpInvoker {
  return options.transport === 'http'
    ? new HttpMcpInvoker(options, fetchImpl)
    : new StdioMcpInvoker(options, onStderr)
}
