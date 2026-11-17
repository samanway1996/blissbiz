export const normalizeSlug = value => value.trim().toLowerCase()
export const validSlug = value => value.length >= 1 && value.length <= 63 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value)

export function createSlugAvailability(client, update, delay = 350) {
  let version = 0
  let timer
  let controller
  function cancel() {
    version += 1
    clearTimeout(timer)
    controller?.abort()
  }
  function check(value) {
    cancel()
    const slug = normalizeSlug(value)
    if (!slug) { update({ status: 'idle', slug }); return }
    if (!validSlug(slug)) { update({ status: 'invalid', slug }); return }
    update({ status: 'checking', slug })
    const current = version
    controller = new AbortController()
    const signal = controller.signal
    timer = setTimeout(async () => {
      try {
        const result = await client.get(`/v1/business-slugs/${encodeURIComponent(slug)}/availability`, { signal })
        if (current === version) update({ status: result.available ? 'available' : 'unavailable', slug })
      } catch (error) {
        if (current === version && !signal.aborted) update({ status: 'error', slug })
      }
    }, delay)
  }
  return { check, cancel }
}
