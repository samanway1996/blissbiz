import test from 'node:test'
import assert from 'node:assert/strict'
import { createApiHarness, hasBackend } from './support/apiHarness.js'
import { createOwnerSession } from '../src/composables/useOwnerSession.js'
import { findOwnedBusiness } from '../src/services/businesses.js'

test('real FastAPI registration → rotated CSRF → profile → logout/login → owned links and conflicts', { skip: !hasBackend, timeout: 20000 }, async () => {
  const harness = createApiHarness()
  const client = harness.client()
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
    await harness.close()
  }
})
