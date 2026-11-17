<script setup>
import { computed, reactive, ref } from 'vue'
import FormField from '../components/FormField.vue'
import ImageManager from '../components/ImageManager.vue'
import BusinessLinks from '../components/BusinessLinks.vue'
import { useBusinessContext } from '../composables/useBusinessContext.js'
import { businessFields, catalog, changedFields, editableValues } from '../services/catalog.js'
import { errorMessage } from '../api/client.js'
const { business, busy, updateBusiness } = useBusinessContext()
const form = reactive(editableValues(business.value, businessFields))
const errors = ref({})
const failure = ref('')
const notice = ref('')
const changes = computed(() => changedFields(form, business.value || {}, businessFields))
async function save() {
  if (busy.value || !business.value) return
  errors.value = {}
  failure.value = ''
  notice.value = ''
  if (!form.name.trim()) { errors.value.name = 'Enter your business name.'; return }
  if (!Object.keys(changes.value).length) { notice.value = 'No changes to save.'; return }
  busy.value = true
  try {
    const saved = await catalog.updateBusiness(business.value.id, changes.value)
    updateBusiness(saved)
    Object.assign(form, editableValues(saved, businessFields))
    notice.value = 'Business settings saved.'
  } catch (error) { failure.value = errorMessage(error); errors.value = error.fields || {} }
  finally { busy.value = false }
}
async function uploadLogo(file) { return catalog.uploadLogo(business.value.id, file) }
async function removeLogo() { await catalog.removeLogo(business.value.id) }
</script>
<template><div class="page-heading"><div><p class="eyebrow">MAKE IT YOURS</p><h1>Business settings</h1><p class="section-description">The details customers see on your storefront.</p></div></div><div class="settings-columns"><section class="editor-panel"><h2>Business details</h2><p v-if="failure" class="notice notice-error" role="alert">{{ failure }}</p><form :aria-busy="busy" @submit.prevent="save"><fieldset :disabled="busy"><legend class="sr-only">Public business details</legend><FormField id="settings-name" label="Business name" :error="errors.name" v-slot="field"><input id="settings-name" v-model="form.name" required maxlength="150" autocomplete="organization" :aria-invalid="field.invalid" :aria-describedby="field.describedby"></FormField><FormField id="settings-description" label="Description" :error="errors.description" v-slot="field"><textarea id="settings-description" v-model="form.description" rows="4" maxlength="5000" :aria-invalid="field.invalid" :aria-describedby="field.describedby"></textarea></FormField><div class="form-two-columns"><FormField id="contact-email" label="Public contact email" :error="errors.contact_email" v-slot="field"><input id="contact-email" v-model="form.contact_email" type="email" maxlength="254" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="hello@yourbusiness.com"></FormField><FormField id="contact-phone" label="Public phone number" :error="errors.contact_phone" v-slot="field"><input id="contact-phone" v-model="form.contact_phone" type="tel" maxlength="32" :aria-invalid="field.invalid" :aria-describedby="field.describedby"></FormField></div><FormField id="business-address" label="Public business address" :error="errors.address" v-slot="field"><textarea id="business-address" v-model="form.address" rows="3" maxlength="1000" :aria-invalid="field.invalid" :aria-describedby="field.describedby"></textarea></FormField><p class="field-hint">These contact details are public. Your private owner email stays separate.</p><div class="form-two-columns"><FormField id="settings-slug" label="Website address" hint="Chosen at registration; cannot be changed."><input id="settings-slug" :value="business.slug" readonly></FormField><FormField id="settings-currency" label="Currency" hint="Applies to all your product prices."><input id="settings-currency" :value="business.currency" readonly></FormField></div><button class="button" :disabled="busy">{{ busy ? 'Please wait…' : 'Save changes' }}</button></fieldset></form><p class="save-notice" role="status">{{ notice }}</p></section><aside class="settings-aside"><section class="editor-panel"><ImageManager id="business-logo" label="Business logo" :current-url="business.logo_url" :upload="uploadLogo" :remove="removeLogo" :disabled="busy" @busy="busy = $event" @saved="updateBusiness" @removed="updateBusiness({ ...business, logo_url: null })" /></section><section class="editor-panel"><h2>Your website links</h2><BusinessLinks :business="business" :urls="business.urls" /></section></aside></div></template>
