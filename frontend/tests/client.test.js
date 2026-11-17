import test from 'node:test'
import assert from 'node:assert/strict'
import { ApiClient, ApiError, errorMessage } from '../src/api/client.js'

const json = (body, status = 200, headers = {}) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })

test('JSON writes include same-origin cookies and a fresh CSRF token before each mutation', async () => {
  const calls = []
  let token = 0
  const client = new ApiClient(async (url, options) => {
    calls.push({ url, ...options })
    return url.endsWith('/csrf') ? json({ csrf_token: `token-${++token}` }) : json({ id: 'created' })
  })
  await client.post('/v1/registrations', { business: { name: 'Bakery' } })
  await client.patch('/v1/admin/businesses/owned', { name: 'Updated' })
  assert.deepEqual(calls.map(call => call.url), ['/api/v1/auth/csrf', '/api/v1/registrations', '/api/v1/auth/csrf', '/api/v1/admin/businesses/owned'])
  assert.equal(calls[1].headers['X-CSRF-Token'], 'token-1')
  assert.equal(calls[3].headers['X-CSRF-Token'], 'token-2')
  assert.equal(calls[1].headers['Content-Type'], 'application/json')
  assert.deepEqual(JSON.parse(calls[1].body), { business: { name: 'Bakery' } })
  assert.ok(calls.every(call => call.credentials === 'same-origin' && call.cache === 'no-store'))
})

test('multipart uploads leave content type/boundary to the browser and 204 is empty', async () => {
  const form = new FormData()
  form.set('file', new Blob(['photo'], { type: 'image/png' }), 'sample.png')
  let upload
  const client = new ApiClient(async (url, options) => {
    if (url.endsWith('/csrf')) return json({ csrf_token: 'token' })
    upload = options
    return new Response(null, { status: 204 })
  })
  assert.equal(await client.put('/v1/admin/businesses/owned/logo', form), null)
  assert.equal(upload.body, form)
  assert.equal(upload.headers['Content-Type'], undefined)
})

test('validation fields and Retry-After survive structured API errors', async () => {
  const client = new ApiClient(async () => json({ error: { code: 'email_unavailable', message: 'Email unavailable.', fields: { 'owner.email': 'Use another email.' } } }, 409))
  await assert.rejects(client.get('/v1/example'), error => error instanceof ApiError && error.status === 409 && error.fields['owner.email'] === 'Use another email.')
  const limited = new ApiClient(async () => json({ error: { code: 'rate_limited', message: 'Too many attempts.' } }, 429, { 'Retry-After': '32' }))
  await assert.rejects(limited.get('/v1/example'), error => errorMessage(error).includes('32 seconds'))
})

test('a rejected CSRF mutation is not automatically replayed', async () => {
  let writes = 0
  const client = new ApiClient(async url => {
    if (url.endsWith('/csrf')) return json({ csrf_token: 'token' })
    writes += 1
    return json({ error: { code: 'csrf_rejected', message: 'Request verification failed.' } }, 403)
  })
  await assert.rejects(client.post('/v1/registrations', {}), error => error.code === 'csrf_rejected')
  assert.equal(writes, 1)
})

test('missing owner sessions notify listeners; invalid login credentials do not', async () => {
  let notifications = 0
  let code = 'invalid_credentials'
  const client = new ApiClient(async () => json({ error: { code, message: 'Sign in.' } }, 401))
  const unsubscribe = client.onUnauthorized(() => notifications++)
  await assert.rejects(client.get('/v1/example'))
  assert.equal(notifications, 0)
  code = 'authentication_required'
  await assert.rejects(client.get('/v1/example'))
  assert.equal(notifications, 1)
  unsubscribe()
})

test('network errors and non-JSON server failures have safe messages', async () => {
  const offline = new ApiClient(async () => { throw new TypeError('private connection detail') })
  await assert.rejects(offline.get('/ready'), error => !error.message.includes('private') && error.status === 0)
  const gateway = new ApiClient(async () => new Response('<html>Bad gateway</html>', { status: 502 }))
  await assert.rejects(gateway.get('/ready'), error => error.status === 502 && !error.message.includes('<html>'))
  const malformed = new ApiClient(async () => new Response('not JSON'))
  await assert.rejects(malformed.get('/ready'), error => error.code === 'invalid_response')
})

test('concurrent mutations share only the in-flight bootstrap and aborts remain cancellable', async () => {
  let bootstraps = 0
  let resolve
  const boot = new Promise(done => { resolve = done })
  const client = new ApiClient(async url => {
    if (url.endsWith('/csrf')) { bootstraps++; await boot; return json({ csrf_token: 'token' }) }
    return new Response(null, { status: 204 })
  })
  const first = client.delete('/v1/one')
  const second = client.delete('/v1/two')
  resolve()
  await Promise.all([first, second])
  assert.equal(bootstraps, 1)
  const controller = new AbortController()
  controller.abort()
  const cancelled = new ApiClient(async (url, options) => { options.signal.throwIfAborted() })
  await assert.rejects(cancelled.get('/ready', { signal: controller.signal }), error => error.name === 'AbortError')
})
