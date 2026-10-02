/**
 * MCP 传输层单元测试：JSON-RPC 封包/解包、http 与 stdio 两种传输、超时与关闭。
 * 用假 stdio 服务与注入的 fetch —— 不依赖 Python 引擎，也不启动 DSH。
 */
import assert from 'node:assert/strict'
import { fileURLToPath } from 'node:url'
import { describe, it } from 'node:test'
import {
  createMcpInvoker,
  extractRpcResponse,
  McpCallError,
  type McpClientOptions,
} from '../src/mcp-client.ts'

const FIXTURE = fileURLToPath(new URL('./fixtures/fake-mcp-stdio.mjs', import.meta.url))

function stdioOptions(overrides: Partial<McpClientOptions> = {}): McpClientOptions {
  return {
    transport: 'stdio',
    command: process.execPath,
    args: [FIXTURE],
    url: 'http://127.0.0.1:1/mcp',
    timeoutMs: 5_000,
    protocolVersion: '2025-06-18',
    clientName: 'pr-genius-test',
    clientVersion: '0.0.0',
    ...overrides,
  }
}

function httpOptions(overrides: Partial<McpClientOptions> = {}): McpClientOptions {
  return {
    transport: 'http',
    command: 'unused',
    args: [],
    url: 'http://127.0.0.1:8000/mcp',
    timeoutMs: 5_000,
    protocolVersion: '2025-06-18',
    clientName: 'pr-genius-test',
    clientVersion: '0.0.0',
    ...overrides,
  }
}

describe('extractRpcResponse', () => {
  it('parses a plain JSON body', () => {
    const text = JSON.stringify({ jsonrpc: '2.0', id: 1, result: { ok: true } })
    assert.deepEqual(extractRpcResponse(text, 1)?.result, { ok: true })
  })

  it('parses an SSE event stream and picks the matching id', () => {
    const text = [
      'event: message',
      'data: {"jsonrpc":"2.0","id":1,"result":{"step":"init"}}',
      '',
      'event: message',
      'data: {"jsonrpc":"2.0","id":2,"result":{"step":"call"}}',
      '',
    ].join('\n')
    assert.deepEqual(extractRpcResponse(text, 2)?.result, { step: 'call' })
  })

  it('returns undefined when no response matches the id', () => {
    const text = JSON.stringify({ jsonrpc: '2.0', id: 9, result: {} })
    assert.equal(extractRpcResponse(text, 1), undefined)
  })
})

describe('http transport', () => {
  it('performs initialize handshake then tools/call, forwarding tool name and arguments', async () => {
    const seen: Array<{ url: string; body: Record<string, unknown> }> = []
    const fetchImpl: typeof fetch = async (input, init) => {
      const body = JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>
      seen.push({ url: String(input), body })
      const id = body.id as number
      const method = body.method as string
      const payload =
        method === 'initialize'
          ? { jsonrpc: '2.0', id, result: { protocolVersion: '2025-06-18' } }
          : { jsonrpc: '2.0', id, result: { tool: 'analyze_pr', ok: true } }
      return new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      })
    }
    const invoker = createMcpInvoker(httpOptions(), () => {}, fetchImpl)
    const result = (await invoker.callTool('analyze_pr', { title: 'fix: x', repo: 'org/name' })) as {
      tool: string
      ok: boolean
    }
    assert.equal(result.tool, 'analyze_pr')
    assert.equal(result.ok, true)

    assert.equal(seen.length, 3, 'initialize + initialized notification + tools/call')
    assert.equal(seen[0]?.body.method, 'initialize')
    assert.equal(seen[1]?.body.method, 'notifications/initialized')
    assert.equal(seen[2]?.body.method, 'tools/call')
    const call = seen[2]?.body.params as { name: string; arguments: Record<string, unknown> }
    assert.equal(call.name, 'analyze_pr')
    assert.deepEqual(call.arguments, { title: 'fix: x', repo: 'org/name' })
    await invoker.close()
  })

  it('parses an SSE response for tools/call', async () => {
    let id = 0
    const fetchImpl: typeof fetch = async (_input, init) => {
      const body = JSON.parse(String(init?.body ?? '{}')) as { id?: number; method?: string }
      id = body.id ?? 0
      const sse =
        body.method === 'initialize'
          ? `data: ${JSON.stringify({ jsonrpc: '2.0', id, result: {} })}\n\n`
          : `data: ${JSON.stringify({ jsonrpc: '2.0', id, result: { via: 'sse' } })}\n\n`
      return new Response(sse, { status: 200, headers: { 'content-type': 'text/event-stream' } })
    }
    const invoker = createMcpInvoker(httpOptions(), () => {}, fetchImpl)
    assert.deepEqual(await invoker.callTool('coach_pr', {}), { via: 'sse' })
    await invoker.close()
  })

  it('surfaces JSON-RPC errors as McpCallError naming the tool', async () => {
    const fetchImpl: typeof fetch = async (_input, init) => {
      const body = JSON.parse(String(init?.body ?? '{}')) as { id?: number; method?: string }
      const payload =
        body.method === 'initialize'
          ? { jsonrpc: '2.0', id: body.id, result: {} }
          : {
              jsonrpc: '2.0',
              id: body.id,
              error: { code: -32000, message: 'unknown tool: nope' },
            }
      return new Response(JSON.stringify(payload), { status: 200 })
    }
    const invoker = createMcpInvoker(httpOptions(), () => {}, fetchImpl)
    await assert.rejects(
      () => invoker.callTool('nope'),
      (error: unknown) => {
        assert.ok(error instanceof McpCallError)
        assert.equal(error.tool, 'nope')
        assert.equal(error.code, -32000)
        assert.match(error.message, /unknown tool: nope/)
        return true
      },
    )
    await invoker.close()
  })

  it('times out instead of waiting forever', async () => {
    const fetchImpl: typeof fetch = async (_input, init) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new Error('aborted'))
        })
      })
    const invoker = createMcpInvoker(httpOptions({ timeoutMs: 30 }), () => {}, fetchImpl)
    await assert.rejects(
      () => invoker.callTool('analyze_pr'),
      (error: unknown) => {
        assert.ok(error instanceof McpCallError)
        assert.match(error.message, /timed out after 30ms/)
        return true
      },
    )
    await invoker.close()
  })
})

describe('stdio transport', () => {
  it('talks newline-delimited JSON-RPC to a child process', async () => {
    const stderrLines: string[] = []
    const invoker = createMcpInvoker(stdioOptions(), (line) => stderrLines.push(line))
    const result = (await invoker.callTool('analyze_pr', { title: 'fix: x' })) as {
      tool: string
      arguments: Record<string, unknown>
    }
    assert.equal(result.tool, 'analyze_pr')
    assert.deepEqual(result.arguments, { title: 'fix: x' })
    await invoker.close()
  })

  it('times out when the server answers too slowly, then refuses calls after close', async () => {
    const invoker = createMcpInvoker(stdioOptions({ args: [FIXTURE, '200'], timeoutMs: 50 }))
    await assert.rejects(
      () => invoker.callTool('analyze_pr'),
      (error: unknown) => {
        assert.ok(error instanceof McpCallError)
        assert.match(error.message, /timed out after 50ms/)
        return true
      },
    )
    await invoker.close()
    await assert.rejects(() => invoker.callTool('analyze_pr'), /closed/)
  })

  it('close() is idempotent and rejects later calls', async () => {
    const invoker = createMcpInvoker(stdioOptions())
    await invoker.callTool('schema_info', {})
    await invoker.close()
    await invoker.close()
    await assert.rejects(() => invoker.callTool('schema_info'), /closed/)
  })
})
