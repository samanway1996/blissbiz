<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import FormField from '../components/FormField.vue'
import ImageManager from '../components/ImageManager.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import { useBusinessContext } from '../composables/useBusinessContext.js'
import { useOwnerSession } from '../composables/useOwnerSession.js'
import { useResource } from '../composables/useResource.js'
import { catalog, changedFields, editableValues, productFields, validPrice } from '../services/catalog.js'
import { errorMessage } from '../api/client.js'
const route = useRoute()
const router = useRouter()
const session = useOwnerSession()
const { business, busy } = useBusinessContext()
const creating = computed(() => route.name === 'product-create')
const form = reactive({ name: '', description: '', price: '', status: 'draft' })
const errors = ref({})
const failure = ref('')
const notice = ref('')
const confirming = ref(false)
const deleteError = ref('')
const { data: product, loading, error, reload } = useResource(
  () => business.value ? `${business.value.id}:${route.name}:${route.params.productId || 'new'}` : null,
  signal => creating.value ? Promise.resolve({ name: '', description: null, price: '', status: 'draft' }) : catalog.getProduct(business.value.id, route.params.productId, { signal }),
)
watch([loading, () => product.value?.id], ([pending]) => {
  if (!pending && product.value) {
    Object.assign(form, editableValues(product.value, productFields))
    errors.value = {}; failure.value = ''; notice.value = ''; confirming.value = false; deleteError.value = ''
  }
})
const listRoute = computed(() => ({ name: 'products', params: { slug: business.value.slug } }))
const canLeave = () => !busy.value || !session.state.owner
onBeforeRouteLeave(canLeave)
onBeforeRouteUpdate(canLeave)
async function save() {
  if (busy.value || !product.value) return
  failure.value = ''; errors.value = {}; notice.value = ''
  if (!form.name.trim()) errors.value.name = 'Enter a product name.'
  if (!validPrice(form.price)) errors.value.price = 'Use a nonnegative price with up to 10 digits and 2 decimal places.'
  if (Object.keys(errors.value).length) return
  const changes = changedFields(form, product.value, creating.value ? productFields.filter(field => field !== 'status') : productFields)
  if (!creating.value && !Object.keys(changes).length) { notice.value = 'No changes to save.'; return }
  busy.value = true
  let destination
  const wasCreating = creating.value
  try {
    const saved = creating.value
      ? await catalog.createProduct(business.value.id, { name: form.name.trim(), description: form.description.trim() || null, price: form.price })
      : await catalog.updateProduct(business.value.id, product.value.id, changes)
    if (creating.value) destination = { name: 'product-edit', params: { slug: business.value.slug, productId: saved.id }, query: { created: '1' } }
    product.value = saved
    Object.assign(form, editableValues(saved, productFields))
    notice.value = 'Product saved.'
    if (!wasCreating && route.query.created) destination = { name: 'product-edit', params: { slug: business.value.slug, productId: saved.id } }
  } catch (problem) { failure.value = errorMessage(problem); errors.value = problem.fields || {} }
  finally { busy.value = false }
  if (destination) await router.replace(destination)
}
async function removeProduct() {
  if (busy.value) return
  busy.value = true
  deleteError.value = ''
  let deleted = false
  try { await catalog.deleteProduct(business.value.id, product.value.id); deleted = true }
  catch (problem) { deleteError.value = errorMessage(problem) }
  finally { busy.value = false }
  if (deleted) { confirming.value = false; await router.replace(listRoute.value) }
}
async function uploadImage(file) { return catalog.uploadProductImage(business.value.id, product.value.id, file) }
async function removeImage() { await catalog.removeProductImage(business.value.id, product.value.id) }
function imageSaved(value) { product.value = value }
</script>
<template><RouterLink class="back-link" :to="listRoute" :aria-disabled="busy" @click="busy && $event.preventDefault()">← All products</RouterLink><div class="page-heading"><div><p class="eyebrow">YOUR CATALOG</p><h1>{{ creating ? 'Add a product' : 'Edit product' }}</h1><p class="section-description">{{ creating ? 'Start with a draft. Publish whenever you’re ready.' : 'Keep the details fresh and choose what customers see.' }}</p></div><span v-if="product?.id" class="status-badge" :class="product.status">{{ product.status === 'published' ? 'Published' : 'Draft' }}</span></div><p v-if="loading" role="status">Loading product…</p><div v-else-if="error" class="notice notice-error" role="alert"><p>{{ error.status === 404 ? 'This product could not be found in this business.' : errorMessage(error) }}</p><button v-if="error.status !== 404" class="button button-secondary" @click="reload">Try again</button></div><div v-else-if="product" class="settings-columns"><section class="editor-panel"><p v-if="route.query.created === '1' && !creating" class="notice" role="status">Draft created. Add a photo and publish when you’re ready.</p><h2>Product details</h2><p v-if="failure" class="notice notice-error" role="alert">{{ failure }}</p><form :aria-busy="busy" @submit.prevent="save"><fieldset :disabled="busy"><legend class="sr-only">Product details</legend><FormField id="product-name" label="Product name" :error="errors.name" v-slot="field"><input id="product-name" v-model="form.name" required maxlength="150" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="e.g. Sourdough loaf"></FormField><FormField id="product-description" label="Description" :error="errors.description" v-slot="field"><textarea id="product-description" v-model="form.description" rows="5" maxlength="5000" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="What makes this product special?"></textarea></FormField><FormField id="product-price" :label="`Price (${business.currency})`" hint="Use up to 2 decimal places, e.g. 499.00." :error="errors.price" v-slot="field"><input id="product-price" v-model="form.price" type="text" inputmode="decimal" required maxlength="13" pattern="[0-9]{1,10}(\.[0-9]{1,2})?" :aria-invalid="field.invalid" :aria-describedby="field.describedby" placeholder="499.00"></FormField><FormField v-if="!creating" id="product-visibility" label="Visibility" hint="Only published products appear on your public storefront." :error="errors.status" v-slot="field"><select id="product-visibility" v-model="form.status" :aria-invalid="field.invalid" :aria-describedby="field.describedby"><option value="draft">Draft — hidden from customers</option><option value="published">Published — visible on storefront</option></select></FormField><div class="actions"><button class="button" :disabled="busy">{{ busy ? 'Please wait…' : creating ? 'Create draft' : 'Save changes' }}</button><RouterLink class="button button-secondary" :to="listRoute" :aria-disabled="busy" @click="busy && $event.preventDefault()">Cancel</RouterLink></div></fieldset></form><p class="save-notice" role="status">{{ notice }}</p></section><aside class="settings-aside"><section class="editor-panel"><ImageManager v-if="!creating && product.id" id="product-image" label="Product photo" :current-url="product.image_url" :upload="uploadImage" :remove="removeImage" :disabled="busy" @busy="busy = $event" @saved="imageSaved" @removed="product = { ...product, image_url: null }" /><template v-else><h2>Product photo</h2><p class="section-description">Create your draft first, then add its photo here.</p></template></section><section v-if="!creating" class="editor-panel delete-section"><h2>Delete product</h2><p class="field-hint">Remove this product and its image permanently. You can choose Draft instead to hide it.</p><button class="button button-secondary danger-text" :disabled="busy" @click="confirming = true; deleteError = ''">Delete product</button></section></aside></div><ConfirmDialog v-if="confirming" title="Delete this product?" confirm-label="Delete permanently" :busy="busy" :error="deleteError" @cancel="confirming = false" @confirm="removeProduct">“{{ product.name }}” and its image will be removed. This cannot be undone.</ConfirmDialog></template>
