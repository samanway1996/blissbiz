import test from 'node:test'
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'
import { ApiClient } from '../src/api/client.js'
import { createOwnerSession } from '../src/composables/useOwnerSession.js'
import { findOwnedBusiness } from '../src/services/businesses.js'

const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
const executable = `${backend}.venv/bin/python3`
const bridge = fileURLToPath(new URL('./support/api_bridge.py', import.meta.url))

test('real FastAPI registration → rotated CSRF → profile → logout/login → owned links and conflicts', { skip: !existsSync(executable), timeout: 20000 }, async () => {
  // The transport adapter uses TestClient's cookie jar and real routes against temporary
  // SQLite stores. It binds no server port and never touches the contributor's MySQL DB.
  const child = spawn(executable, [bridge], { cwd: backend, env: { ...process.env, PYTHONPATH: backend, DATABASE_URL: 'mysql+pymysql://unused:unused@127.0.0.1:1/unused' }, stdio: ['pipe', 'pipe', 'pipe'] })
  const pending = []
  const lines = createInterface({ input: child.stdout })
  lines.on('line', line => {
    const request = pending.shift()
    try {
      const response = JSON.parse(line)
      request.resolve(new Response(response.status === 204 ? null : response.body, { status: response.status, headers: response.headers }))
    } catch (error) { request?.reject(error) }
  })
  let exited
  const finished = new Promise(resolve => { exited = resolve })
  child.on('error', error => { while (pending.length) pending.shift().reject(error) })
  child.on('exit', code => {
    while (pending.length) pending.shift().reject(new Error(`Disposable API bridge exited (${code}).`))
    exited(code)
  })
  // Drain dependency warnings without logging protocol bodies, credentials or tokens.
  child.stderr.resume()
  const client = new ApiClient((url, options) => new Promise((resolve, reject) => {
    pending.push({ resolve, reject })
    child.stdin.write(`${JSON.stringify({ url, method: options.method, headers: options.headers, body: options.body })}\n`)
  }))
  const session = createOwnerSession(client)
  const credentials = { email: 'frontend-review@example.com', password: 'a disposable review passphrase' }
  const payload = { owner: { full_name: 'Frontend Review', ...credentials }, business: { name: 'Review Bakery', slug: 'frontend-review-bakery', currency: 'INR' } }
  try {
    assert.equal(await session.restore(), null)
    const available = await client.get('/v1/business-slugs/frontend-review-bakery/availability')
    assert.equal(available.available, true)
    const result = await session.register(payload)
    assert.equal(result.business.slug, payload.business.slug)
    assert.equal(result.urls.admin, 'http://admin.localhost:5173/businesses/frontend-review-bakery')
    assert.equal(result.urls.storefront, 'http://frontend-review-bakery.localhost:5173')
    assert.equal((await session.restore()).id, result.owner.id)
    const initialToken = await client.csrf()
    await session.logout()
    assert.equal(await session.restore(), null)
    await session.login(credentials)
    assert.notEqual(await client.csrf(), initialToken)
    const business = await findOwnedBusiness(payload.business.slug, client)
    assert.equal(business.id, result.business.id)
    assert.equal(await findOwnedBusiness('not-owned', client), null)
    await session.logout()
    await assert.rejects(client.get('/v1/admin/businesses'), error => error.status === 401)
    await assert.rejects(session.register(payload), error => error.status === 409 && Boolean(error.fields['business.slug']))
    await assert.rejects(session.register({ ...payload, business: { ...payload.business, slug: 'another-free-slug' } }), error => error.status === 409 && Boolean(error.fields['owner.email']))
    await assert.rejects(session.login({ ...credentials, password: 'wrong' }), error => error.status === 401 && error.code === 'invalid_credentials')
  } finally {
    payload.owner.password = ''
    credentials.password = ''
    child.stdin.end()
    const timeout = setTimeout(() => child.kill('SIGTERM'), 3000)
    await finished
    clearTimeout(timeout)
    lines.close()
  }
})
