import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js'
import {
  CallToolResultSchema,
  ListToolsResultSchema,
} from '@modelcontextprotocol/sdk/types.js'

function fail(message, details = undefined) {
  const payload = { success: false, message }
  if (details !== undefined) {
    payload.details = details
  }
  process.stdout.write(JSON.stringify(payload))
  process.exit(1)
}

function parseInput(raw) {
  try {
    return JSON.parse(raw)
  } catch (error) {
    fail(`Invalid bridge input JSON: ${error.message}`)
  }
}

function timeoutAfter(ms, label) {
  return new Promise((_, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`${label} timed out after ${ms}ms`))
    }, ms)
    timer.unref?.()
  })
}

async function withTimeout(promise, ms, label) {
  return await Promise.race([promise, timeoutAfter(ms, label)])
}

function buildTransport(server) {
  if (server.transport === 'http') {
    return new StreamableHTTPClientTransport(new URL(server.url))
  }

  const env = {
    ...process.env,
    ...(server.env || {}),
  }

  return new StdioClientTransport({
    command: server.command,
    args: server.args || [],
    env,
    stderr: 'pipe',
  })
}

async function collectStderr(transport) {
  let stderrOutput = ''
  if (transport?.stderr) {
    transport.stderr.on('data', chunk => {
      try {
        stderrOutput += chunk.toString()
      } catch {
        // Ignore secondary logging failures.
      }
    })
  }
  return () => stderrOutput.trim()
}

async function main() {
  const rawInput = await new Promise((resolve, reject) => {
    let body = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', chunk => {
      body += chunk
    })
    process.stdin.on('end', () => resolve(body))
    process.stdin.on('error', reject)
  })

  const request = parseInput(rawInput)
  const {
    action,
    server,
    tool_name: toolName,
    arguments: toolArguments = {},
    timeout_ms: timeoutMs = 15000,
  } = request

  if (!server || !server.transport) {
    fail('Bridge request is missing server configuration.')
  }

  const transport = buildTransport(server)
  const getStderr = await collectStderr(transport)

  const client = new Client(
    {
      name: 'multiclaw',
      version: '0.1.0',
    },
    {
      capabilities: {},
    },
  )

  try {
    await withTimeout(client.connect(transport), timeoutMs, 'MCP connect')

    if (action === 'list_tools') {
      const result = await withTimeout(
        client.request({ method: 'tools/list' }, ListToolsResultSchema),
        timeoutMs,
        'tools/list',
      )
      process.stdout.write(
        JSON.stringify({
          success: true,
          tools: result.tools || [],
          stderr: getStderr(),
        }),
      )
      return
    }

    if (action === 'call_tool') {
      if (!toolName) {
        fail('Bridge request is missing tool_name.')
      }
      const result = await withTimeout(
        client.request(
          {
            method: 'tools/call',
            params: {
              name: toolName,
              arguments: toolArguments,
            },
          },
          CallToolResultSchema,
        ),
        timeoutMs,
        'tools/call',
      )
      process.stdout.write(
        JSON.stringify({
          success: true,
          result,
          stderr: getStderr(),
        }),
      )
      return
    }

    fail(`Unsupported bridge action: ${action}`)
  } catch (error) {
    fail(error instanceof Error ? error.message : String(error), {
      stderr: getStderr(),
    })
  } finally {
    try {
      await client.close()
    } catch {
      // Ignore close errors during teardown.
    }
  }
}

await main()
