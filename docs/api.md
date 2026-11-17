# BlissBiz API plan

Contract for the hackathon MVP: register a business, manage its catalog through an owner dashboard, and display published products on a public storefront. Backend APIs through B09 are implemented, including host-based storefronts and deployment preparation. `/api/health`, `/api/ready` and `/media/...` also exist. Business frontend screens remain separate work.

## Conventions

- New endpoints use `/api/v1`; paths below are relative to that prefix.
- Requests and responses use JSON with `snake_case` fields, except image uploads, which use `multipart/form-data`.
- IDs are opaque strings in the API, timestamps use UTC ISO 8601, and prices are decimal strings, such as `"249.00"`. A business has one currency, initially `INR`.
- Success codes: `200` for reads/updates, `201` for creation, and `204` for deletion/logout with no response body.
- Admin routes require an owner session. Every business/product operation checks ownership in FastAPI, including nested product IDs.
- Lists return `{ "items": [], "page": 1, "page_size": 20, "total": 0 }`; `page_size` is capped at 100. Products default to newest first with an ID tie-breaker.
- `PATCH` changes only supplied fields; explicit `null` clears nullable fields. IDs, ownership, and timestamps are server-controlled.

## Business registration

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/business-slugs/{slug}/availability` | Public | Check normalized slug availability; returns `slug` and `available`. |
| POST | `/registrations` | Public + CSRF | Create owner account and business together; return both website URLs and start an owner session. |

Both registration endpoints are implemented. See [the B02 contract and review guide](registration.md) for password/email validation, transaction/conflict behavior, rate limiting, and configured URL generation. Session/CSRF bootstrap is required before submitting the form.

The availability check is advisory. Registration must enforce slug and normalized owner-email uniqueness in the database and return `409` on conflict. Slugs are trimmed and lowercased, contain 1–63 ASCII letters/numbers separated by single hyphens, and cannot start/end with a hyphen. Infrastructure names such as `admin`, `api`, and `www` are reserved and return `available: false`. Invalid formats return `422`; an unavailable database returns `503` without connection details. Keep the slug immutable in the MVP.

Example registration request:

```json
{
  "owner": {
    "full_name": "Sample Owner",
    "email": "owner@example.com",
    "password": "<owner-chosen-password>",
    "phone": "+919000000000"
  },
  "business": {
    "name": "Happy Bakery",
    "slug": "happy-bakery",
    "description": "Freshly baked every morning.",
    "contact_email": "hello@example.com",
    "contact_phone": "+919000000001",
    "address": "Sample shop address",
    "currency": "INR"
  }
}
```

Required: owner name/email/password and business name/slug. Other fields are optional; currency defaults to `INR`. Private owner details must not become public business contact details automatically.

Example `201` response:

```json
{
  "owner": { "id": "owner_123", "full_name": "Sample Owner", "email": "owner@example.com" },
  "business": { "id": "business_123", "name": "Happy Bakery", "slug": "happy-bakery" },
  "urls": {
    "admin": "https://admin.example.com/businesses/happy-bakery",
    "storefront": "https://happy-bakery.example.com"
  }
}
```

The example uses the proposed central admin hostname. Generate URLs from trusted deployment configuration. Commit owner and business creation in one transaction; a failed registration must not leave a partial business. With wildcard DNS/HTTPS already configured, registration creates database records rather than deploying another site.

## Owner authentication

| Method | Endpoint | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/auth/csrf` | Public | Establish a CSRF token; returns `{ "csrf_token": "..." }`. |
| POST | `/auth/login` | Public + CSRF | Accept email/password, start a session, and return the owner profile. |
| GET | `/auth/me` | Owner | Return the current owner profile. |
| POST | `/auth/logout` | Owner + CSRF | Invalidate the server session and clear its cookie; return `204`. |

All four authentication endpoints are implemented. See [the B01 session contract](session-security.md) for expiry, cookie and origin rules.

### Basic authentication requests

Use the same host throughout, for example `http://127.0.0.1:8000`. Keep cookies enabled in your API client.

