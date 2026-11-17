<script setup>
import { computed, ref, watch } from 'vue'
import { safeMediaUrl } from '../services/images.js'
const props = defineProps({ src: String, alt: { type: String, default: '' }, eager: Boolean })
const failed = ref(false)
const source = computed(() => safeMediaUrl(props.src))
watch(() => props.src, () => { failed.value = false })
</script>
<template>
  <div class="catalog-image"><img v-if="source && !failed" :src="source" :alt="alt" :loading="eager ? 'eager' : 'lazy'" decoding="async" @error="failed = true"><span v-else class="image-placeholder" role="img" :aria-label="`${alt || 'Product'} — no image available`">{{ alt?.slice(0, 1).toUpperCase() || '◇' }}</span></div>
</template>
