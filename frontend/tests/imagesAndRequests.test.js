import test from 'node:test'
import assert from 'node:assert/strict'
import { createImagePreview, imageSelectionError, MAX_IMAGE_BYTES, safeMediaUrl } from '../src/services/images.js'
import { createLatestRequest } from '../src/services/latestRequest.js'

test('image selection rejects empty, oversized, unsupported files before upload', () => {
  assert.match(imageSelectionError({ size: 0, type: 'image/png' }), /non-empty/)
  assert.match(imageSelectionError({ size: MAX_IMAGE_BYTES + 1, type: 'image/png' }), /5 MB/)
  assert.match(imageSelectionError({ size: 10, type: 'image/svg+xml' }), /JPEG, PNG or WebP/)
  assert.equal(imageSelectionError({ size: MAX_IMAGE_BYTES, type: 'image/webp' }), '')
  assert.equal(imageSelectionError({ size: 20, type: '' }), '')
})

test('previews release old object URLs on replacement, cancellation and cleanup', () => {
  const revoked = []
  const previews = createImagePreview({ createObjectURL: file => `blob:${file}`, revokeObjectURL: url => revoked.push(url) })
  assert.equal(previews.select('first'), 'blob:first')
  previews.select('second')
  assert.deepEqual(revoked, ['blob:first'])
  previews.clear()
  previews.clear()
  assert.deepEqual(revoked, ['blob:first', 'blob:second'])
})

test('persisted image URLs must be generated media paths on the same origin', () => {
  assert.equal(safeMediaUrl('/media/businesses/business-a/generated-name.png'), '/media/businesses/business-a/generated-name.png')
  for (const value of ['https://evil.example/image.png', '//evil.example/image.png', '/media/businesses/../secret.png', '/media/businesses/a/evil.svg', '/media/businesses/a/photo.png?redirect=evil', null]) assert.equal(safeMediaUrl(value), '')
})

test('late cross-business results and failures cannot overwrite the new resource', async () => {
  const latest = createLatestRequest()
  const resolvers = []
  const signals = []
  const events = []
  const callbacks = { start: () => events.push('start'), success: value => events.push(value), error: value => events.push(value.message), finish: () => events.push('finish') }
  const first = latest.run(signal => { signals.push(signal); return new Promise(resolve => resolvers.push(resolve)) }, callbacks)
  const second = latest.run(signal => { signals.push(signal); return new Promise(resolve => resolvers.push(resolve)) }, callbacks)
  assert.equal(signals[0].aborted, true)
  resolvers[1]('business-b')
  await second
  resolvers[0]('business-a')
  await first
  assert.deepEqual(events, ['start', 'start', 'business-b', 'finish'])
  const failure = latest.run(() => Promise.reject(new Error('old failure')), callbacks)
  latest.cancel()
  await failure
  assert.ok(!events.includes('old failure'))
})

test('current errors finish loading and cancellation ignores updates after unmount', async () => {
  const latest = createLatestRequest()
  const events = []
  const callbacks = { success: value => events.push(value), error: error => events.push(error.message), finish: () => events.push('finish') }
  await latest.run(async () => { throw new Error('retry available') }, callbacks)
  assert.deepEqual(events, ['retry available', 'finish'])
  let resolve
  const pending = latest.run(() => new Promise(done => { resolve = done }), callbacks)
  latest.cancel()
  resolve('private stale data')
  await pending
  assert.deepEqual(events, ['retry available', 'finish'])
})

test('clearing a business during logout pauses reads before child views unmount', async () => {
  const { effectScope, nextTick, ref } = await import('vue')
  const { useResource } = await import('../src/composables/useResource.js')
  const business = ref({ id: 'business-a' })
  const scope = effectScope()
  const pending = []
  const state = scope.run(() => useResource(
    () => business.value?.id || null,
    signal => new Promise(resolve => pending.push({ id: business.value.id, signal, resolve })),
  ))
  assert.equal(pending.length, 1)
  assert.doesNotThrow(() => { business.value = null })
  assert.equal(pending[0].signal.aborted, true)
  assert.equal(state.loading.value, false)
  pending[0].resolve({ id: 'private-a' })
  await nextTick()
  assert.equal(state.data.value, null)
  business.value = { id: 'business-b' }
  assert.equal(pending.length, 2)
  pending[1].resolve({ id: 'public-b' })
  await nextTick()
  assert.deepEqual(state.data.value, { id: 'public-b' })
  assert.equal(state.loading.value, false)
  business.value = { id: 'business-c' }
  scope.stop()
  assert.equal(pending[2].signal.aborted, true)
  pending[2].resolve({ id: 'after-unmount' })
  await nextTick()
  assert.deepEqual(state.data.value, null)
})
