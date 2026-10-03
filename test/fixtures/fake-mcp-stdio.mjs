#!/usr/bin/env node
/**
 * 测试用假 MCP stdio 服务：换行分隔 JSON-RPC，支持 initialize / tools/call。
 * 用法：node fake-mcp-stdio.mjs [delayMs]
 *   delayMs > 0 时，tools/call 响应延迟 delayMs 毫秒（用于超时测试）。
 */
import { createInterface } from 'node:readline'

const delayMs = Number(process.argv[2] ?? '0')
let nextResult = 0

const rl = createInterface({ input: process.stdin })
rl.on('line', (line) => {
  const text = line.trim()
  if (text === '') return
  let msg
  try {
    msg = JSON.parse(text)
  } catch {
    return
  }
  if (msg.method === 'initialize') {
    process.stdout.write(
      `${JSON.stringify({
        jsonrpc: '2.0',
        id: msg.id,
        result: {
          protocolVersion: msg.params?.protocolVersion ?? '2025-06-18',
          capabilities: {},
          serverInfo: { name: 'fake-mcp-stdio', version: '0.0.0' },
        },
      })}\n`,
    )
    return
  }
  if (msg.method === 'tools/call') {
    const respond = () => {
      process.stdout.write(
        `${JSON.stringify({
          jsonrpc: '2.0',
          id: msg.id,
          result: {
            tool: msg.params?.name,
            arguments: msg.params?.arguments,
            echo: nextResult++,
          },
        })}\n`,
      )
    }
    if (delayMs > 0) setTimeout(respond, delayMs)
    else respond()
    return
  }
  if (msg.id !== undefined) {
    process.stdout.write(
      `${JSON.stringify({
        jsonrpc: '2.0',
        id: msg.id,
        error: { code: -32601, message: `method not found: ${msg.method}` },
      })}\n`,
    )
  }
})
