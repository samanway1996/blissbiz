<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { catalog, catalogQuery, formatMoney } from '../services/catalog.js'
import { useBusinessContext } from '../composables/useBusinessContext.js'
import { useResource } from '../composables/useResource.js'
import { errorMessage } from '../api/client.js'
import CatalogImage from '../components/CatalogImage.vue'
import PagePagination from '../components/PagePagination.vue'
const route = useRoute()
const router = useRouter()
const { business } = useBusinessContext()
const query = computed(() => catalogQuery(route.query))
const search = ref(query.value.q)
const status = ref(query.value.status)
watch(query, value => { search.value = value.q; status.value = value.status })
const { data, loading, error, reload } = useResource(
  () => business.value ? `${business.value.id}:${query.value.q}:${query.value.status}:${query.value.page}` : null,
  signal => catalog.listProducts(business.value.id, query.value, { signal }),
)
const addRoute = computed(() => ({ name: 'product-create', params: { slug: business.value.slug } }))
function navigate(page = 1, q = search.value.trim(), selectedStatus = status.value) {
  router.push({ name: 'products', params: { slug: business.value.slug }, query: { ...(q ? { q } : {}), ...(selectedStatus ? { status: selectedStatus } : {}), ...(page > 1 ? { page: String(page) } : {}) } })
}
watch(data, value => {
  if (value && query.value.page > 1 && !value.items.length) navigate(Math.max(1, Math.ceil(value.total / query.value.page_size)), query.value.q, query.value.status)
})
</script>
<template><div class="page-heading"><div><p class="eyebrow">YOUR CATALOG</p><h1>Products</h1><p class="section-description">A little collection of what makes your business yours.</p></div><RouterLink class="button" :to="addRoute">+ Add product</RouterLink></div><form class="catalog-controls" role="search" @submit.prevent="navigate()"><div class="search-field"><label for="product-search">Search products</label><input id="product-search" v-model="search" type="search" maxlength="150" placeholder="Search by name or description"></div><div class="status-field"><label for="product-status">Visibility</label><select id="product-status" v-model="status"><option value="">All products</option><option value="draft">Draft</option><option value="published">Published</option></select></div><button class="button button-secondary" type="submit">Search</button><button v-if="query.q || query.status" class="button button-secondary" type="button" @click="navigate(1, '', '')">Clear filters</button></form><p v-if="loading" class="loading-state" role="status">Loading products…</p><div v-else-if="error" class="notice notice-error" role="alert"><p>{{ errorMessage(error) }}</p><button class="button button-secondary" @click="reload">Try again</button></div><template v-else-if="data"><ul v-if="data.items.length" class="product-list"><li v-for="product in data.items" :key="product.id" class="product-row"><div class="product-identity"><CatalogImage :src="product.image_url" :alt="product.name" /><div><h2>{{ product.name }}</h2><p class="product-description">{{ product.description || 'No description added.' }}</p></div></div><strong class="product-price">{{ formatMoney(product.price, business.currency) }}</strong><span class="status-badge" :class="product.status">{{ product.status === 'published' ? 'Published' : 'Draft' }}</span><RouterLink class="button button-secondary button-small" :to="{ name: 'product-edit', params: { slug: business.slug, productId: product.id } }" :aria-label="`Edit ${product.name}`">Edit</RouterLink></li></ul><section v-else class="empty-state"><span class="empty-mark" aria-hidden="true">◇</span><h2>{{ query.q || query.status ? 'No products match.' : 'Your first product starts here.' }}</h2><p>{{ query.q || query.status ? 'Try another search or clear the filters.' : 'Add a photo, a price, and a little description. New products stay in draft until you publish them.' }}</p><RouterLink v-if="!query.q && !query.status" class="button" :to="addRoute">Add your first product →</RouterLink></section><PagePagination :page="query.page" :page-size="query.page_size" :total="data.total" @change="navigate($event, query.q, query.status)" /></template></template>
