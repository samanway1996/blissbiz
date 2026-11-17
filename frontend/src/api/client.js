export class ApiError extends Error {
  constructor(message, { status = 0, code = 'network_error', fields = {}, retryAfter = null } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields || {}
    this.retryAfter = retryAfter
  }
}

export class ApiClient {
  constructor(fetcher = (...args) => fetch(...args)) {
    this.fetcher = fetcher
    this.csrfRequest = null
    this.unauthorizedListeners = new Set()
  }

  onUnauthorized(listener) {
    this.unauthorizedListeners.add(listener)
    return () => this.unauthorizedListeners.delete(listener)
  }

  async send(path, { method = 'GET', body, signal, headers = {} } = {}) {
    if (!path.startsWith('/') || path.startsWith('//')) throw new Error('Use a relative API path.')
    let response
    try {
      response = await this.fetcher(`/api${path}`, {
        method,
        body,
        headers: { Accept: 'application/json', ...headers },
        credentials: 'same-origin',
        cache: 'no-store',
        signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(10000)]) : AbortSignal.timeout(10000),
      })
    } catch (error) {
      if (signal?.aborted) throw error
      throw new ApiError(error.name === 'TimeoutError'
        ? 'The request timed out. Check your connection before trying again.'
        : 'Unable to reach the server. Check your connection and try again.')
    }

    let data = null
    if (response.status !== 204) {
      try { data = await response.json() } catch {
        if (response.ok) throw new ApiError('The server returned an unexpected response.', { code: 'invalid_response' })
      }
    }
    if (!response.ok) {
      const detail = data?.error
      const error = new ApiError(detail?.message || `Request failed (${response.status}). Please try again.`, {
        status: response.status,
        code: detail?.code || 'request_failed',
        fields: detail?.fields,
        retryAfter: response.headers.get('Retry-After'),
      })
      if (error.status === 401 && error.code === 'authentication_required') {
        this.unauthorizedListeners.forEach(listener => listener())
      }
      throw error
    }
    return data
  }

  async csrf() {
    // Recheck before each mutation: cookies can rotate in another tab or expire.
    // Share only an in-flight bootstrap; never persist credentials or tokens.
    if (!this.csrfRequest) {
      this.csrfRequest = this.send('/v1/auth/csrf').finally(() => { this.csrfRequest = null })
    }
    const result = await this.csrfRequest
    if (!result?.csrf_token) throw new ApiError('Unable to verify this request. Please try again.')
    return result.csrf_token
  }

  async request(path, { method = 'GET', body, signal } = {}) {
    method = method.toUpperCase()
    const headers = {}
    if (!['GET', 'HEAD'].includes(method)) headers['X-CSRF-Token'] = await this.csrf()
    const multipart = typeof FormData !== 'undefined' && body instanceof FormData
    if (body !== undefined && !multipart) headers['Content-Type'] = 'application/json'
    // A failed mutation is never automatically replayed: its commit may be uncertain.
    return this.send(path, { method, signal, headers, body: body === undefined || multipart ? body : JSON.stringify(body) })
  }

  get(path, options) { return this.request(path, options) }
  post(path, body) { return this.request(path, { method: 'POST', body }) }
  patch(path, body) { return this.request(path, { method: 'PATCH', body }) }
  put(path, body) { return this.request(path, { method: 'PUT', body }) }
  delete(path) { return this.request(path, { method: 'DELETE' }) }
}

export const api = new ApiClient()
export const getJson = (path, options) => api.get(path, options)

export function errorMessage(error) {
  if (error.status === 429) return `${error.message} Try again${error.retryAfter ? ` in ${error.retryAfter} seconds` : ' later'}.`
  if (error.code === 'csrf_rejected') return 'Your request could not be verified. Your session may have changed in another tab. Please try again.'
  return error.message || 'Something went wrong. Please try again.'
}
