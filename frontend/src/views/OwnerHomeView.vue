<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import BusinessLinks from '../components/BusinessLinks.vue'
import PagePagination from '../components/PagePagination.vue'
import { useOwnerSession } from '../composables/useOwnerSession.js'
import { useResource } from '../composables/useResource.js'
import { catalog, catalogQuery } from '../services/catalog.js'
import { errorMessage } from '../api/client.js'
const session = useOwnerSession()
const route = useRoute()
const router = useRouter()
const logoutFailure = ref('')
const loggingOut = ref(false)
const page = computed(() => catalogQuery(route.query).page)
const pageSize = 12
const { data, loading, error, reload } = useResource(
  () => session.state.owner?.id ? `${session.state.owner.id}:${page.value}` : null,
  signal => catalog.listBusinesses({ page: page.value, page_size: pageSize }, { signal }),
)
function navigate(value) { router.push({ name: 'owner-home', query: value > 1 ? { page: String(value) } : {} }) }
watch(data, value => { if (value && page.value > 1 && !value.items.length) navigate(Math.max(1, Math.ceil(value.total / pageSize))) })
async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutFailure.value = ''
  try { await session.logout(); await router.replace('/login') }
  catch (failure) { logoutFailure.value = errorMessage(failure) }
  finally { loggingOut.value = false }
}
</script>
<template><SiteHeader simple /><main id="main-content" tabindex="-1" class="owner-page"><div class="page-heading"><div><p class="eyebrow">YOUR OWNER SPACE</p><h1>Your businesses</h1><p class="section-description">Welcome, {{ session.state.owner?.full_name }}. Choose your business to manage its products and website.</p></div><button class="button button-secondary" :disabled="loggingOut" @click="logout">{{ loggingOut ? 'Logging out…' : 'Log out' }}</button></div><p v-if="logoutFailure" role="alert" class="notice notice-error">{{ logoutFailure }}</p><p v-if="loading" role="status">Loading your businesses…</p><div v-else-if="error" class="notice notice-error" role="alert"><p>{{ errorMessage(error) }}</p><button class="button button-secondary" @click="reload">Try again</button></div><template v-else-if="data"><section v-for="business in data.items" :key="business.id" class="owner-business"><span class="badge">Your business</span><h2>{{ business.name }}</h2><p v-if="business.description" class="section-description">{{ business.description }}</p><RouterLink class="button" :to="{ name: 'products', params: { slug: business.slug } }">Manage products →</RouterLink><BusinessLinks :business="business" :urls="business.urls" /></section><p v-if="!data.items.length" class="notice">No business is linked to this account. Please check that you used the correct email address.</p><PagePagination :page="page" :page-size="pageSize" :total="data.total" singular="business" plural="businesses" @change="navigate" /></template></main></template>
