# B01 session and CSRF contract

B01 implements server-side sessions and request-verification helpers. B02 now uses them for registration; login/logout/profile remain future tasks. This contract is shared by B02/B03 and frontend task F02.

## Bootstrap and expiration

`GET /api/v1/auth/csrf` returns `{ "csrf_token": "<opaque-token>" }` and sets a host-only HttpOnly session cookie. Session credentials and CSRF tokens are independently generated random values. The database stores only a SHA-256 hash of the session credential and keeps the independent CSRF token in the session record; the session credential is never returned in JSON.

A valid existing session is reused, including its CSRF token and owner association. Bootstrap does not extend expiry or downgrade an owner to anonymous. Missing, malformed, unknown, or expired credentials receive a fresh anonymous session; client-chosen credentials are never adopted. Reusing the CSRF token until session rotation avoids invalidating other tabs unnecessarily.

Anonymous sessions have a 15-minute absolute lifetime; owner sessions have an 8-hour absolute lifetime. Expiry is checked server-side regardless of the browser's cookie retention. Rotation replaces both tokens and removes the old session within the caller's transaction. Revoked/expired sessions cannot authorize requests.

## Cookies and origins

| Setting | Development | Production |
| --- | --- | --- |
| Cookie name | `blissbiz_session` | `__Host-blissbiz_session` |
| Secure | No, to allow local HTTP | Yes |
| HttpOnly / SameSite / Path | Yes / Lax / `/` | Yes / Lax / `/` |
| Domain attribute | Omitted: host-only | Omitted: host-only |
| Lifetime | Max-Age and Expires match remaining server lifetime | Same |

Production settings require explicitly configured HTTPS admin origins. Both the auth request target and its source must be explicitly allowed; suffixes, wildcards, and public storefront origins are not accepted. The application ignores forwarded-host headers for this decision; production proxy trust/HTTPS forwarding must be configured safely in B09.

Use Origin when present; otherwise check Referer. Mutations reject requests missing both. A bad Origin cannot be overridden by a good Referer. Bootstrap permits neither header for direct navigation/CLI use, but still validates its target. `Sec-Fetch-Site: cross-site` is rejected. Successful bootstrap and security-error responses use `Cache-Control: no-store`; bootstrap also varies by Cookie/Origin.

The default development allowlist explicitly includes `127.0.0.1`, `localhost`, and `admin.localhost`, each on ports 5173 and 8000. It supports current Vite and direct Swagger review without trusting arbitrary storefront subdomains. This is an auth allowlist, not CORS permission.

## Future endpoint integration

1. The frontend calls `/api/v1/auth/csrf` on its admin origin. Keep the returned CSRF token in memory; the browser manages the HttpOnly cookie.
2. Send `X-CSRF-Token` on POST/PATCH/PUT/DELETE. Do not send it as a URL/query value or persist session credentials in local storage.
3. Registration/login require `require_csrf_session`. Owner reads use `require_owner_session`; owner mutations use `require_owner_mutation`, enforcing both owner authentication and CSRF. These are reusable dependencies; B01 exposes no debug mutation endpoints.
4. Owner-session validation does not replace business ownership validation. Future repositories/services must still scope every business/product operation to the authenticated owner.
5. After CSRF and credential checks, registration/login call `SessionService.rotate(raw_token, owner_id)`. The helper locks the active session row, replaces it, and returns new credentials. The caller commits owner/business/session changes together; service/repository helpers never commit independently.
6. Set cookies only after a successful commit using `SessionCookies`, which centralizes scope/attributes. Copy response data/expiry before commit so ORM expiration does not cause unnecessary queries afterward. Fetch CSRF again after rotation.
7. Future logout revokes the server session, commits, then uses `SessionCookies.clear`. Cookie removal alone is insufficient.
8. Expired rows are denied immediately. `purge_expired` is available for maintenance, but cleanup scheduling is not implemented. Bootstrap prunes only an expired session matching the supplied credential. Public abuse controls remain auth/deployment follow-ups.

Missing, mismatched, expired, or cross-session CSRF tokens produce `403` / `csrf_rejected`; missing/expired/anonymous owner sessions produce `401` / `authentication_required`. Errors use the API envelope and never include credential values. Database failures return a safe `503` and do not issue a session cookie.

## Configuration

Add overrides to `backend/.env`; do not overwrite the existing `DATABASE_URL`. Defaults allow existing local environments to keep working.

| Environment variable | Default / format |
| --- | --- |
| `APP_ENV` | `development`; use `production` to require secure cookies/HTTPS origins |
| `ANONYMOUS_SESSION_TTL_SECONDS` | `900`; range 60–3600 |
| `OWNER_SESSION_TTL_SECONDS` | `28800`; range 60–2592000 |
| `AUTH_ALLOWED_ORIGINS` | JSON array of exact admin UI/API origins; see `backend/.env.example` |

Production example (replace the example domain):

```dotenv
APP_ENV=production
AUTH_ALLOWED_ORIGINS=["https://admin.example.com"]
STOREFRONT_BASE_URL=https://example.com
ADMIN_BASE_URL=https://admin.example.com
```

Restart a development server after changing environment configuration. Origin/cookie settings do not enable local hostname routing or production TLS by themselves.

## Review B01

1. Run `make db-up` and `make db-migrate`; the migration head should be `0002`.
2. Run your backend with `make dev-backend`; if it is already running, keep using that terminal. B01 verification does not require another server process.
3. Open `/api/docs` and execute `GET /api/v1/auth/csrf`. Expect `200`, one `csrf_token` JSON field, and an HttpOnly cookie. Do not copy real token values into reviews/logs.
4. Execute again in the same browser: the CSRF token should stay the same while the session is valid. Inspect cookie attributes and `Cache-Control: no-store` in browser developer tools.
5. Run `make check` and `make test-mysql`. Tests cover anonymous/owner lifecycle, expiry, cross-session CSRF rejection, strict origins, production cookies, atomic rotation failure, and legacy behavior. Security probe routes exist only inside test applications and are never registered in the real backend.

No new dependencies were introduced. The design follows the server-side synchronizer-token pattern and restrictive cookie scope in the [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html) and [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
