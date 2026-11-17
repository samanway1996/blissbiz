function origin(value) {
  const url = new URL(value)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('Frontend base URLs must be HTTP(S) origins without paths or credentials.')
  }
  return url.origin
}

export function createSiteConfig(location, env = {}) {
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname) || location.hostname.endsWith('.localhost')
  const port = location.port ? `:${location.port}` : ''
  const root = env.VITE_STOREFRONT_BASE_URL || (local ? `http://localhost${port}` : '')
  const admin = env.VITE_ADMIN_BASE_URL || (local ? `http://admin.localhost${port}` : '')
  if (!root || !admin) throw new Error('Configure VITE_STOREFRONT_BASE_URL and VITE_ADMIN_BASE_URL before building for this domain.')
  const storefrontOrigin = origin(root)
  const adminOrigin = origin(admin)
  const publicBase = new URL(storefrontOrigin)
  const publicHost = publicBase.hostname
  const suffix = `.${publicHost}`
  const candidate = location.hostname.endsWith(suffix) ? location.hostname.slice(0, -suffix.length) : ''
  const storefrontSlug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(candidate) && candidate.length <= 63 ? candidate : null
  const isStorefront = Boolean(storefrontSlug) && location.origin !== adminOrigin
    && location.protocol === publicBase.protocol && location.port === publicBase.port
  return {
    storefrontOrigin,
    adminOrigin,
    publicHost,
    storefrontSlug,
    isStorefront,
    isAdmin: location.origin === adminOrigin,
    isLanding: location.origin === storefrontOrigin || (local && ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname)),
    adminUrl: path => new URL(path, `${adminOrigin}/`).href,
  }
}

export function safeReturnPath(value) {
  // Return targets are restricted to implemented owner routes; reject external URLs.
  return typeof value === 'string' && /^\/businesses(?:\/[a-z0-9]+(?:-[a-z0-9]+)*(?:\/(?:settings|products(?:\/(?:new|[a-zA-Z0-9-]+\/edit))?))?)?$/.test(value)
    ? value : '/businesses'
}

export function safeBusinessUrls(urls, slug, config) {
  if (!urls || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) return null
  const admin = config.adminUrl(`/businesses/${slug}`)
  const storefront = new URL(config.storefrontOrigin)
  storefront.hostname = `${slug}.${storefront.hostname}`
  // Only display navigable API URLs which agree with the configured deployment.
  return urls.admin === admin && urls.storefront === storefront.origin ? { admin, storefront: storefront.origin } : null
}
