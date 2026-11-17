export const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const imageTypes = new Set(['image/jpeg', 'image/png', 'image/webp'])

export function imageSelectionError(file) {
  if (!file || file.size === 0) return 'Choose a non-empty JPEG, PNG or WebP image.'
  if (file.size > MAX_IMAGE_BYTES) return 'Choose an image no larger than 5 MB.'
  if (file.type && !imageTypes.has(file.type)) return 'Choose a JPEG, PNG or WebP image.'
  return ''
}

export function safeMediaUrl(value) {
  return typeof value === 'string' && /^\/media\/businesses\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+\.(?:jpg|png|webp)$/.test(value) ? value : ''
}

export function createImagePreview(urls = URL) {
  let current = ''
  function clear() {
    if (current) urls.revokeObjectURL(current)
    current = ''
  }
  return { select(file) { clear(); current = urls.createObjectURL(file); return current }, clear }
}
