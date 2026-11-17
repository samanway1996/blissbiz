<script setup>
import { onMounted, ref } from 'vue'
import { getJson } from '../api/client'

const apiStatus = ref('Checking…')
const databaseStatus = ref('Checking…')
const checking = ref(false)

async function checkConnections() {
  checking.value = true
  const results = await Promise.allSettled([getJson('/health'), getJson('/ready')])
  apiStatus.value = results[0].status === 'fulfilled' ? 'Connected' : 'Unavailable — start the backend'
  databaseStatus.value = results[1].status === 'fulfilled' ? 'Connected' : 'Unavailable — check backend and MySQL'
  checking.value = false
}

onMounted(checkConnections)
</script>

<template>
  <main id="main-content" tabindex="-1" class="development-page">
    <p class="eyebrow">BLISSBIZ · LOCAL DEVELOPMENT</p>
    <h1>Your workspace starts here.</h1>
    <p>Vue is running. Check the connections below before building your first feature.</p>
    <dl aria-live="polite">
      <div><dt>Vue frontend</dt><dd>Connected</dd></div>
      <div><dt>FastAPI backend</dt><dd>{{ apiStatus }}</dd></div>
      <div><dt>MySQL database</dt><dd>{{ databaseStatus }}</dd></div>
    </dl>
    <div class="actions">
      <button :disabled="checking" @click="checkConnections">{{ checking ? 'Checking…' : 'Check again' }}</button>
      <a href="/api/docs" target="_blank" rel="noopener">Open API documentation ↗</a>
    </div>
  </main>
</template>

