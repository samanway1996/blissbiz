<script setup>
import { computed, provide, watch } from 'vue'
import { ApiError, errorMessage } from '../api/client.js'
import { storefront } from '../services/storefront.js'
import { site } from '../composables/useSite.js'
import { useResource } from '../composables/useResource.js'
import { storefrontContextKey } from '../composables/useStorefrontContext.js'
import CatalogImage from '../components/CatalogImage.vue'
const { data: business, loading, error, reload } = useResource(() => site.storefrontSlug, async signal => {
  const result = await storefront.profile({ signal })
  if (result.slug !== site.storefrontSlug) throw new ApiError('This storefront could not be found.', { status: 404 })
  return result
})
provide(storefrontContextKey, { business })
const phoneLink = computed(() => /[0-9]/.test(business.value?.contact_phone || '') ? `tel:${business.value.contact_phone.replace(/[^0-9+]/g, '')}` : null)
const hasContact = computed(() => business.value && (business.value.contact_email || business.value.contact_phone || business.value.address))
watch(business, value => { if (value) document.title = `${value.name} · Our products` })
</script>
<template><main v-if="loading" id="main-content" tabindex="-1" class="center-page" role="status">Opening this storefront…</main><main v-else-if="error" id="main-content" tabindex="-1" class="center-page"><p class="eyebrow">STOREFRONT UNAVAILABLE</p><h1>{{ error.status === 404 ? 'We couldn’t find this business.' : 'A little interruption.' }}</h1><p class="section-description" role="alert">{{ error.status === 404 ? 'Check the website address and try again.' : errorMessage(error) }}</p><button v-if="error.status !== 404" class="button button-secondary" @click="reload">Try again</button><a v-else class="button" :href="site.storefrontOrigin">Discover BlissBiz →</a></main><div v-else-if="business" class="storefront-app"><header class="storefront-header"><RouterLink class="storefront-brand" :to="{ name: 'storefront' }"><CatalogImage :src="business.logo_url" :alt="`${business.name} logo`" eager /><span>{{ business.name }}</span></RouterLink><RouterLink class="text-link" :to="{ name: 'storefront' }">Our products</RouterLink></header><main id="main-content" tabindex="-1" class="storefront-content"><RouterView /></main><footer class="storefront-footer"><section v-if="hasContact" class="storefront-contact" aria-labelledby="contact-heading"><div><p class="eyebrow">SAY HELLO</p><h2 id="contact-heading">Get in touch.</h2><p>{{ business.name }}</p></div><div class="contact-details"><a v-if="business.contact_email" :href="`mailto:${business.contact_email}`">{{ business.contact_email }}</a><a v-if="phoneLink" :href="phoneLink">{{ business.contact_phone }}</a><p v-else-if="business.contact_phone">{{ business.contact_phone }}</p><p v-if="business.address" class="preserve-lines">{{ business.address }}</p></div></section><div class="storefront-credit"><span>{{ business.name }}</span><a :href="site.storefrontOrigin">Made possible with <strong>blissbiz.</strong></a></div></footer></div></template>
