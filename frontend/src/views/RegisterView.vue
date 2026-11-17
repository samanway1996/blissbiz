<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import FormField from '../components/FormField.vue'
import { api, errorMessage } from '../api/client.js'
import { site } from '../composables/useSite.js'
import { useOwnerSession } from '../composables/useOwnerSession.js'
import { createSlugAvailability, normalizeSlug } from '../services/slugAvailability.js'

const router = useRouter()
const session = useOwnerSession()
const form = reactive({ full_name: '', email: '', password: '', name: '', slug: '', description: '' })
const errors = ref({})
const failure = ref('')
const busy = ref(false)
const slugState = ref({ status: 'idle', slug: '' })
const checker = createSlugAvailability(api, value => { slugState.value = value })
watch(() => form.slug, value => { delete errors.value['business.slug']; checker.check(value) })
onBeforeUnmount(() => { checker.cancel(); form.password = '' })
const slugMessages = {
  idle: 'Choose 1–63 letters or numbers, separated by single hyphens.',
  checking: 'Checking this address…',
  available: 'This address is available. It is reserved when registration completes.',
  unavailable: 'This address is taken or reserved. Choose another.',
  invalid: 'Use 1–63 letters or numbers, separated by single hyphens.',
  error: 'Availability could not be checked. You can still submit; we will check it then.',
}
const slugMessage = computed(() => slugMessages[slugState.value.status])
const slugUrl = computed(() => `${normalizeSlug(form.slug) || 'your-business'}.${new URL(site.storefrontOrigin).host}`)

async function submit() {
  if (busy.value) return
  failure.value = ''
  errors.value = {}
  busy.value = true
  const payload = {
    owner: { full_name: form.full_name.trim(), email: form.email.trim(), password: form.password },
    business: { name: form.name.trim(), slug: normalizeSlug(form.slug), description: form.description.trim() || null, currency: 'INR' },
  }
  try {
    const result = await session.register(payload)
    await router.replace({ name: 'registration-success', params: { slug: result.business.slug } })
  } catch (error) {
    errors.value = error.fields || {}
    failure.value = error.status === 0
      ? `${errorMessage(error)} If you already submitted, try logging in before registering again.`
      : errorMessage(error)
    if (error.code === 'already_authenticated') await router.replace('/businesses')
  } finally {
    form.password = ''
    payload.owner.password = ''
    busy.value = false
  }
}
</script>

<template>
  <SiteHeader simple />
  <main id="main-content" tabindex="-1" class="auth-layout registration-layout">
    <aside class="auth-story"><p class="eyebrow">YOUR NEXT CHAPTER STARTS HERE</p><h1>Small business.<br><em>Big beginning.</em></h1><p>You bring the idea. We’ll give it a place online.</p><ol class="benefit-list"><li>Your own website address</li><li>A simple place to manage products</li><li>A storefront you can share with anyone</li></ol><p class="privacy-note">Your owner email is private. You can add separate public contact details later.</p></aside>
    <section class="form-panel"><p class="eyebrow">LET’S MAKE IT HAPPEN</p><h2>Create your business</h2><p class="section-description">Just a few details to get you started.</p>
      <p v-if="failure" role="alert" class="notice notice-error">{{ failure }}</p>
      <form :aria-busy="busy" @submit.prevent="submit"><fieldset :disabled="busy"><legend>About you</legend>
        <FormField id="owner-name" label="Full name" :error="errors['owner.full_name']" v-slot="field"><input id="owner-name" v-model="form.full_name" name="name" autocomplete="name" required maxlength="150" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="Your full name"></FormField>
        <FormField id="owner-email" label="Email address" :error="errors['owner.email']" v-slot="field"><input id="owner-email" v-model="form.email" name="email" autocomplete="email" type="email" required maxlength="254" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="you@example.com"></FormField>
        <FormField id="owner-password" label="Password" hint="Use 15–128 characters. A memorable passphrase works well." :error="errors['owner.password']" v-slot="field"><input id="owner-password" v-model="form.password" name="password" autocomplete="new-password" type="password" required minlength="15" maxlength="128" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="Create a passphrase"></FormField>
      </fieldset><fieldset :disabled="busy"><legend>About your business</legend>
        <FormField id="business-name" label="Business name" :error="errors['business.name']" v-slot="field"><input id="business-name" v-model="form.name" name="business-name" autocomplete="organization" required maxlength="150" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="e.g. MyDreamBakery"></FormField>
        <FormField id="business-slug" label="Website address" :error="errors['business.slug']" v-slot="field"><input id="business-slug" v-model="form.slug" name="slug" autocapitalize="none" spellcheck="false" required maxlength="63" pattern="[A-Za-z0-9]+(-[A-Za-z0-9]+)*" :aria-invalid="field.invalid || ['invalid', 'unavailable'].includes(slugState.status)" :aria-describedby="[field.describedby, 'slug-preview', 'slug-feedback'].filter(Boolean).join(' ')" placeholder="my-dream-bakery" @blur="form.slug = normalizeSlug(form.slug)"></FormField>
        <p id="slug-preview" class="slug-preview">{{ slugUrl }}</p><p id="slug-feedback" class="field-hint slug-feedback" :class="{ 'field-error': ['invalid', 'unavailable'].includes(slugState.status), 'field-success': slugState.status === 'available' }" role="status">{{ slugMessage }}</p>
        <FormField id="description" label="Business description (optional)" :error="errors['business.description']" v-slot="field"><textarea id="description" v-model="form.description" name="description" rows="3" maxlength="5000" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="Tell customers a little about what you do."></textarea></FormField>
        <p class="field-hint">Product prices will use INR (₹).</p>
        <button class="button button-block" :disabled="busy || ['checking', 'unavailable', 'invalid'].includes(slugState.status)">{{ busy ? 'Creating your business…' : 'Create my business →' }}</button>
      </fieldset></form>
      <p class="form-footer">Already have a business? <RouterLink to="/login">Log in</RouterLink></p>
    </section>
  </main>
</template>
