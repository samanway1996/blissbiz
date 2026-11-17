<script setup>
import { site } from '../composables/useSite.js'
defineProps({ simple: Boolean })
</script>

<template>
  <header class="site-header">
    <a class="brand" :href="site.storefrontOrigin" aria-label="BlissBiz home"><span class="brand-mark" aria-hidden="true">b</span>blissbiz<span class="brand-dot">.</span></a>
    <nav v-if="!simple" class="header-actions" aria-label="Main navigation">
      <a class="text-link" :href="site.adminUrl('/login')">Owner login</a>
      <a class="button button-small" :href="site.adminUrl('/register')">Start a business today <span aria-hidden="true">↗</span></a>
    </nav>
    <span v-else class="header-caption">A little business. A big beginning.</span>
  </header>
</template>
