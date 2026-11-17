<script setup>
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storefront } from '../services/storefront.js'
import { catalogQuery, formatMoney } from '../services/catalog.js'
import { useStorefrontContext } from '../composables/useStorefrontContext.js'
import { useResource } from '../composables/useResource.js'
import { errorMessage } from '../api/client.js'
import CatalogImage from '../components/CatalogImage.vue'
const route = useRoute()
const { business } = useStorefrontContext()
const { data: product, loading, error, reload } = useResource(
  () => business.value ? `${business.value.slug}:${route.params.productId}` : null,
  signal => storefront.product(route.params.productId, { signal }),
)
const backRoute = computed(() => {
  const query = catalogQuery(route.query, true)
  return { name: 'storefront', query: { ...(query.q ? { q: query.q } : {}), ...(query.page > 1 ? { page: String(query.page) } : {}) } }
})
watch([product, () => route.fullPath], ([value]) => { if (value && business.value) document.title = `${value.name} · ${business.value.name}` }, { flush: 'post' })
</script>
<template><RouterLink class="back-link" :to="backRoute">← All products</RouterLink><p v-if="loading" class="loading-state" role="status">Opening product…</p><section v-else-if="error" class="empty-state"><p class="eyebrow">PRODUCT UNAVAILABLE</p><h1>{{ error.status === 404 ? 'This product isn’t available.' : 'A little interruption.' }}</h1><p role="alert">{{ error.status === 404 ? 'It may have been removed or is no longer published. Explore our other products.' : errorMessage(error) }}</p><button v-if="error.status !== 404" class="button button-secondary" @click="reload">Try again</button><RouterLink v-else class="button" :to="backRoute">Explore our products →</RouterLink></section><article v-else-if="product" class="storefront-product-detail"><CatalogImage :src="product.image_url" :alt="product.name" eager /><div><p class="eyebrow">{{ business.name }}</p><h1>{{ product.name }}</h1><p class="detail-price">{{ formatMoney(product.price, business.currency) }}</p><p v-if="product.description" class="detail-description preserve-lines">{{ product.description }}</p><a v-if="business.contact_email || business.contact_phone || business.address" class="button button-secondary" href="#contact-heading">Contact the business ↓</a></div></article></template>
