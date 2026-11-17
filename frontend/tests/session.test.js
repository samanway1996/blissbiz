import test from 'node:test'
import assert from 'node:assert/strict'
import { createOwnerSession } from '../src/composables/useOwnerSession.js'
const owner = { id: 'owner-a', full_name: 'Review Owner', email: 'review@example.com' }
const client = overrides => ({ onUnauthorized: () => {}, ...overrides })

test('refresh restoration uses the backend profile and coalesces concurrent calls', async () => {
  let reads = 0
  let done
  const session = createOwnerSession(client({ get: () => { reads++; return new Promise(resolve => { done = resolve }) } }))
  const one = session.restore()
  const two = session.restore()
  done(owner)
  assert.deepEqual(await one, owner)
  assert.deepEqual(await two, owner)
  assert.equal(reads, 1)
  assert.deepEqual(session.state.owner, owner)
  assert.equal(session.state.restoring, false)
})

test('expired sessions clear identity; unavailable API is a recoverable error', async () => {
  const expired = createOwnerSession(client({ get: async () => { throw { status: 401 } } }))
  assert.equal(await expired.restore(), null)
  const unavailable = createOwnerSession(client({ get: async () => { throw new Error('offline') } }))
  await assert.rejects(unavailable.restore(), /offline/)
  assert.equal(unavailable.state.owner, null)
  assert.equal(unavailable.state.error.message, 'offline')
  assert.equal(unavailable.state.restoring, false)
})

test('registration stores only returned profile/business links; logout clears both', async () => {
  const result = { owner, business: { slug: 'bakery' }, urls: { admin: 'admin', storefront: 'public' } }
  const session = createOwnerSession(client({ post: async path => path === '/v1/registrations' ? result : null }))
  await session.register({ owner: { password: 'a review passphrase' } })
  assert.deepEqual(session.state.registration, result)
  assert.ok(!JSON.stringify(session.state).includes('passphrase'))
  await session.logout()
  assert.equal(session.state.owner, null)
  assert.equal(session.state.registration, null)
})

test('login updates identity; failed logout retains it and an already-expired logout clears it', async () => {
  let failure
  const session = createOwnerSession(client({ post: async path => { if (path.endsWith('logout') && failure) throw failure; return owner } }))
  await session.login({ email: owner.email, password: 'private passphrase' })
  assert.equal(session.state.owner.id, 'owner-a')
  failure = { status: 503 }
  await assert.rejects(session.logout())
  assert.equal(session.state.owner.id, 'owner-a')
  failure = { status: 401 }
  await session.logout()
  assert.equal(session.state.owner, null)
})

test('an older restoration response cannot restore identity after logout', async () => {
  let done
  const session = createOwnerSession(client({ get: () => new Promise(resolve => { done = resolve }), post: async () => null }))
  const pending = session.restore()
  await session.logout()
  done(owner)
  await pending
  assert.equal(session.state.owner, null)
})

test('401 notifications discard private profile and registration state', async () => {
  let invalidate
  const session = createOwnerSession({ onUnauthorized: callback => { invalidate = callback }, post: async () => ({ owner, business: {}, urls: {} }) })
  await session.register({})
  invalidate()
  assert.equal(session.state.owner, null)
  assert.equal(session.state.registration, null)
})


test('restoring a different cookie owner discards the previous registration result', async () => {
  const session = createOwnerSession(client({
    post: async () => ({ owner, business: { slug: 'private-bakery' }, urls: {} }),
    get: async () => ({ id: 'owner-b', full_name: 'Another Owner', email: 'another@example.com' }),
  }))
  await session.register({})
  await session.restore()
  assert.equal(session.state.owner.id, 'owner-b')
  assert.equal(session.state.registration, null)
})
