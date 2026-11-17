<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import BusinessLinks from '../components/BusinessLinks.vue'
import { useOwnerSession } from '../composables/useOwnerSession.js'
import { api, errorMessage } from '../api/client.js'
import { findOwnedBusiness } from '../services/businesses.js'
const session = useOwnerSession()
const route = useRoute()
const router = useRouter()
const businesses = ref([])
const loading = ref(true)
const failure = ref('')
const logoutFailure = ref('')
const loggingOut = ref(false)
let requestId = 0
async function load() {
  const current = ++requestId
  loading.value = true
  failure.value = ''
  businesses.value = []
  try {
    const slug = route.params.slug
    const result = slug ? await findOwnedBusiness(slug) : (await api.get('/v1/admin/businesses?page=1&page_size=100')).items
    if (current !== requestId) return
    businesses.value = slug ? result ? [result] : [] : result
    if (slug && !result) failure.value = 'This business could not be found in your account.'
  } catch (error) { if (current === requestId) failure.value = errorMessage(error) }
  finally { if (current === requestId) loading.value = false }
}
async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  logoutFailure.value = ''
  try { await session.logout(); await router.replace('/login') }
  catch (error) { logoutFailure.value = errorMessage(error) }
  finally { loggingOut.value = false }
}
onMounted(load)
watch(() => route.params.slug, load)
onBeforeUnmount(() => { requestId += 1 })
</script>

<template>
  <SiteHeader simple />
  <main id="main-content" tabindex="-1" class="owner-page"><div class="page-heading"><div><p class="eyebrow">YOUR OWNER SPACE</p><h1>You’re signed in.</h1><p class="section-description">Welcome, {{ session.state.owner?.full_name }}.</p></div><button class="button button-secondary" :disabled="loggingOut" @click="logout">{{ loggingOut ? 'Logging out…' : 'Log out' }}</button></div>
    <p v-if="logoutFailure" role="alert" class="notice notice-error">{{ logoutFailure }}</p>
    <p v-if="loading" role="status">Loading your business…</p>
    <div v-else-if="failure" class="notice notice-error" role="alert"><p>{{ failure }}</p><button class="button button-secondary" @click="load">Try again</button></div>
    <template v-else><section v-for="business in businesses" :key="business.id" class="owner-business"><span class="badge">Your business</span><h2>{{ business.name }}</h2><p v-if="business.description" class="section-description">{{ business.description }}</p><BusinessLinks :business="business" :urls="business.urls" /></section><p v-if="!businesses.length" class="notice">No business is linked to this account. Please check that you used the correct email address.</p></template>
    <div class="next-iteration"><h3>Your foundations are ready.</h3><p>Registration and owner login are available. Business settings and product management are next, followed by the public storefront.</p></div>
  </main>
</template>
