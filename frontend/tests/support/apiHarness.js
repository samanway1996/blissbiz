import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'
import { ApiClient } from '../../src/api/client.js'

const backend = fileURLToPath(new URL('../../../backend/', import.meta.url))
const executable = `${backend}.venv/bin/python3`
export const hasBackend = existsSync(executable)

export function createApiHarness() {
  const bridge = fileURLToPath(new URL('./api_bridge.py', import.meta.url))
  const child = spawn(executable, [bridge], {
    cwd: backend,
    env: { ...process.env, APP_ENV: 'development', PYTHONPATH: backend, DATABASE_URL: 'mysql+pymysql://unused:unused@127.0.0.1:1/unused' },
    stdio: ['pipe', 'pipe', 'pipe'],
  })
  const pending = []
  const lines = createInterface({ input: child.stdout })
  lines.on('line', line => {
    const request = pending.shift()
    try {
      const response = JSON.parse(line)
      const body = response.base64 ? Buffer.from(response.body, 'base64') : response.body
      request.resolve(new Response(response.status === 204 ? null : body, { status: response.status, headers: response.headers }))
    } catch (error) { request?.reject(error) }
  })
  let exited
  const finished = new Promise(resolve => { exited = resolve })
  child.on('error', error => { while (pending.length) pending.shift().reject(error) })
  child.on('exit', code => {
    while (pending.length) pending.shift().reject(new Error(`Disposable API bridge exited (${code}).`))
    exited(code)
  })
  child.stderr.resume()
  async function transport(url, options = {}, browser = 'default', origin = 'http://admin.localhost:5173') {
    let body = options.body
    const headers = { ...options.headers }
    const multipart = body instanceof FormData
    if (multipart) {
      const encoded = new Request('http://test.invalid', { method: options.method, body })
      headers['Content-Type'] = encoded.headers.get('Content-Type')
      body = Buffer.from(await encoded.arrayBuffer()).toString('base64')
    }
    return new Promise((resolve, reject) => {
      pending.push({ resolve, reject })
      child.stdin.write(`${JSON.stringify({ url, method: options.method || 'GET', headers, body, base64: multipart, browser, origin, credentials: options.credentials })}\n`)
    })
  }
  return {
    client(browser = 'default', origin = 'http://admin.localhost:5173', credentials = 'same-origin') {
      return new ApiClient((url, options) => transport(url, options, browser, origin), { credentials })
    },
    raw: transport,
    async close() {
      child.stdin.end()
      const timeout = setTimeout(() => child.kill('SIGTERM'), 3000)
      await finished
      clearTimeout(timeout)
      lines.close()
    },
  }
}
