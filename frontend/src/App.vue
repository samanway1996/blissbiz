<script setup>
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ownerSession } from './composables/useOwnerSession.js'
import { safeReturnPath } from './config/site.js'
const route = useRoute()
const router = useRouter()
watch(() => ownerSession.state.owner, (owner, previous) => {
  if (!owner && previous && route.meta.requiresAuth) {
    router.replace({ name: 'login', query: { reason: 'expired', redirect: safeReturnPath(route.path) } })
  }
})
</script>
<template><a class="skip-link" href="#main-content">Skip to content</a><RouterView /></template>
