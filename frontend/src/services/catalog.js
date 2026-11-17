import { api } from '../api/client.js'

export function catalogQuery(query = {}, publicOnly = false) {
  const text = typeof query.q === 'string' ? query.q.trim().slice(0, 150) : ''
  const raw = typeof query.page === 'string' ? query.page : ''
  const page = /^[1-9][0-9]{0,6}$/.test(raw) && Number(raw) <= 1000000 ? Number(raw) : 1
  const status = !publicOnly && ['draft', 'published'].includes(query.status) ? query.status : ''
  return { q: text, page, page_size: 12, status }
}

export function queryString(query = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== '' && value !== undefined && value !== null) params.set(key, String(value))
  }
  const encoded = params.toString()
  return encoded ? `?${encoded}` : ''
}

export function validPrice(value) {
  return typeof value === 'string' && /^[0-9]{1,10}(?:\.[0-9]{1,2})?$/.test(value)
}

export function formatMoney(value, currency = 'INR') {
  if (!validPrice(value)) return '—'
  const [integer, decimal = ''] = value.split('.')
  return `${currency === 'INR' ? '₹' : `${currency} `}${BigInt(integer).toLocaleString('en-IN')}.${decimal.padEnd(2, '0')}`
}

export const businessFields = ['name', 'description', 'contact_email', 'contact_phone', 'address']
export const productFields = ['name', 'description', 'price', 'status']

export function editableValues(record, fields) {
  return Object.fromEntries(fields.map(field => [field, record?.[field] ?? '']))
}

export function changedFields(form, original, fields) {
  const result = {}
  for (const field of fields) {
    const value = typeof form[field] === 'string' ? form[field].trim() : form[field]
    const normalized = value === '' && !['name', 'price', 'status'].includes(field) ? null : value
    if (normalized !== (original[field] ?? null)) result[field] = normalized
  }
  return result
}

export class CatalogService {
  constructor(client = api) { this.client = client }
  businessPath(id) { return `/v1/admin/businesses/${encodeURIComponent(id)}` }
  productPath(businessId, productId) {
    const base = `${this.businessPath(businessId)}/products`
    return productId ? `${base}/${encodeURIComponent(productId)}` : base
  }
  listBusinesses(query = {}, options) { return this.client.get(`/v1/admin/businesses${queryString(query)}`, options) }
  getBusiness(id, options) { return this.client.get(this.businessPath(id), options) }
  updateBusiness(id, changes) { return this.client.patch(this.businessPath(id), changes) }
  listProducts(id, query, options) { return this.client.get(`${this.productPath(id)}${queryString(query)}`, options) }
  getProduct(id, productId, options) { return this.client.get(this.productPath(id, productId), options) }
  createProduct(id, data) { return this.client.post(this.productPath(id), data) }
  updateProduct(id, productId, changes) { return this.client.patch(this.productPath(id, productId), changes) }
  deleteProduct(id, productId) { return this.client.delete(this.productPath(id, productId)) }
  uploadImage(path, file) {
    const form = new FormData()
    form.append('file', file)
    return this.client.put(path, form)
  }
  uploadLogo(id, file) { return this.uploadImage(`${this.businessPath(id)}/logo`, file) }
  removeLogo(id) { return this.client.delete(`${this.businessPath(id)}/logo`) }
  uploadProductImage(id, productId, file) { return this.uploadImage(`${this.productPath(id, productId)}/image`, file) }
  removeProductImage(id, productId) { return this.client.delete(`${this.productPath(id, productId)}/image`) }
}

export const catalog = new CatalogService()
