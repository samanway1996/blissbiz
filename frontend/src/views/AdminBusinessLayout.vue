<script setup>
import { computed, provide, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { api, errorMessage } from '../api/client.js'
import { findOwnedBusiness } from '../services/businesses.js'
import { safeBusinessUrls } from '../config/site.js'
import { site } from '../composables/useSite.js'
import { useOwnerSession } from '../composables/useOwnerSession.js'
import { useResource } from '../composables/useResource.js'
import { businessContextKey } from '../composables/useBusinessContext.js'
import CatalogImage from '../components/CatalogImage.vue'
const route = useRoute()
const router = useRouter()
const session = useOwnerSession()
const busy = ref(false)
const logoutFailure = ref('')
const loggingOut = ref(false)
const { data: business, loading, error, reload } = useResource(
  () => session.state.owner?.id ? `${route.params.slug}:${session.state.owner.id}` : null,
  signal => findOwnedBusiness(route.params.slug, api, { signal }),
)
const urls = computed(() => business.value ? safeBusinessUrls(business.value.urls, business.value.slug, site) : null)
const productsRoute = computed(() => ({ name: 'products', params: { slug: route.params.slug } }))
const settingsRoute = computed(() => ({ name: 'business-settings', params: { slug: route.params.slug } }))
function updateBusiness(value) { if (business.value?.id === value.id) business.value = value }
provide(businessContextKey, { business, busy, updateBusiness })
const canLeave = () => !busy.value || !session.state.owner
onBeforeRouteLeave(canLeave)
onBeforeRouteUpdate(canLeave)
watch(() => session.state.owner?.id, () => { busy.value = false })
async function logout() {
  if (busy.value || loggingOut.value) return
  loggingOut.value = true
  logoutFailure.value = ''
  try { await session.logout(); await router.replace('/login') }
  catch (failure) { logoutFailure.value = errorMessage(failure) }
  finally { loggingOut.value = false }
}
</script>
<template><div class="admin-app"><header class="admin-header"><RouterLink class="brand" to="/businesses"><span class="brand-mark" aria-hidden="true">b</span>blissbiz.</RouterLink><div class="header-actions"><a v-if="urls" class="text-link" :href="urls.storefront" target="_blank" rel="noopener">View storefront ↗</a><button class="button button-secondary button-small" :disabled="busy || loggingOut" @click="logout">{{ loggingOut ? 'Logging out…' : 'Log out' }}</button></div></header><p v-if="logoutFailure" class="notice notice-error" role="alert">{{ logoutFailure }}</p><main v-if="loading" id="main-content" tabindex="-1" class="owner-page" role="status">Loading your business…</main><main v-else-if="error || !business" id="main-content" tabindex="-1" class="owner-page"><h1>Business unavailable.</h1><p class="notice notice-error" role="alert">{{ error ? errorMessage(error) : 'This business could not be found in your account.' }}</p><div class="actions"><button v-if="error" class="button button-secondary" @click="reload">Try again</button><RouterLink class="button" to="/businesses">Your businesses</RouterLink></div></main><div v-else class="admin-workspace"><aside class="admin-sidebar"><div class="admin-business-name"><CatalogImage :src="business.logo_url" :alt="business.name" /><div><strong>{{ business.name }}</strong><small>Your owner dashboard</small></div></div><nav aria-label="Business navigation"><RouterLink :to="productsRoute" :aria-disabled="busy" @click="busy && $event.preventDefault()">Products</RouterLink><RouterLink :to="settingsRoute" :aria-disabled="busy" @click="busy && $event.preventDefault()">Business settings</RouterLink><RouterLink to="/businesses" :aria-disabled="busy" @click="busy && $event.preventDefault()">Your businesses</RouterLink></nav><p class="sidebar-note">Make a little update.<br>Keep your business growing.</p></aside><main id="main-content" tabindex="-1" class="admin-content"><RouterView :key="business.id" /></main></div></div></template>
