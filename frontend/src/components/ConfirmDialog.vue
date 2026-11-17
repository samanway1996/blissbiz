<script setup>
import { onBeforeUnmount, onMounted, ref, useId } from 'vue'
defineProps({ title: { type: String, required: true }, confirmLabel: { type: String, default: 'Delete' }, busy: Boolean, error: String })
const emit = defineEmits(['confirm', 'cancel'])
const dialog = ref(null)
const titleId = useId()
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => dialog.value?.close())
</script>
<template><Teleport to="body"><dialog ref="dialog" class="confirmation-dialog" :aria-labelledby="titleId" :aria-busy="busy" @cancel.prevent="!busy && emit('cancel')"><h2 :id="titleId">{{ title }}</h2><div class="section-description"><slot /></div><p v-if="error" class="notice notice-error" role="alert">{{ error }}</p><div class="actions"><button class="button button-secondary" :disabled="busy" autofocus @click="emit('cancel')">Cancel</button><button class="button button-danger" :disabled="busy" @click="emit('confirm')">{{ busy ? 'Working…' : confirmLabel }}</button></div></dialog></Teleport></template>
