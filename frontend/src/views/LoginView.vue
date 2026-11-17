<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import FormField from '../components/FormField.vue'
import { errorMessage } from '../api/client.js'
import { safeReturnPath } from '../config/site.js'
import { useOwnerSession } from '../composables/useOwnerSession.js'
const session = useOwnerSession()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const busy = ref(false)
const errors = ref({})
const failure = ref('')
const info = computed(() => route.query.reason === 'unavailable'
  ? 'We couldn’t verify your session. Check the connection and try logging in.'
  : route.query.reason === 'expired' ? 'Please log in to continue. Your session may have expired.' : '')
onBeforeUnmount(() => { password.value = '' })
async function submit() {
  if (busy.value) return
  busy.value = true
  failure.value = ''
  errors.value = {}
  const credentials = { email: email.value.trim(), password: password.value }
  try {
    await session.login(credentials)
    await router.replace(safeReturnPath(route.query.redirect))
  } catch (error) {
    failure.value = errorMessage(error)
    errors.value = error.fields || {}
  } finally {
    password.value = ''
    credentials.password = ''
    busy.value = false
  }
}
</script>

<template>
  <SiteHeader simple />
  <main id="main-content" tabindex="-1" class="auth-layout login-layout"><aside class="auth-story"><p class="eyebrow">GOOD TO SEE YOU AGAIN</p><h1>A little care.<br><em>A growing business.</em></h1><p>Your next update, new idea, or freshly made product starts here.</p><span class="story-decoration" aria-hidden="true">b.</span></aside>
    <section class="form-panel login-panel"><p class="eyebrow">YOUR OWNER SPACE</p><h2>Welcome back.</h2><p class="section-description">Log in to manage your business.</p><p v-if="info && !failure" class="notice" role="status">{{ info }}</p><p v-if="failure" class="notice notice-error" role="alert">{{ failure }}</p>
      <form :aria-busy="busy" @submit.prevent="submit"><fieldset :disabled="busy"><legend class="sr-only">Owner login</legend>
        <FormField id="email" label="Email address" :error="errors.email" v-slot="field"><input id="email" v-model="email" name="email" type="email" autocomplete="username" required maxlength="254" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="you@example.com"></FormField>
        <FormField id="password" label="Password" :error="errors.password" v-slot="field"><input id="password" v-model="password" name="password" type="password" autocomplete="current-password" required maxlength="128" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="Your password"></FormField>
        <button class="button button-block" :disabled="busy">{{ busy ? 'Logging in…' : 'Log in →' }}</button>
      </fieldset></form><p class="form-footer">Starting something new? <RouterLink to="/register">Create your business</RouterLink></p>
    </section>
  </main>
</template>
