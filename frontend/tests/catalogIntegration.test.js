import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createApiHarness, hasBackend } from './support/apiHarness.js'
import { createOwnerSession } from '../src/composables/useOwnerSession.js'
import { CatalogService } from '../src/services/catalog.js'
import { StorefrontService } from '../src/services/storefront.js'

const payload = slug => ({ owner: { full_name: 'Disposable Owner', email: `${slug}@example.com`, password: 'a disposable review passphrase' }, business: { name: slug, slug, currency: 'INR' } })

test('two real owners: settings, CRUD, image lifecycle, publication, public pagination and tenant boundaries', { skip: !hasBackend, timeout: 30000 }, async () => {
  const harness = createApiHarness()
  const ownerA = harness.client('owner-a')
  const ownerB = harness.client('owner-b')
  const sessionA = createOwnerSession(ownerA)
  const sessionB = createOwnerSession(ownerB)
  const adminA = new CatalogService(ownerA)
  const adminB = new CatalogService(ownerB)
  const publicA = new StorefrontService(harness.client('visitor', 'http://bakery-a.localhost:5173', 'omit'))
  const publicB = new StorefrontService(harness.client('visitor', 'http://crafts-b.localhost:5173', 'omit'))
  const picture = new File([await readFile(new URL('./fixtures/product.png', import.meta.url))], 'product.png', { type: 'image/png' })
  const replacement = new File([await readFile(new URL('./fixtures/replacement.png', import.meta.url))], 'replacement.png', { type: 'image/png' })
  try {
    const a = (await sessionA.register(payload('bakery-a'))).business
    const b = (await sessionB.register(payload('crafts-b'))).business
    assert.equal((await publicA.profile()).contact_email, null)
    const settings = await adminA.updateBusiness(a.id, { name: 'Fresh Bakery', description: 'Fresh bread <script>never execute</script>', contact_email: 'shop@example.com', contact_phone: '+919000000000', address: '12 Market Road' })
    assert.equal(settings.name, 'Fresh Bakery')
    const profile = await publicA.profile()
    assert.equal(profile.contact_email, 'shop@example.com')
    assert.equal(profile.owner_id, undefined)
    assert.equal(profile.email, undefined)
    await assert.rejects(adminB.getBusiness(a.id), error => error.status === 404)
    await assert.rejects(adminB.updateBusiness(a.id, { name: 'stolen' }), error => error.status === 404)
    const draft = await adminA.createProduct(a.id, { name: 'Sourdough', description: 'Slow fermented', price: '180.00' })
    assert.equal(draft.status, 'draft')
    assert.equal(draft.price, '180.00')
    assert.equal((await publicA.products({ page: 1, page_size: 12 })).total, 0)
    await assert.rejects(publicA.product(draft.id), error => error.status === 404)
    const uploaded = await adminA.uploadProductImage(a.id, draft.id, picture)
    assert.match(uploaded.image_url, /^\/media\/businesses\//)
    const firstPath = uploaded.image_url
    assert.equal((await harness.raw(firstPath, { credentials: 'omit' }, 'visitor', 'http://bakery-a.localhost:5173')).status, 200)
    await assert.rejects(adminA.uploadProductImage(a.id, draft.id, new File(['bad image'], 'bad.png', { type: 'image/png' })), error => error.status === 415)
    assert.equal((await adminA.getProduct(a.id, draft.id)).image_url, firstPath)
    const replaced = await adminA.uploadProductImage(a.id, draft.id, replacement)
    assert.notEqual(replaced.image_url, firstPath)
    assert.equal((await harness.raw(firstPath, {}, 'visitor', 'http://bakery-a.localhost:5173')).status, 404)
    const published = await adminA.updateProduct(a.id, draft.id, { status: 'published' })
    assert.equal(published.description, 'Slow fermented')
    assert.equal((await publicA.product(draft.id)).price, '180.00')
    await assert.rejects(publicB.product(draft.id), error => error.status === 404)
    await assert.rejects(adminB.getProduct(a.id, draft.id), error => error.status === 404)
    await assert.rejects(adminB.updateProduct(b.id, draft.id, { name: 'stolen' }), error => error.status === 404)
    await assert.rejects(adminB.deleteProduct(a.id, draft.id), error => error.status === 404)
    await assert.rejects(adminB.uploadProductImage(a.id, draft.id, picture), error => error.status === 404)
    const logo = await adminA.uploadLogo(a.id, picture)
    assert.equal((await publicA.profile()).logo_url, logo.logo_url)
    await assert.rejects(adminB.removeLogo(a.id), error => error.status === 404)
    await adminA.removeLogo(a.id)
    assert.equal((await publicA.profile()).logo_url, null)
    for (let index = 0; index < 12; index++) {
      const product = await adminA.createProduct(a.id, { name: `Bread ${index}`, price: '9999999999.99' })
      await adminA.updateProduct(a.id, product.id, { status: 'published' })
    }
    const page = await publicA.products({ page: 1, page_size: 12 })
    assert.equal(page.total, 13)
    assert.equal(page.items.length, 12)
    assert.equal((await publicA.products({ page: 2, page_size: 12 })).items.length, 1)
    assert.equal((await publicA.products({ q: 'Sourdough', page: 1, page_size: 12 })).total, 1)
    assert.equal((await adminA.listProducts(a.id, { status: 'draft', page: 1, page_size: 12 })).total, 0)
    const foreign = await adminB.createProduct(b.id, { name: 'Handmade mug', price: '250.00' })
    await adminB.updateProduct(b.id, foreign.id, { status: 'published' })
    assert.equal((await publicB.products({ page: 1, page_size: 12 })).total, 1)
    assert.equal((await publicB.products({ q: 'Sourdough', page: 1, page_size: 12 })).total, 0)
    await adminA.updateProduct(a.id, draft.id, { status: 'draft', description: null })
    await assert.rejects(publicA.product(draft.id), error => error.status === 404)
    await adminA.removeProductImage(a.id, draft.id)
    assert.equal((await adminA.getProduct(a.id, draft.id)).image_url, null)
    await adminA.deleteProduct(a.id, draft.id)
    await assert.rejects(adminA.getProduct(a.id, draft.id), error => error.status === 404)
    assert.equal((await publicB.product(foreign.id)).name, 'Handmade mug')
    const unknown = new StorefrontService(harness.client('visitor', 'http://unknown.localhost:5173', 'omit'))
    await assert.rejects(unknown.profile(), error => error.status === 404)
    await sessionA.logout()
    await assert.rejects(adminA.listProducts(a.id, { page: 1 }), error => error.status === 401)
  } finally { await harness.close() }
})
