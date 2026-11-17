import test from 'node:test'
import assert from 'node:assert/strict'
import { setTimeout as wait } from 'node:timers/promises'
import { createSlugAvailability, normalizeSlug, validSlug } from '../src/services/slugAvailability.js'

async function until(predicate) {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await wait(5) }
  assert.fail('Expected async state was not reached')
}

test('slug normalization and shape follow the backend contract', () => {
  assert.equal(normalizeSlug(' My-Bakery '), 'my-bakery')
  for (const slug of ['', '-bakery', 'bakery-', 'my--bakery', 'two.words', 'éclair', 'a'.repeat(64)]) assert.equal(validSlug(slug), false)
  for (const slug of ['a', 'my-bakery', 'bakery2', 'a'.repeat(63)]) assert.equal(validSlug(slug), true)
})

test('a delayed old availability response cannot overwrite the latest input', async () => {
  const pending = new Map()
  let state
  const checker = createSlugAvailability({ get: path => new Promise(resolve => { pending.set(path.split('/')[3], resolve) }) }, value => { state = value }, 0)
  checker.check('old')
  await until(() => pending.has('old'))
  checker.check('new')
  await until(() => pending.has('new'))
  pending.get('new')({ available: false })
  await until(() => state.status === 'unavailable')
  pending.get('old')({ available: true })
  await wait(0)
  assert.deepEqual(state, { status: 'unavailable', slug: 'new' })
  checker.cancel()
})

test('clearing input and unmount cancellation discard pending checks', async () => {
  let resolve
  let state
  const checker = createSlugAvailability({ get: () => new Promise(done => { resolve = done }) }, value => { state = value }, 0)
  checker.check('bakery')
  await until(() => resolve)
  checker.check('')
  resolve({ available: true })
  await wait(0)
  assert.equal(state.status, 'idle')
  checker.check('another')
  checker.cancel()
  await wait(0)
  assert.equal(state.status, 'checking')
})

test('availability failures are recoverable and malformed slugs never reach the API', async () => {
  let requests = 0
  let state
  const checker = createSlugAvailability({ get: async () => { requests++; throw new Error('offline') } }, value => { state = value }, 0)
  checker.check('bad--slug')
  await wait(0)
  assert.equal(state.status, 'invalid')
  assert.equal(requests, 0)
  checker.check('bakery')
  await until(() => state.status === 'error')
  assert.equal(requests, 1)
  checker.cancel()
})
