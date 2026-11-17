<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storefront } from '../services/storefront.js'
import { catalogQuery, formatMoney } from '../services/catalog.js'
import { useStorefrontContext } from '../composables/useStorefrontContext.js'
import { useResource } from '../composables/useResource.js'
import { errorMessage } from '../api/client.js'
import CatalogImage from '../components/CatalogImage.vue'
import PagePagination from '../components/PagePagination.vue'
const route = useRoute()
const router = useRouter()
const { business } = useStorefrontContext()
const query = computed(() => catalogQuery(route.query, true))
const search = ref(query.value.q)
watch(query, value => { search.value = value.q })
const { data, loading, error, reload } = useResource(
  () => business.value ? `${business.value.slug}:${query.value.q}:${query.value.page}` : null,
  signal => storefront.products(query.value, { signal }),
)
function navigate(page = 1, q = search.value.trim()) {
  router.push({ name: 'storefront', query: { ...(q ? { q } : {}), ...(page > 1 ? { page: String(page) } : {}) } })
}
const currentQuery = computed(() => ({ ...(query.value.q ? { q: query.value.q } : {}), ...(query.value.page > 1 ? { page: String(query.value.page) } : {}) }))
watch(data, value => { if (value && query.value.page > 1 && !value.items.length) navigate(Math.max(1, Math.ceil(value.total / query.value.page_size)), query.value.q) })
watch([() => business.value?.name, () => route.fullPath], ([name]) => { if (name) document.title = `${name} · Our products` }, { immediate: true, flush: 'post' })
</script>
<template><section class="storefront-hero"><p class="eyebrow">WELCOME TO {{ business.name }}</p><h1>A little something<br><em>you’ll love.</em></h1><p v-if="business.description" class="storefront-description preserve-lines">{{ business.description }}</p></section><section aria-labelledby="catalog-heading"><div class="storefront-catalog-heading"><div><p class="eyebrow">TAKE A LOOK AROUND</p><h2 id="catalog-heading">Our products</h2></div><form class="storefront-search" role="search" @submit.prevent="navigate()"><label class="sr-only" for="storefront-search">Search our products</label><input id="storefront-search" v-model="search" type="search" maxlength="150" placeholder="Search our products…"><button class="button button-secondary" type="submit">Search</button><button v-if="query.q" class="button button-secondary" type="button" @click="navigate(1, '')">Clear</button></form></div><p v-if="loading" class="loading-state" role="status">Finding our products…</p><div v-else-if="error" class="notice notice-error" role="alert"><p>{{ errorMessage(error) }}</p><button class="button button-secondary" @click="reload">Try again</button></div><template v-else-if="data"><div v-if="data.items.length" class="storefront-grid"><article v-for="product in data.items" :key="product.id" class="storefront-card"><RouterLink :to="{ name: 'storefront-product', params: { productId: product.id }, query: currentQuery }" class="product-card-link"><CatalogImage :src="product.image_url" :alt="product.name" /><div class="storefront-card-copy"><h3>{{ product.name }}</h3><p class="storefront-price">{{ formatMoney(product.price, business.currency) }}</p><span class="product-card-action">View product <span aria-hidden="true">→</span></span></div></RouterLink></article></div><section v-else class="empty-state"><span class="empty-mark" aria-hidden="true">◇</span><h2>{{ query.q ? 'Nothing matches just yet.' : 'Something good is on its way.' }}</h2><p>{{ query.q ? 'Try another search or clear your search to see everything.' : 'Our products will appear here when they’re ready. Check back soon.' }}</p></section><PagePagination :page="query.page" :page-size="query.page_size" :total="data.total" @change="navigate($event, query.q)" /></template></section></template>
