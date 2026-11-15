# B02 business registration

`POST /api/v1/registrations` creates a new owner and business, replaces the anonymous session with an owner session, and returns admin/storefront URLs. Login/logout/profile and both business UIs remain later tasks. Generated URLs describe the eventual routes; registration does not deploy a new app or provision DNS.

## Request and response

First call `GET /api/v1/auth/csrf` on the same admin origin, retain the browser cookie, and send the returned token in `X-CSRF-Token`. Origin (or Referer when Origin is absent) must pass the B01 allowlist.

Example body; choose a unique email and slug when reviewing:

```json
{
  "owner": {
    "full_name": "Review Owner",
    "email": "review-owner@example.com",
    "password": "a unique review passphrase"
  },
  "business": {
    "name": "Review Bakery",
    "slug": "review-bakery",
    "description": "Fresh bread every morning.",
    "currency": "INR"
  }
}
```

A `201` response contains `owner` (`id`, `full_name`, `email`), `business` (`id`, `name`, `slug`), and `urls` (`admin`, `storefront`). It sets the new HttpOnly session cookie and `Cache-Control: no-store`; no password, hash, or session credential appears in JSON. The old cookie/CSRF token becomes invalid. Bootstrap CSRF again before another mutation.

Validation rules:

- Owner name/email/password and business name/slug are required. Names are trimmed and limited to 150 characters. Unknown fields, including client-supplied ownership IDs/hashes, are rejected.
- Passwords contain 15–128 characters and are not trimmed, silently truncated, or subject to special-character composition rules. They are stored as salted Argon2id hashes through `argon2-cffi`, never plaintext.
- Emails are syntax-validated, converted to an ASCII address (including IDN domain conversion), and lowercased before lookup/storage. Internationalized local parts are not supported in this MVP. DNS deliverability and email ownership verification are deferred; syntax validation does not verify an inbox.
- Phone fields are optional and limited to 32 characters. Description is optional, up to 5000 characters; address up to 1000. Business contact email/phone/address are explicitly public fields and never copied automatically from the owner's private profile.
- Slugs follow B00 normalization/reserved-name rules. Currency defaults to `INR`; other currencies are not enabled yet.
- Existing owner sessions cannot create another owner through this endpoint; return `409` / `already_authenticated`. Adding businesses to an existing account requires a future dedicated flow.

## Transactions and conflicts

Owner/business creation and session rotation share one transaction. Repositories/services flush only; the route commits once before issuing a cookie. A failure rolls back related writes and preserves the previously committed anonymous session. Rotation locks and rechecks the session so a competing request cannot reuse a consumed session.

Prechecks produce `409` / `slug_unavailable` or `email_unavailable`, with field errors. Database unique constraints remain authoritative: a uniqueness race returns `409` / `registration_conflict` without exposing SQL/driver messages. Non-uniqueness database failures return a safe `503`. Missing/invalid CSRF or origins return `403`; invalid fields return `422`.

The service explicitly checks normalized email/slug uniqueness; ID generation and existing database constraints are unchanged. No owner/business schema change is needed for B02.

## Shared registration rate limit

Default: **5 schema-valid, CSRF-verified registration submissions per network peer per 15-minute fixed window**. Windows align to Unix time boundaries; this is not a sliding window. Conflicts, already-authenticated attempts, and later registration failures still consume quota. Invalid body/CSRF requests fail before quota consumption and password hashing.

Quota state lives in MySQL, in `rate_limit_buckets` (migration `0003`). An independent transaction commits the attempt before registration starts. A separate bounded connection pool (2 pooled connections plus up to 3 overflow connections per worker) prevents nested quota checks from exhausting the main request pool. Atomic upserts and transaction locks share limits across workers and keep concurrent requests from exceeding the quota; counters saturate at limit + 1. `429` responses include `Retry-After` seconds until the current window ends.

The application uses the ASGI network peer, not raw `X-Forwarded-For` headers. Production must configure trusted proxies correctly and prevent direct public access to the upstream port. Local requests through Vite may share the same peer/quota. Missing peer information shares a conservative `unknown` bucket. Keys include purpose, peer, and window and are hashed; raw IP addresses are not stored in this table.

Counter operations use isolated MySQL/SQLite upsert implementations in `db/rate_limits.py`; uniqueness-error classification is isolated in `db/integrity.py`. Switching database engines requires adapting these helpers in addition to the documented migration/data-transfer checks. Cleanup scheduling for expired counters remains B09 work; expired windows cannot block a new window.

## Configuration

Optional additions to `backend/.env` (defaults shown):

```dotenv
STOREFRONT_BASE_URL=http://localhost:5173
ADMIN_BASE_URL=http://admin.localhost:5173
REGISTRATION_RATE_LIMIT=5
REGISTRATION_RATE_WINDOW_SECONDS=900
```

The URL settings must be origins, without paths, credentials, or wildcards. The storefront base uses a DNS name, not an IP address, with room for a business label. URLs are generated from this configuration and the validated slug, never Host/forwarded headers.

For production, configure both as real HTTPS origins, set `APP_ENV=production`, and include the exact admin origin in `AUTH_ALLOWED_ORIGINS`. Example:

```dotenv
APP_ENV=production
STOREFRONT_BASE_URL=https://example.com
ADMIN_BASE_URL=https://admin.example.com
AUTH_ALLOWED_ORIGINS=["https://admin.example.com"]
```

Keep the existing database/session settings. Restart the user-owned backend after dependency or environment changes. Domain routing and storefront/dashboard pages are not provided by B02. For the eventual browser registration flow, submit on the configured admin hostname so its host-only session cookie also applies to the dashboard; direct Swagger review on a different local hostname keeps its cookie on that hostname.

## Review B02

1. Install the new locked dependencies with `make setup`, then run `make db-up` and `make db-migrate`. The migration head is `0003`. These commands preserve existing local environment files and business data.
2. Start/restart the backend in your terminal with `make dev-backend`.
3. Open `/api/docs`. Execute `GET /api/v1/auth/csrf`, then copy its CSRF token into the `X-CSRF-Token` input on `POST /api/v1/registrations`. Keep the same browser origin/cookies. Do not include real credentials in review screenshots or logs.
4. Submit a unique version of the example. Expect `201`, both URLs, and a replaced HttpOnly cookie. Manual registration creates real local records; it is not an automatic test fixture.
5. In a separate private browser session, bootstrap again and submit the same email or slug. Expect `409`. Omit CSRF for `403`; use a short password for a safe field-specific `422`. After a successful registration, the current owner session intentionally gets `already_authenticated` on another registration.
6. Run `make check` and `make test-mysql`. Coverage includes real Argon2 verification, normalization/validation, privacy, session rotation, transactional rollback, database uniqueness conflicts, rate-window reset, failed-attempt persistence, and independent concurrent workers. The MySQL worker test runs only with the opt-in MySQL suite and cleans up only its own uniquely keyed counter.
7. If manual review reaches `429`, wait the returned Retry-After or deliberately change the development limit and restart; do not delete databases/volumes to reset the counter.

Main code: `schemas/registrations.py` → `api/registrations.py` → `services/registrations.py` → owner/business/session repositories. Password and URL services and the separate rate limiter are explicit collaborators. Tests live in `test_registrations.py` and `test_rate_limits.py`.

Library references: [argon2-cffi password hashing](https://argon2-cffi.readthedocs.io/en/stable/howto.html), [email-validator normalization](https://pypi.org/project/email-validator/), and [OWASP password guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).
