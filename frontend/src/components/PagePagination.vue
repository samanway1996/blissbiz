<script setup>
import { computed } from 'vue'
const props = defineProps({ page: { type: Number, required: true }, pageSize: { type: Number, required: true }, total: { type: Number, required: true }, disabled: Boolean, singular: { type: String, default: 'product' }, plural: { type: String, default: 'products' } })
defineEmits(['change'])
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
</script>
<template><nav v-if="total > 0" class="pagination" aria-label="Catalog pages"><p role="status">{{ total }} {{ total === 1 ? singular : plural }} · Page {{ page }} of {{ pages }}</p><div class="actions"><button class="button button-secondary button-small" :disabled="disabled || page <= 1" @click="$emit('change', page - 1)">← Previous</button><button class="button button-secondary button-small" :disabled="disabled || page >= pages" @click="$emit('change', page + 1)">Next →</button></div></nav></template>
