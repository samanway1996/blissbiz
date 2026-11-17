import { reactive, readonly } from 'vue'
import { api } from '../api/client.js'

export function createOwnerSession(client) {
  const state = reactive({ owner: null, restoring: false, error: null, registration: null })
  let restoreRequest = null
  let revision = 0

  function clear() {
    revision += 1
    state.owner = null
    state.registration = null
  }
  client.onUnauthorized(clear)

  async function restore() {
    if (restoreRequest) return restoreRequest
    const current = revision
    state.restoring = true
    state.error = null
    restoreRequest = (async () => {
      try {
        const owner = await client.get('/v1/auth/me')
        if (current === revision) {
          if (state.owner?.id !== owner.id) state.registration = null
          state.owner = owner
        }
        return state.owner
      } catch (error) {
        if (error.status === 401) { clear(); return null }
        if (current === revision) { state.owner = null; state.error = error }
        throw error
      } finally {
        state.restoring = false
        restoreRequest = null
      }
    })()
    return restoreRequest
  }

  async function login(credentials) {
    const owner = await client.post('/v1/auth/login', credentials)
    revision += 1
    state.owner = owner
    state.registration = null
    state.error = null
    return owner
  }

  async function register(payload) {
    const result = await client.post('/v1/registrations', payload)
    revision += 1
    state.owner = result.owner
    state.registration = result
    state.error = null
    return result
  }

  async function logout() {
    try { await client.post('/v1/auth/logout') } catch (error) {
      if (error.status !== 401) throw error
    }
    clear()
  }

  return { state: readonly(state), restore, login, register, logout, clear }
}

export const ownerSession = createOwnerSession(api)
export const useOwnerSession = () => ownerSession
