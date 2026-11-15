export async function getJson(path) {
  const response = await fetch(`/api${path}`, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(10000),
  })
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`)
  }
  return response.json()
}

