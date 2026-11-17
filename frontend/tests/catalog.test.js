import test from 'node:test'
import assert from 'node:assert/strict'
import { CatalogService, businessFields, catalogQuery, changedFields, editableValues, formatMoney, productFields, queryString, validPrice } from '../src/services/catalog.js'
import { createSiteConfig, safeReturnPath } from '../src/config/site.js'
import { ApiClient } from '../src/api/client.js'
import { StorefrontService } from '../src/services/storefront.js'

test('catalog route queries ignore malformed pages/statuses and bound searches', () => {
  for (const page of ['0', '-1', '1e2', 'NaN', '1000001', ['2']]) assert.equal(catalogQuery({ page }).page, 1)
  assert.equal(catalogQuery({ page: '1000000' }).page, 1000000)
  assert.deepEqual(catalogQuery({ q: ' cake ', page: '2', status: 'draft' }), { q: 'cake', page: 2, page_size: 12, status: 'draft' })
  assert.equal(catalogQuery({ q: 'a'.repeat(200) }).q.length, 150)
  assert.equal(catalogQuery({ q: ['cake'], status: ['draft'] }).q, '')
  assert.equal(catalogQuery({ status: 'draft' }, true).status, '')
  assert.equal(queryString({ q: 'cake & tea', page: 2, status: '', unused: null }), '?q=cake+%26+tea&page=2')
})

test('prices stay decimal strings including the largest supported value', () => {
  for (const value of [0, 1.99, '', '-1', '1e2', '1.999', '.99', '10000000000.00', ' 2 ']) assert.equal(validPrice(value), false)
  for (const value of ['0', '0.00', '1.9', '9999999999.99']) assert.equal(validPrice(value), true)
  assert.equal(formatMoney('9999999999.99'), '₹9,99,99,99,999.99')
  assert.equal(formatMoney('0'), '₹0.00')
  assert.equal(formatMoney('10.5'), '₹10.50')
  assert.equal(formatMoney('bad'), '—')
})

test('PATCH contains only changed editable fields and explicit null clears optional text', () => {
  const original = { name: 'Bakery', description: 'Fresh bread', contact_email: null, contact_phone: null, address: null, slug: 'immutable', currency: 'INR' }
  const form = { ...editableValues(original, businessFields), name: ' Bakery ', description: ' ', slug: 'changed', currency: 'USD' }
  assert.deepEqual(changedFields(form, original, businessFields), { description: null })
  const product = { name: 'Cake', description: null, price: '499.00', status: 'draft' }
  assert.deepEqual(changedFields({ ...product, status: 'published' }, product, productFields), { status: 'published' })
  assert.deepEqual(changedFields(editableValues(original, businessFields), original, businessFields), {})
})

test('admin catalog service sends tenant-scoped paths and multipart files', async () => {
  const calls = []
  const client = Object.fromEntries(['get', 'post', 'patch', 'put', 'delete'].map(method => [method, async (...args) => { calls.push({ method, args }); return {} }]))
  const service = new CatalogService(client)
  await service.listProducts('business-a', { page: 2, status: 'draft', q: 'cake' })
  await service.createProduct('business-a', { name: 'Cake', price: '499.00' })
  await service.updateProduct('business-a', 'product/a?', { status: 'published' })
  const file = new File(['image'], 'photo.png', { type: 'image/png' })
  await service.uploadProductImage('business-a', 'product-a', file)
  await service.removeProductImage('business-a', 'product-a')
  await service.deleteProduct('business-a', 'product-a')
  await service.uploadLogo('business-a', file)
  await service.removeLogo('business-a')
  assert.equal(calls[0].args[0], '/v1/admin/businesses/business-a/products?page=2&status=draft&q=cake')
  assert.equal(calls[1].args[1].price, '499.00')
  assert.equal(calls[2].args[0], '/v1/admin/businesses/business-a/products/product%2Fa%3F')
  assert.equal(calls[3].args[1].get('file').name, 'photo.png')
  assert.equal(calls[4].args[0], '/v1/admin/businesses/business-a/products/product-a/image')
  assert.equal(calls[5].method, 'delete')
  assert.ok(calls.slice(6).every(call => call.args[0] === '/v1/admin/businesses/business-a/logo'))
})

test('public catalog sends neither draft/business query overrides nor browser credentials', async () => {
  const calls = []
  const publicClient = new ApiClient(async (url, options) => {
    calls.push({ url, ...options })
    return new Response(JSON.stringify({ items: [] }), { headers: { 'Content-Type': 'application/json' } })
  }, { credentials: 'omit' })
  const publicService = new StorefrontService(publicClient)
  await publicService.profile()
  await publicService.products({ q: 'cake', page: 1, page_size: 12, status: 'draft', business_id: 'foreign' })
  await publicService.product('product-a')
  assert.ok(calls.every(call => call.credentials === 'omit' && !call.headers['X-CSRF-Token']))
  assert.equal(calls[1].url, '/api/v1/storefront/products?q=cake&page=1&page_size=12')
  assert.equal(calls[2].url, '/api/v1/storefront/products/product-a')
})

test('public routing recognizes exactly one business label under the configured base', () => {
  assert.equal(createSiteConfig(new URL('http://bakery.localhost:5173')).isStorefront, true)
  for (const host of ['localhost', 'admin.localhost', 'nested.bakery.localhost', 'bakery.localhost.evil.example']) {
    const config = createSiteConfig(new URL(`http://${host}:5173`), { VITE_STOREFRONT_BASE_URL: 'http://localhost:5173', VITE_ADMIN_BASE_URL: 'http://admin.localhost:5173' })
    assert.equal(config.isStorefront, false, host)
  }
  const env = { VITE_STOREFRONT_BASE_URL: 'https://example.com', VITE_ADMIN_BASE_URL: 'https://admin.example.com' }
  assert.equal(createSiteConfig(new URL('https://bakery.example.com'), env).storefrontSlug, 'bakery')
  assert.equal(createSiteConfig(new URL('https://bakery.example.com:444'), env).isStorefront, false)
})

test('session return paths allow nested owner pages without accepting external or arbitrary routes', () => {
  for (const path of ['/businesses/bakery/products', '/businesses/bakery/products/new', '/businesses/bakery/products/opaque-id/edit', '/businesses/bakery/settings']) assert.equal(safeReturnPath(path), path)
  for (const path of ['/businesses/bakery/products/../../login', '/businesses/bakery/products/%2F/edit', '/businesses/bakery/settings?next=//evil.example', '//evil.example']) assert.equal(safeReturnPath(path), '/businesses')
})
