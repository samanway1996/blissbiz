import { safeReturnPath } from '../config/site.js'

export function createSessionGuard(session, site, navigate = url => window.location.replace(url)) {
  return async to => {
    if (!to.meta.admin) return true
    if (!site.isAdmin) { navigate(site.adminUrl(to.fullPath)); return false }
    let owner
    try { owner = await session.restore() }
    catch {
      if (to.meta.requiresAuth) return { name: 'login', query: { reason: 'unavailable', redirect: safeReturnPath(to.path) } }
      return true
    }
    if (to.meta.requiresAuth && !owner) {
      return { name: 'login', query: { reason: 'expired', redirect: safeReturnPath(to.path) } }
    }
    if (to.meta.guestOnly && owner) return safeReturnPath(to.query.redirect)
    return true
  }
}
