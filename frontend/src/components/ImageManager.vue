<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import CatalogImage from './CatalogImage.vue'
import ConfirmDialog from './ConfirmDialog.vue'
import { createImagePreview, imageSelectionError } from '../services/images.js'
import { errorMessage } from '../api/client.js'
const props = defineProps({ id: { type: String, required: true }, label: { type: String, required: true }, currentUrl: String, upload: { type: Function, required: true }, remove: { type: Function, required: true }, disabled: Boolean })
const emit = defineEmits(['busy', 'saved', 'removed'])
const file = ref(null)
const preview = ref('')
const input = ref(null)
const busy = ref(false)
const failure = ref('')
const notice = ref('')
const confirming = ref(false)
const previews = createImagePreview()
const blocked = computed(() => props.disabled || busy.value)
function clearSelection() {
  previews.clear()
  preview.value = ''
  file.value = null
  if (input.value) input.value.value = ''
}
function choose(selected) {
  const message = imageSelectionError(selected)
  if (message) { failure.value = message; return }
  file.value = selected
  preview.value = previews.select(selected)
}
function onSelect(event) {
  const selected = event.target.files?.[0]
  clearSelection()
  failure.value = ''
  notice.value = ''
  if (selected) choose(selected)
}
async function upload() {
  if (blocked.value || !file.value) return
  busy.value = true
  emit('busy', true)
  failure.value = ''
  try {
    const result = await props.upload(file.value)
    emit('saved', result)
    clearSelection()
    notice.value = 'Image saved.'
  } catch (error) { failure.value = error.status ? errorMessage(error) : `${errorMessage(error)} Refresh to check the saved image before trying again.` }
  finally { busy.value = false; emit('busy', false) }
}
async function remove() {
  if (blocked.value) return
  busy.value = true
  emit('busy', true)
  failure.value = ''
  try {
    await props.remove()
    emit('removed')
    clearSelection()
    confirming.value = false
    notice.value = 'Image removed.'
  } catch (error) { failure.value = errorMessage(error) }
  finally { busy.value = false; emit('busy', false) }
}
onBeforeUnmount(previews.clear)
</script>
<template><section class="image-manager" :aria-labelledby="`${id}-label`" :aria-busy="busy"><h3 :id="`${id}-label`">{{ label }}</h3><div class="image-manager-preview"><CatalogImage v-if="currentUrl" :src="currentUrl" :alt="`Current ${label.toLowerCase()}`" /><div v-if="preview" class="selected-image"><img :src="preview" :alt="`Preview of selected ${label.toLowerCase()}`"><p class="field-hint">Preview · not saved yet</p></div><p v-if="!currentUrl && !preview" class="field-hint">No image added yet.</p></div><label class="file-label" :for="id">Choose {{ label.toLowerCase() }}</label><input :id="id" ref="input" type="file" accept="image/jpeg,image/png,image/webp" :disabled="blocked" :aria-describedby="`${id}-hint`" @change="onSelect"><p :id="`${id}-hint`" class="field-hint">Still JPEG, PNG or WebP · Up to 5 MB and 20 megapixels. Images are publicly accessible, including draft product images.</p><p v-if="failure && !confirming" class="notice notice-error" role="alert">{{ failure }}</p><div class="actions"><button v-if="file" type="button" class="button button-small" :disabled="blocked" @click="upload">{{ busy ? 'Saving image…' : currentUrl ? 'Replace image' : 'Upload image' }}</button><button v-if="file" type="button" class="button button-secondary button-small" :disabled="blocked" @click="clearSelection">Cancel selection</button><button v-if="currentUrl" type="button" class="button button-secondary button-small" :disabled="blocked" @click="failure = ''; confirming = true">Remove image</button></div><p class="field-hint" role="status">{{ notice }}</p><ConfirmDialog v-if="confirming" title="Remove this image?" confirm-label="Remove image" :busy="busy" :error="failure" @cancel="confirming = false" @confirm="remove">The saved image will be removed from this business. This cannot be undone.</ConfirmDialog></section></template>
