# BlissBiz API plan

Contract for the hackathon MVP: register a business, manage its catalog through an owner dashboard, and display published products on a public storefront. B00 implements slug availability; B01 implements CSRF/session foundations; B02 implements registration. `/api/health` and `/api/ready` also exist. Login/logout/profile, admin, and storefront endpoints remain planned.

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

`GET /auth/csrf` is implemented; login/logout/profile are planned. See [the B01 session contract](session-security.md) for exact expiry, rotation, cookie/origin rules, dependencies, configuration, and review instructions.

Use a host-only HttpOnly session cookie, Secure in production and `SameSite=Lax`. Send `X-CSRF-Token` on all state-changing requests, including registration and login; obtain a fresh token after session rotation. Do not return session credentials in JSON or store them in browser local storage. Return a generic `401` for invalid login credentials and rate-limit authentication and registration.

Serve registration/login and owner APIs from the central admin origin; the landing-page button navigates there. Public storefronts require no owner cookies. This avoids sharing owner sessions across business subdomains.

## Admin panel

All routes below require an owner session; all mutations also require CSRF protection.

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

Require a name and nonnegative price with at most two decimal places. Currency comes from the business. Product responses include `id`, `business_id`, `name`, `description`, `price`, `status`, `image_url` (nullable), `created_at`, and `updated_at`. Draft is the default; publishing uses `PATCH`. Currency changes are deferred to avoid reinterpreting existing prices.

For uploads, accept JPEG, PNG, and WebP up to 5 MiB per file. Validate actual file content, use generated filenames, and return the updated resource with its public image URL. Attach files only to an owned resource. Failed uploads must preserve the existing image; replacement/deletion cleanup must not remove another resource's files. Uploaded images are public assets, including images attached to draft products; private draft media is outside the MVP.

## End customer website

No login is needed. Resolve the business from the validated storefront hostname; do not accept an arbitrary tenant header from the browser. Unknown businesses return `404`. Public pages and their `/api` requests use the same storefront origin.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/storefront` | Return business name, slug, description, logo URL, currency, and explicitly public contact/address fields. |
| GET | `/storefront/products` | List published products only; optional `q`, `page`, and `page_size`. |
| GET | `/storefront/products/{product_id}` | Return a published product belonging to the resolved business; otherwise `404`. |

Public product responses contain `id`, `name`, `description`, `price`, and `image_url`. Do not expose owner IDs, private account details, storage paths, or draft products. Scope reads and any caches to the resolved business. Local tenant hostname configuration will be added with storefront routing.

## Errors and existing operational APIs

Planned errors use a consistent envelope:

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

Existing operational endpoints stay unversioned: `GET /api/health` checks the API process; `GET /api/ready` checks database connectivity and returns `503` if unavailable. Their current response format remains unchanged. Interactive API documentation is at `/api/docs` and will reflect endpoints as they are implemented.

## Implementation order and scope

1. Owner/business/product models and migrations, CSRF/session handling, then transactional registration and URL responses.
2. Owner login/logout/profile and business settings with ownership enforcement.
3. Product CRUD, publication, and image uploads.
4. Hostname-based public business and published-product endpoints.

The first version supports one owner per business and one image per product. Customer accounts, cart, orders, payment, inventory, staff roles, custom customer domains, password recovery/email delivery, and business/account deletion are deferred. Password recovery and email verification should be addressed before onboarding real users beyond the hackathon.
