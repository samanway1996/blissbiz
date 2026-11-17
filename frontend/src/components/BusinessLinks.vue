<script setup>
import { computed, ref } from 'vue'
import { safeBusinessUrls } from '../config/site.js'
import { site } from '../composables/useSite.js'
const props = defineProps({ business: { type: Object, required: true }, urls: { type: Object, required: true } })
const urls = computed(() => safeBusinessUrls(props.urls, props.business.slug, site))
const notice = ref('')
async function copy(value) {
  try { await navigator.clipboard.writeText(value); notice.value = 'Link copied.' }
  catch { notice.value = 'Copy is unavailable in this browser. Select and copy the link above.' }
}
</script>

<template>
  <div v-if="urls" class="business-links">
    <div v-for="(url, key) in urls" :key="key" class="business-link-row">
      <div><p class="link-label">{{ key === 'admin' ? 'Your owner dashboard' : 'Your public storefront' }}</p><a :href="url" :target="key === 'storefront' ? '_blank' : undefined" rel="noopener">{{ url }}</a></div>
      <button class="button button-secondary button-small" :aria-label="`Copy ${key} link`" @click="copy(url)">Copy link</button>
    </div>
    <p class="field-hint" aria-live="polite">{{ notice }}</p>
  </div>
  <p v-else role="alert" class="notice notice-error">Business created, but its links do not match this frontend’s domain configuration. Check the frontend and backend base URLs.</p>
</template>
