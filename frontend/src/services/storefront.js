import { ApiClient } from '../api/client.js'
import { queryString } from './catalog.js'

// Public requests deliberately omit cookies, even on an unexpected browser configuration.
export const publicApi = new ApiClient(undefined, { credentials: 'omit' })
export class StorefrontService {
  constructor(client = publicApi) { this.client = client }
  profile(options) { return this.client.get('/v1/storefront', options) }
  products(query, options) {
    const { q, page, page_size } = query
    return this.client.get(`/v1/storefront/products${queryString({ q, page, page_size })}`, options)
  }
  product(id, options) { return this.client.get(`/v1/storefront/products/${encodeURIComponent(id)}`, options) }
}
export const storefront = new StorefrontService()
