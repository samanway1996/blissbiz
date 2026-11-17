<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import BusinessLinks from '../components/BusinessLinks.vue'
import { useOwnerSession } from '../composables/useOwnerSession.js'
import { findOwnedBusiness } from '../services/businesses.js'
import { errorMessage } from '../api/client.js'
const route = useRoute()
const session = useOwnerSession()
const result = ref(null)
const loading = ref(true)
const failure = ref('')
const destination = computed(() => `/businesses/${encodeURIComponent(route.params.slug)}`)
let requestId = 0
async function load() {
  const current = ++requestId
  const slug = route.params.slug
  loading.value = true
  failure.value = ''
  result.value = null
  try {
    const created = session.state.registration
    if (created?.business.slug === slug) result.value = created
    else {
      const business = await findOwnedBusiness(slug)
      if (current !== requestId) return
      if (business) result.value = { business, urls: business.urls }
      else failure.value = 'This business could not be found in your account.'
    }
  } catch (error) { if (current === requestId) failure.value = errorMessage(error) }
  finally { if (current === requestId) loading.value = false }
}
onMounted(load)
watch(() => route.params.slug, load)
onBeforeUnmount(() => { requestId += 1 })
</script>

<template>
  <SiteHeader simple />
  <main id="main-content" tabindex="-1" class="center-page"><section class="success-panel">
    <p v-if="loading" role="status">Getting your business links…</p>
    <div v-else-if="failure" class="notice notice-error" role="alert"><p>{{ failure }}</p><button class="button button-secondary" @click="load">Try again</button><RouterLink class="inline-link" to="/businesses">Your account</RouterLink></div>
    <template v-else-if="result"><span class="success-mark" aria-hidden="true">✓</span><p class="eyebrow">HERE’S TO YOUR NEXT CHAPTER</p><h1>Your business<br>has a home online.</h1><p class="section-description">Welcome, {{ result.business.name }}. Keep these links handy.</p><BusinessLinks :business="result.business" :urls="result.urls" /><RouterLink class="button" :to="destination">Go to your owner space →</RouterLink><p class="field-hint">Your owner space is ready. Product management and the customer storefront are coming next.</p></template>
  </section></main>
</template>
