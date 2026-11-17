import { api } from '../api/client.js'

// Used only to recover authoritative URLs after login/refresh. Settings and catalog are F05+.
export async function findOwnedBusiness(slug, client = api) {
  for (let page = 1; ; page += 1) {
    const result = await client.get(`/v1/admin/businesses?page=${page}&page_size=100`)
    const business = result.items.find(item => item.slug === slug)
    if (business) return business
    if (page * result.page_size >= result.total) return null
  }
}