1. `GET /api/v1/auth/csrf` — no body. Save `csrf_token`; the response also sets the session cookie.
2. `POST /api/v1/auth/login` — send `Content-Type: application/json`, `Origin: http://127.0.0.1:8000` and `X-CSRF-Token: <csrf_token>` with an existing registered owner's credentials:

```json
{
  "email": "asha@example.com",
  "password": "a long test passphrase"
}
```

Login returns `200` with `{ "id": "owner-uuid", "full_name": "Asha", "email": "asha@example.com" }` and replaces the session cookie. Email is normalized; passwords are not trimmed. Login may replace an already authenticated session after valid credentials/CSRF checks.

3. `GET /api/v1/auth/me` — no body; send the current cookie. Returns the same profile shape. Missing, anonymous or expired sessions return `401`.
4. Before logout, call `GET /api/v1/auth/csrf` again to obtain the rotated token. `POST /api/v1/auth/logout` has **no body**; send the cookie, `Origin` and the fresh `X-CSRF-Token`. Returns `204`, revokes the server session and clears its cookie. Logging in again requires a new CSRF bootstrap.

Unknown email and wrong password both return `401 invalid_credentials`. Missing/mismatched CSRF or an untrusted origin returns `403`. Authentication responses are marked `Cache-Control: no-store`.

Login uses independently committed database counters: by default 20 attempts per network peer and 5 per normalized email in a 900-second fixed window. Validated, CSRF-verified attempts count, including successful logins; counters are not reset by logout or failed transactions. `429` includes `Retry-After`. Limits are configured with `LOGIN_PEER_RATE_LIMIT`, `LOGIN_ACCOUNT_RATE_LIMIT`, and `LOGIN_RATE_WINDOW_SECONDS`. Changing networks does not bypass the account quota; exhausting it temporarily blocks that account until the next window. Rate limits use the request client identity after explicit trusted-proxy processing; Nginx overwrites client-supplied forwarding headers. See B09 deployment settings.

Use a host-only HttpOnly session cookie, Secure in production and `SameSite=Lax`. Send `X-CSRF-Token` on all state-changing requests, including registration and login; obtain a fresh token after session rotation. Do not return session credentials in JSON or store them in browser local storage. Return a generic `401` for invalid login credentials and rate-limit authentication and registration.

Serve registration/login and owner APIs from the central admin origin; the landing-page button navigates there. Public storefronts require no owner cookies. This avoids sharing owner sessions across business subdomains.

## Admin panel

All routes below require an owner session; all mutations also require CSRF protection.

