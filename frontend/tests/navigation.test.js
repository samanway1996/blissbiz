import test from 'node:test'
import assert from 'node:assert/strict'
import { createSiteConfig, safeReturnPath, safeBusinessUrls } from '../src/config/site.js'
import { createSessionGuard } from '../src/router/guards.js'
import { findOwnedBusiness } from '../src/services/businesses.js'

const config = createSiteConfig(new URL('http://localhost:5173'))
const target = (options = {}) => ({ meta: { admin: true }, path: '/businesses/bakery', fullPath: '/businesses/bakery', query: {}, ...options })

test('landing points to central admin; business links must agree with configured origins', () => {
  assert.equal(config.adminUrl('/register'), 'http://admin.localhost:5173/register')
  assert.equal(config.isLanding, true)
  assert.equal(config.isAdmin, false)
  const urls = { admin: 'http://admin.localhost:5173/businesses/bakery', storefront: 'http://bakery.localhost:5173' }
  assert.deepEqual(safeBusinessUrls(urls, 'bakery', config), urls)
  assert.equal(safeBusinessUrls({ ...urls, admin: 'https://evil.example' }, 'bakery', config), null)
  assert.equal(createSiteConfig(new URL('http://bakery.localhost:5173')).isLanding, false)
  assert.equal(createSiteConfig(new URL('http://admin.localhost:5173')).isAdmin, true)
})

test('production requires explicit origins and rejects paths, credentials and unsafe protocols', () => {
  assert.throws(() => createSiteConfig(new URL('https://admin.example.com')))
  for (const value of ['javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com/path']) {
    assert.throws(() => createSiteConfig(new URL('https://example.com'), { VITE_STOREFRONT_BASE_URL: value, VITE_ADMIN_BASE_URL: 'https://admin.example.com' }))
  }
  const prod = createSiteConfig(new URL('https://admin.example.com'), { VITE_STOREFRONT_BASE_URL: 'https://example.com', VITE_ADMIN_BASE_URL: 'https://admin.example.com' })
  assert.equal(prod.isAdmin, true)
})

test('redirects accept only implemented relative owner routes', () => {
  for (const path of ['https://evil.example', '//evil.example', '/login', '/register', '/businesses/../login', '/businesses/%2f%2fevil.example', ['/businesses/a']]) {
    assert.equal(safeReturnPath(path), '/businesses')
  }
  assert.equal(safeReturnPath('/businesses/my-bakery'), '/businesses/my-bakery')
})

test('registration/login on the root or a storefront moves to admin before session requests', async () => {
  let location
  const guard = createSessionGuard({ restore() { throw new Error('should not run') } }, config, url => { location = url })
  assert.equal(await guard(target()), false)
  assert.equal(location, 'http://admin.localhost:5173/businesses/bakery')
})

test('expired sessions go to login and valid sessions restore protected routes', async () => {
  const admin = { ...config, isAdmin: true }
  const guestGuard = createSessionGuard({ restore: async () => null }, admin)
  assert.deepEqual(await guestGuard(target({ meta: { admin: true, requiresAuth: true } })), { name: 'login', query: { reason: 'expired', redirect: '/businesses/bakery' } })
  const ownerGuard = createSessionGuard({ restore: async () => ({ id: 'owner' }) }, admin)
  assert.equal(await ownerGuard(target({ meta: { admin: true, requiresAuth: true } })), true)
  assert.equal(await ownerGuard(target({ meta: { admin: true, guestOnly: true }, query: { redirect: '//evil.example' } })), '/businesses')
})

test('unavailable backend does not cause a login redirect loop', async () => {
  const guard = createSessionGuard({ restore: async () => { throw new Error('offline') } }, { ...config, isAdmin: true })
  assert.equal(await guard(target({ meta: { admin: true, guestOnly: true } })), true)
  assert.equal((await guard(target({ meta: { admin: true, requiresAuth: true } }))).query.reason, 'unavailable')
})

test('URL recovery checks only owned pages and handles missing/non-owned business slugs', async () => {
  const pages = [{ items: [{ slug: 'other-owned' }], page_size: 1, total: 2 }, { items: [{ slug: 'bakery', id: 'owned-id' }], page_size: 1, total: 2 }]
  const client = { get: async path => pages[path.includes('page=1&') ? 0 : 1] }
  assert.equal((await findOwnedBusiness('bakery', client)).id, 'owned-id')
  assert.equal(await findOwnedBusiness('foreign', client), null)
})
