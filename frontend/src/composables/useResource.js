import { onScopeDispose, ref, watch } from 'vue'
import { createLatestRequest } from '../services/latestRequest.js'

export function useResource(source, loader) {
  const data = ref(null)
  const error = ref(null)
  const loading = ref(true)
  const request = createLatestRequest()
  function reload() {
    if (source() == null) {
      request.cancel()
      data.value = null
      error.value = null
      loading.value = false
      return Promise.resolve()
    }
    return request.run(loader, {
      start() { loading.value = true; error.value = null; data.value = null },
      success(value) { data.value = value },
      error(value) { error.value = value },
      finish() { loading.value = false },
    })
  }
  watch(source, reload, { immediate: true, flush: 'sync' })
  onScopeDispose(request.cancel)
  return { data, error, loading, reload }
}
