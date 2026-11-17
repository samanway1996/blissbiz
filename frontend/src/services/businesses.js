import { api } from '../api/client.js'

// Resolve a slug through owner-scoped API results; never treat a URL parameter as ownership.
export async function findOwnedBusiness(slug, client = api, options) {
  for (let page = 1; ; page += 1) {
    const result = await client.get(`/v1/admin/businesses?page=${page}&page_size=100`, options)
    const business = result.items.find(item => item.slug === slug)
    if (business) return business
    if (page * result.page_size >= result.total) return null
  }
}
