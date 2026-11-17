import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer as createHttpServer, request as httpRequest } from 'node:http'
import { fileURLToPath } from 'node:url'
import { createServer as createViteServer } from 'vite'
import config from '../vite.config.js'

test('real Vite proxy preserves browser Host and Origin for API and media requests', async () => {
  const upstream = createHttpServer((request, response) => {
    response.setHeader('Content-Type', 'application/json')
    response.end(JSON.stringify({ host: request.headers.host, origin: request.headers.origin }))
  })
  await new Promise(resolve => upstream.listen(0, '127.0.0.1', resolve))
  const target = `http://127.0.0.1:${upstream.address().port}`
  const proxy = Object.fromEntries(Object.entries(config.server.proxy).map(([prefix, options]) => [prefix, typeof options === 'string' ? target : { ...options, target }]))
  let vite
  let frontend
  try {
    vite = await createViteServer({
      configFile: false,
      root: fileURLToPath(new URL('../', import.meta.url)),
      logLevel: 'silent',
      optimizeDeps: { noDiscovery: true, include: [] },
      server: { ...config.server, middlewareMode: true, hmr: false, watch: null, proxy },
    })
    frontend = createHttpServer((request, response) => vite.middlewares(request, response))
    await new Promise(resolve => frontend.listen(0, '127.0.0.1', resolve))
    const port = frontend.address().port
    for (const path of ['/api/probe', '/media/probe']) {
      const response = await new Promise((resolve, reject) => {
        const request = httpRequest({ hostname: '127.0.0.1', port, path, headers: { Host: 'bakery.localhost:5173', Origin: 'http://bakery.localhost:5173' } }, incoming => {
          let text = ''
          incoming.setEncoding('utf8')
          incoming.on('data', chunk => { text += chunk })
          incoming.on('end', () => resolve({ status: incoming.statusCode, text }))
        })
        request.on('error', reject)
        request.end()
      })
      assert.equal(response.status, 200)
      assert.deepEqual(JSON.parse(response.text), { host: 'bakery.localhost:5173', origin: 'http://bakery.localhost:5173' })
    }
  } finally {
    await vite?.close()
    if (frontend) {
      frontend.closeAllConnections()
      await new Promise(resolve => frontend.close(resolve))
    }
    upstream.closeAllConnections()
    await new Promise(resolve => upstream.close(resolve))
  }
})