All admin routes listed below are implemented through B06. Use the cookie and mutation headers described under [authentication](#basic-authentication-requests). Admin responses are not cached. Missing and non-owned resources both return `404`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/admin/businesses` | List businesses owned by the current user, including admin/storefront URLs. |
| GET | `/admin/businesses/{business_id}` | Read business settings. |
| PATCH | `/admin/businesses/{business_id}` | Update name, description, and public contact/address fields. |
| PUT | `/admin/businesses/{business_id}/logo` | Upload or replace the business logo; multipart field `file`. |
| DELETE | `/admin/businesses/{business_id}/logo` | Remove the logo; return `204`. |
| GET | `/admin/businesses/{business_id}/products` | List all products; filter by `status=draft\|published`, optional `q`, and pagination. |
| POST | `/admin/businesses/{business_id}/products` | Create a product, initially a draft; return `201`. |
| GET | `/admin/businesses/{business_id}/products/{product_id}` | Read full product details, including drafts. |
| PATCH | `/admin/businesses/{business_id}/products/{product_id}` | Update product details or set `status` to `draft`/`published`. |
| DELETE | `/admin/businesses/{business_id}/products/{product_id}` | Delete the product and schedule image cleanup; return `204`. |
| PUT | `/admin/businesses/{business_id}/products/{product_id}/image` | Upload or replace the product's single image; multipart field `file`. |
| DELETE | `/admin/businesses/{business_id}/products/{product_id}/image` | Remove the image; return `204`. |

Product creation body:

```json
{
  "name": "Chocolate Cake",
  "description": "Fresh chocolate cake, 500 g.",
  "price": "499.00"
}
```

Require a name (1–150 characters) and a nonnegative decimal-string price from `"0"` to `"9999999999.99"` with at most two decimal places. JSON numbers are rejected to avoid floating-point ambiguity. Responses always format two decimal places. Description is optional (up to 5,000 characters). Currency comes from the business. Product responses include `id`, `business_id`, `name`, `description`, `price`, `status`, `image_url` (nullable), `created_at`, and `updated_at`. Draft is the default; publishing uses `PATCH`. Currency changes are deferred to avoid reinterpreting existing prices.

### Basic business/product requests

First `GET /api/v1/admin/businesses` to find your `business_id`. It returns the standard paginated envelope, including each business's public contact fields, logo URL, currency, timestamps and configured admin/storefront URLs. Private owner fields and disk paths are excluded. Business lists use `page`/`page_size` too.

`PATCH /api/v1/admin/businesses/{business_id}` — example JSON:

```json
{
  "name": "Happy Bakery",
  "description": "Baked fresh daily",
  "contact_email": "hello@example.com",
  "contact_phone": "+919000000001",
  "address": "Shop 12, Market Road"
}
```

`POST /api/v1/admin/businesses/{business_id}/products` — use the product creation JSON above. Save the returned `id` as `product_id`.

`PATCH /api/v1/admin/businesses/{business_id}/products/{product_id}` — example JSON:

```json
{
  "price": "549.00",
  "status": "published"
}
```

Use `{"status":"draft"}` to unpublish or `{"description":null}` to clear a description. Omitted fields stay unchanged. Empty patches and explicit null for name/price/status are rejected. Business slug/currency and all IDs, timestamps, storage paths and ownership fields cannot be edited. Nullable business description/contact/address fields may be cleared with null.

`GET /api/v1/admin/businesses/{business_id}/products?q=cake&status=published&page=1&page_size=20` searches name/description; omit status to include drafts. Search is case-insensitive, treats SQL wildcard characters literally, and accepts 1–150 trimmed characters. Page starts at 1 (maximum 1,000,000), page size is 1–100. `GET` detail and `DELETE` product need no body; deletion returns `204`.

### Image uploads

`PUT /api/v1/admin/businesses/{business_id}/products/{product_id}/image` or `PUT /api/v1/admin/businesses/{business_id}/logo` takes **multipart form data**, with a single file field named `file`. Choose the image in Swagger's file picker or your API client's form-data tab. Send the owner cookie, `Origin` and `X-CSRF-Token`; let the client generate Content-Type and its multipart boundary. There is no JSON body. The response is the updated product/business. Corresponding `DELETE` requests take no body and return `204`; removing an already absent image also succeeds.

Accept still JPEG, PNG and WebP up to 5 MiB per file and 20 megapixels. Content is decoded and re-encoded, ignoring the supplied MIME type/filename; phone orientation is applied and metadata/trailing content removed. Animated/oversized-dimension images return `422`, invalid/unsupported content `415`, and excessive file/request size `413`. The processed file must also fit 5 MiB. The multipart request limit is 5 MiB plus 64 KiB of overhead, enforced before parsing, including chunked requests.

Files use generated names under `UPLOAD_DIR/businesses/{business_id}/{random-name}.{jpg|png|webp}`. The default local root is ignored `backend/uploads`; production requires an absolute persistent root outside this checkout/deployment folder. MySQL stores relative paths only. Responses expose relative `/media/businesses/...` URLs; FastAPI serves validated, referenced files with `nosniff`, and Vite proxies `/media` locally. Public media needs no session, including for draft products. Removed/unreferenced paths return `404`; browser caches may retain previously fetched images for up to one hour. Private draft media is outside the MVP.

Replacement writes a new generated file, commits its reference, then removes the old file only if no business/logo/product references it. Mutations lock business/product rows to serialize concurrent changes. Failed database writes roll back references and clean the new file if it is unreferenced; an uncertain commit never deletes a referenced new image. Disk/DB failure during post-commit cleanup leaves an unused file and logs a generic warning, while the completed operation succeeds. B09 adds the dry-run/apply maintenance command and optional reviewed timer for expired security rows and old orphan files; nothing schedules deletion automatically in local setup.

## End customer website

No login is needed. Resolve the business from the validated storefront hostname; do not accept an arbitrary tenant header from the browser. Unknown businesses return `404`. Public pages and their `/api` requests use the same storefront origin.

B07/B08 implement all three endpoints below. The Host must be exactly `<slug>.<configured-base-domain>`, with an optional valid port. Nested, malformed, reserved and unknown names return `404`. Forwarded host/tenant headers cannot select a business. Public responses use `Cache-Control: no-store`; no owner cookie or CSRF header is needed.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/storefront` | Return business name, slug, description, logo URL, currency, and explicitly public contact/address fields. |
| GET | `/storefront/products` | List published products only; optional `q`, `page`, and `page_size`. |
| GET | `/storefront/products/{product_id}` | Return a published product belonging to the resolved business; otherwise `404`. |

Public product responses contain `id`, `name`, `description`, `price`, and `image_url`. Do not expose owner IDs, private account details, storage paths, or draft products. Scope reads and any caches to the resolved business. The configured storefront base domain controls tenant hostname resolution.

Local GET examples for a registered business with slug `happy-bakery` (no request body):

```sh
curl --resolve happy-bakery.localhost:8000:127.0.0.1 http://happy-bakery.localhost:8000/api/v1/storefront
curl --resolve happy-bakery.localhost:8000:127.0.0.1 'http://happy-bakery.localhost:8000/api/v1/storefront/products?q=cake&page=1&page_size=20'
curl --resolve happy-bakery.localhost:8000:127.0.0.1 http://happy-bakery.localhost:8000/api/v1/storefront/products/PRODUCT_ID
```

Lists use the existing page envelope and decimal-string prices. Draft, deleted, missing or another business's product IDs return `404`, even if a query parameter asks for drafts or supplies another business ID. Business profiles expose name/slug/description, public contact/address, currency and logo_url only. Local Vite forwards Host on `/api` and `/media`; use `<slug>.localhost:5173` where your OS resolves it, or add an explicit local hosts entry. This enables API routing; Vue storefront screens remain unimplemented.

B09 configuration and operational commands are described in [deployment preparation](../deploy/README.md). Start/restart local backend processes with `make dev-backend` so Uvicorn's own proxy processing is disabled; the app's explicit trusted-proxy policy handles it. Existing env files may omit `TRUSTED_PROXY_IPS` (default empty). Cleanup is dry-run by default; no production services or schedules are enabled automatically.

## Errors and existing operational APIs

API errors use a consistent envelope:

```json
{
  "error": {
    "code": "slug_unavailable",
    "message": "This website address is already taken.",
    "fields": { "business.slug": "Choose another address." }
  }
}
```

`fields` is optional. Use `401` for missing/expired sessions, `403` for CSRF rejection, `404` for missing or non-owned resources, `409` for uniqueness conflicts, `413` for oversized uploads, `415` for unsupported image formats, `422` for invalid fields, and `429` for rate limits. Never expose database errors or credentials. Add exception handlers to normalize framework validation/HTTP errors when implementing the contract.

Existing operational endpoints stay unversioned: `GET /api/health` checks the API process; `GET /api/ready` checks database connectivity and returns `503` if unavailable. Their current response format remains unchanged. Interactive API documentation is at `/api/docs` in development; production hides Swagger and OpenAPI routes.

## Implementation order and scope

1. Owner/business/product models and migrations, CSRF/session handling, then transactional registration and URL responses.
2. Owner login/logout/profile and business settings with ownership enforcement.
3. Product CRUD, publication, and image uploads.
4. Hostname-based public business and published-product endpoints.

The first version supports one owner per business and one image per product. Customer accounts, cart, orders, payment, inventory, staff roles, custom customer domains, password recovery/email delivery, and business/account deletion are deferred. Password recovery and email verification should be addressed before onboarding real users beyond the hackathon.
