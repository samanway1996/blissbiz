<script setup>
const props = defineProps({ id: { type: String, required: true }, label: { type: String, required: true }, error: String, hint: String })
</script>

<template>
  <div class="form-field">
    <label :for="id">{{ label }}</label>
    <slot :invalid="Boolean(props.error)" :describedby="error ? `${id}-error` : hint ? `${id}-hint` : undefined" />
    <p v-if="error" :id="`${id}-error`" class="field-error">{{ error }}</p>
    <p v-else-if="hint" :id="`${id}-hint`" class="field-hint">{{ hint }}</p>
  </div>
</template>
