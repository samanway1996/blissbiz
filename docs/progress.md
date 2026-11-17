# Implementation progress

Use this file with [the workflow](implementation-workflow.md) and [the API contract](api.md). Update only the rows and handoff belonging to the task you own; coordinate shared tracker edits before integration.

## Status rules

- `planned`: not started; prerequisites or authorization may still be pending.
- `in_progress`: claimed with a named contributor and branch/checkpoint.
- `review`: implementation and verification evidence are ready; awaiting user acceptance.
- `accepted`: explicit acceptance recorded with reviewer and reference.
- `blocked`: record the exact dependency or missing decision and the last safe checkpoint.

Code completion, user acceptance, and merging are separate facts. Record merge references in the evidence/handoff; do not infer acceptance from tests, silence, or a status question.

## Work queue

| ID | Deliverable | Status | Owner and branch | Evidence or blocker |
| --- | --- | --- | --- | --- |
| B00 | Models, initial migration, slug availability | accepted | Codex; reviewed by project owner | Foundation included in the final backend verification (474 SQLite/MySQL tests). Accepted by the user on 2026-11-17; see backend acceptance record below. |
| F00 | Vue/Vite starter and API connection page | review | Initial implementation; claim review owner | Starter exists in `frontend/`; previous production build passed. No explicit acceptance recorded. |
| B01 | Session and CSRF foundation | accepted | Codex; `codex/b01-session-csrf` | Migration 0002 applied; `make check` passed (72 tests + lint/format/build), `make test-mysql` passed (130 tests), real-app in-process smoke and Alembic drift check passed. See handoff below. |
| B02 | Transactional business registration | accepted | Codex; `codex/b02-registration` | Migration 0003 applied; project checks passed (109 tests; 1 opt-in test skipped), MySQL suite 195 passed; real-app registration/quota rollback checks passed. See handoff below. |
| B03 | Login/logout/current owner | accepted | Codex; `codex/b03-owner-auth` | Project checks: 127 passed, 1 expected MySQL-only skip; MySQL suite: 231 passed. Login rotation, revocation, generic failures, owner isolation, quota and rollback checks pass. |
| B04 | Owner business APIs | accepted | Codex; `codex/b04-b06-catalog-images` | Owned business list/detail/PATCH; cross-owner isolation and validation checked on SQLite/MySQL. See combined handoff. |
| B05a | Product create/list/detail | accepted | Codex; `codex/b04-b06-catalog-images` | Migration 0004 applied; exact decimal prices, draft defaults, search/pagination and tenant boundaries pass. |
| B05b | Product edit/delete/publication | accepted | Codex; `codex/b04-b06-catalog-images` | Partial updates, publish/unpublish, deletion, rollback and image cleanup checks pass. |
| B06 | Logo and product images | accepted | Codex; `codex/b04-b06-catalog-images` | Validated uploads, persistent root configuration, public media and transaction-aware cleanup pass; combined MySQL suite 403 tests. |
| B07 | Host resolution and public business profile | accepted | Codex; `codex/b07-b09-storefront-deploy` | Strict Host resolution and public-only profile; malformed/unknown/forwarded-host cases pass. |
| B08 | Public product catalog | accepted | Codex; `codex/b07-b09-storefront-deploy` | Published-only, tenant-scoped list/detail/search/pagination; draft, deleted and cross-business IDs return 404. |
| B09 | Backend integration and deployment preparation | accepted | Codex; `codex/b07-b09-storefront-deploy` | 474 SQLite/MySQL tests; isolated verified-HTTPS Nginx/two-worker integration, restart persistence and backup/restore passed. No production deployment. |
| F01 | Landing page and CTA | planned | Unassigned | After F00 acceptance and authorization. |
| F02 | Shared client and session handling | planned | Unassigned | F00, B01. |
| F03 | Registration form and success page | planned | Unassigned | F01, F02, B02. |
| F04 | Login/logout and protected navigation | planned | Unassigned | F02, B03. |
| F05 | Business admin/settings | planned | Unassigned | F04, B04. |
| F06a | Product listing and creation | planned | Unassigned | F05, B05a. |
| F06b | Product editing and publication | planned | Unassigned | F06a, B05b. |
| F07 | Image management UI | planned | Unassigned | F05, F06b, B06. |
| F08 | Public storefront UI | planned | Unassigned | F01, B07, B08. |
| F09 | Full browser integration and MVP review | planned | Unassigned | F03–F08, B09. |

## Open decisions

Resolve each when its task is claimed; none blocks reviewing the existing implementation.

| Decision | Resolve before |
| --- | --- |
| B01 defines 15-minute anonymous/8-hour owner sessions, rotation, exact admin origins, and secure production cookies; review [the contract](session-security.md) | B01 acceptance |
| SQL-backed fixed-window limits: registration 5 per peer; login 20 per peer and 5 per normalized account, each per 900 seconds by default. See [API configuration](api.md#basic-authentication-requests). | Review limits and actual proxy addresses before production; B09 handling is implemented. |
| Frontend component library, if any; otherwise continue with existing CSS | F01 implementation |
| Frontend lint/format and automated UI testing tools | Adding those checks; discuss dependencies first |
| Central admin and slug-based API host routing are implemented; confirm the real production domain and verify local DNS on each OS | F01 navigation/B01 origin integration, finalized by B07 |
| Persistent storage and validation are implemented; B09 adds dry-run/apply expired-security/orphan cleanup and optional service/timer examples. Nothing schedules local deletion automatically. | Production maintenance/backup setup before deployment |
| Exact GoDaddy product, production domain, DNS/HTTPS, proxy, and backup setup | B09 preparation; deployment requires separate authorization |

## Handoff template

Copy this section for the task being handed off. Keep one current handoff per task; preserve review/commit links when updating it. Never include secrets, cookie values, real owner data, or complete environment files.

```text
Task ID and objective:
Status: planned | in_progress | review | accepted | blocked
Contributor:
Branch / PR / commit (or explicitly uncommitted):
Local checkout path (optional):
Owned files / shared-file coordination:
Prerequisites and acceptance references:
Implemented behavior:
API/schema/configuration changes:
Migration head and local DB setup (no credentials):
Verification commands and actual results:
Skipped checks / known limitations:
Unresolved decisions or blockers:
Exact remaining work in this task:
Review instructions and expected results:
Acceptance: pending, or reviewer + explicit reference
Merge reference: pending, or commit/PR
Next eligible task (requires authorization):
```

## Current checkpoint

Backend tasks B00–B09 (including B05a/B05b) are accepted by the project owner on 2026-11-17. Backend APIs, proxy handling, maintenance and deployment preparation are implemented and locally verified. Frontend statuses are unchanged: F00 awaits review and F01–F09 remain planned. Schema head remains 0004. Production deployment, service installation and offsite backup configuration remain separate work; further implementation requires a user request.

## Backend acceptance record — 2026-11-17

- Reviewer: project owner (user).
- Reviewed repository checkpoint: `0beede6` (`Backend implementation completion`) on `codex/b07-b09-storefront-deploy`.
- Scope: B00, B01, B02, B03, B04, B05a, B05b, B06, B07, B08 and B09.
- Explicit review reference: user message in this project chat, “I have reviewed backend changes, it can be marked now”.
- Result: all backend work-queue items above are `accepted`. This accepts the implemented backend and deployment preparation; it does not authorize deployment or change frontend review statuses.
- Verification evidence remains the recorded B09 checkpoint: 474 SQLite/MySQL tests, project checks and isolated HTTPS/Nginx backup/restore verification. This status-only update does not claim a new test run.
- Historical handoffs below preserve their original implementation-time status and references. Any pending backend acceptance language in those snapshots is superseded by this record. Commit/merge/deployment state remains separate from acceptance.

## B01 handoff

Historical B01 checkpoint; the B02 handoff below describes the current implementation.

- Task/status: B01 session and CSRF foundation; `review`, acceptance pending.
- Contributor/reference: Codex; branch `codex/b01-session-csrf`, uncommitted. The repository also contains the earlier uncommitted scaffold; do not assume all untracked files belong to B01.
- Prerequisite: user explicitly requested implementation of B01. This does not mark B00 or F00 accepted.
- Owned changes: `backend/app/api/auth.py`, `session_dependencies.py`, `session_cookies.py`; core config/origin/error modules; `BrowserSession` model and session repository/service; CSRF schema; API registration/error handlers; migration `0002`; `backend/tests/test_sessions.py`; backend environment example; session contract, README/API docs, and this tracker.
- Behavior: one new public endpoint, `GET /api/v1/auth/csrf`; anonymous/owner session lifecycle and reusable origin/CSRF/owner dependencies; atomic rotation/revocation helpers; consistent cookie issuance/removal. No production diagnostic mutation routes.
- Database/config: local MySQL migration head `0002`; no schema drift. New optional settings and defaults are documented in `backend/.env.example` and `docs/session-security.md`; existing local `.env` is preserved.
- Verification: `make check` passed with 72 tests, Ruff lint/format, and Vue production build. `make test-mysql` passed with 130 tests across SQLite/MySQL. Alembic `check` found no pending changes. Real production-app wiring was smoke-tested in-process against MySQL; its session was rolled back, and the database retained no test sessions.
- Existing warning: Starlette reports deprecation of its httpx-backed TestClient. It does not fail tests; no dependency/tool change was introduced here.
- Runtime: no backend server was started/stopped for B01; the user controls their backend terminal. No production deployment or destructive rollback was performed.
- Scope left for later: registration and password hashing/rate limiting (B02), login/logout/profile (B03), cleanup scheduling and production proxy/deployment integration (B09). Revocation/cleanup helpers exist but are not public endpoints or scheduled jobs.
- Review: follow [the B01 review steps](session-security.md#review-b01); inspect session service, repository, request dependencies, cookie helper, and security tests. Defaults and production configuration are part of the review.
- Acceptance/merge: pending; no commit, PR, or merge created.
- Next eligible backend task after B01 acceptance and authorization: B02. Frontend F02 can integrate against the documented B01 contract once accepted.

## B02 handoff

- Task/status: B02 transactional owner/business registration; `review`, acceptance pending.
- Contributor/reference: Codex; branch `codex/b02-registration`, uncommitted. Earlier uncommitted scaffold/B00/B01 files remain present; do not attribute all untracked files to this slice.
- Authorization: user requested the next implementation after B01. Earlier acceptance statuses are preserved.
- Owned changes: registration request/response schemas, endpoint/service, owner repository and business insert helper, password service, URL builder, shared quota service/repository and isolated pool, uniqueness-error helper, error-envelope extensions, settings/environment example, rate model/migration `0003`, new registration/rate tests, transaction-safe test fixture, dependency declarations/lock, and related documentation.
- Behavior: valid CSRF/origin-protected registration atomically creates an owner/business, hashes the password with Argon2id, rotates the anonymous session, returns trusted configured URLs, and issues the owner cookie only after commit. Existing-owner registration, duplicates, malformed fields, and uniqueness races have safe errors. Private owner contact details do not become public business fields automatically.
- Quota: 5 schema-valid/CSRF-verified submissions per network peer per 900-second fixed window by default, persisted in independent MySQL transactions and a separate bounded connection pool. Concurrent workers share the quota; failed registration does not reset it. `429` includes Retry-After. Counter upserts and uniqueness-code classification are explicitly isolated dialect-specific code.
- Database/dependencies: local migration head `0003`, no schema drift. Added `argon2-cffi` and `email-validator` and locked their transitive dependencies. `pip check` passed. Existing `.env` files/business data were preserved; new optional settings are in `backend/.env.example`.
- Verification: `make check` passed: 109 tests, 1 expected MySQL-only concurrency skip, Ruff lint/format, and Vue build. `make test-mysql` passed: 195 tests across SQLite/MySQL, including committed concurrent quota checks. A real-app in-process registration smoke check passed with the actual quota provider; rollback removed its owner/business/session writes while quota consumption remained committed, then only its unique counter was cleaned up. No backend process was started/stopped.
- Test isolation: request sessions join outer fixture transactions using savepoints so route rollback preserves setup sessions/fixtures. Rate-limit route tests use a separate committed SQLite store; the MySQL suite additionally verifies native upserts and independent workers. Business test records remain rolled back.
- Existing warning: Starlette's TestClient reports an httpx deprecation; no test fails because of it.
- Scope/limitations: returned dashboard/storefront URLs do not yet have business UIs or tenant routing. Login/logout/profile is B03. Email verification, recovery, cleanup scheduling, production proxy handling and hosting remain later work. No deployment or destructive migration rollback was performed.
- Review: [B02 review guide](registration.md#review-b02); install locked dependencies, migrate, then use the same-origin Swagger CSRF bootstrap and POST registration flow. Manual review creates local records intentionally; automated tests do not leave business records behind.
- Acceptance/merge: pending. No commit, PR, or merge created.
- Next backend task after acceptance and authorization: B03. Frontend F03 can consume registration after F01/F02 and contract acceptance.


## B03 handoff

- Status/reference: review; Codex, `codex/b03-owner-auth`, uncommitted changes after base `a9d01a3`. User authorized this next slice and requested basic documentation with request bodies.
- Scope: authentication routes/service/schemas, owner lookup helpers, shared fixed-window quota base and login quotas, optional settings/environment example, 18 focused authentication tests, and updates to existing API/README/status documentation. No new verification document, dependency or migration.
- Behavior: login returns a minimal owner profile, rotates cookie/session/CSRF after credential verification and commit, and uses generic invalid-credential errors with dummy Argon2 verification for unknown accounts. `/auth/me` derives the owner solely from the cookie. Logout revokes the server record and clears the cookie after commit. Failed commits preserve the prior session and emit no credential cookie.
- Quota: independently committed counters through the existing dedicated pool; defaults 20 attempts per network peer and 5 per normalized account per 900-second window. Successes and failures count. Account quota applies across peers; new CSRF sessions or forwarded IP headers do not reset it. `429` includes Retry-After. Proxy trust/cleanup scheduling remain B09.
- Verification: `make check` passed (127 tests, 1 expected opt-in MySQL skip; Ruff lint/format and Vue build). `make test-mysql` passed (231 tests across SQLite/MySQL). Existing TestClient deprecation warning remains. Tests cover session/CSRF rotation and replay, expiry, cookie-owner isolation, login/logout origin/CSRF checks, generic failures, rollback, normalized account/peer throttling, window reset and successful-login quota consumption.
- Runtime/data: no backend process started or stopped; no schema or dependency changes. Business/session test writes roll back using existing fixtures. No deployment.
- Usage: [basic authentication requests](api.md#basic-authentication-requests) provides the login JSON and headers. GET me and POST logout take no body.
- Acceptance/merge: pending; no commit or PR created for B03. Next backend slice is B04, only upon user request.


## B04–B06 combined handoff

- Status: review, acceptance pending. User explicitly requested implementation through B06 before review. No B07/B08 or business frontend implementation.
- Reference: Codex, `codex/b04-b06-catalog-images`, uncommitted. Branch carries earlier uncommitted B03 work; do not attribute every changed/untracked file to this slice.
- Owned scope: admin routes; catalog schemas/repositories/service; Product model and migration 0004; image storage/media repository/service/routes and bounded-upload middleware; settings, environment example, locked dependencies, application router, Vite media proxy; shared catalog fixture and catalog/image tests; basic examples in existing API/README documentation. No separate verification guide created.
- Behavior: paginated owned business list/detail/PATCH, immutable slug/currency; tenant-scoped product create/list/detail/PATCH/delete, string-decimal prices, draft/published states and literal case-insensitive search. Reads require an owner and mutations require CSRF/origin verification; missing and non-owned IDs return 404. Mutations lock business/product rows and refresh persisted values before responses.
- Images: still JPEG/PNG/WebP, at most 5 MiB and 20 MP; generated paths, decoding/re-encoding, orientation correction and metadata removal; bounded multipart requests; public referenced-only media with nosniff. Replacement/delete cleanup runs after commit and checks all product/logo references. Rollback removes unreferenced new files; uncertain commits preserve referenced new files. Shared paths, unsafe paths/symlinks, failed writes and name collisions are covered.
- Storage/config: default ignored backend/uploads; production requires an absolute UPLOAD_DIR outside the deployment directory. Preserve the root across releases and back it up with MySQL. Vite proxies /media; production Nginx/backup configuration remains B09. Added Pillow 13.0.0 and python-multipart 0.0.34, declared and locked. No existing local environment files were overwritten.
- Database: additive migration 0004 creates products with business FK, indexes, price/status checks and Numeric(12,2). Applied locally; Alembic current reports 0004 and check reports no drift. No destructive downgrade or business-data deletion.
- Verification: make check passed (214 tests, 1 expected MySQL concurrency skip, Ruff lint/format and Vue build); make test-mysql passed (403 tests across SQLite/MySQL). pip check passed; documentation links/JSON examples and portable lock validated. Existing TestClient deprecation warning remains.
- Integration: real-app in-process MySQL flow passed registration, business settings, product creation, logo/image upload and serving, publication/filtering, media/product deletion, logout/login. Outer rollback removed smoke business/session writes, temporary media was removed, and only that run's uniquely keyed committed security counters were cleaned. Your backend process was not started/stopped.
- Known limits: post-commit cleanup failures log a generic warning and leave an unused file; retry/reconciliation after disk failure or process crash is B09 work. Previously fetched public images may remain in browser caches for up to one hour. Public storefront/catalog pages are still unimplemented.
- Usage: docs/api.md contains business/product JSON bodies, list/filter examples and multipart file-field instructions; /api/docs exposes the implemented routes. For a new contributor: make setup, make db-migrate, then start their own backend terminal.
- Acceptance/merge: pending user review; no commit, PR, merge or deployment created. Next backend slice is B07 only after authorization.


## B07–B09 handoff

- Status/reference: review; Codex, `codex/b07-b09-storefront-deploy`, uncommitted after `66bd5c5`. User authorized implementation through B09. Earlier acceptance statuses are preserved.
- Owned scope: storefront schemas/service/routes; published-product and slug repository queries; proxy settings/application factory; maintenance repository/service/CLI and focused tests; Nginx/systemd/environment examples, optional backend Dockerfile and disposable integration Compose stack; backup and deployment-test scripts; Vite hostname access, Make targets and basic API/setup/deployment documentation. No new framework/dependency or schema migration.
- B07/B08 behavior: actual Host selects one validated slug directly beneath the configured base domain; unknown/malformed/reserved/nested names return 404. Forwarded host/tenant headers cannot select a business. Public profiles and product schemas expose explicit public fields only. Product lists/detail enforce published status and business ID in SQL; search/pagination retain existing limits and decimal-string formatting. Responses are not shared-cached; public GETs need no session/CSRF. Vue storefront screens remain unimplemented.
- Proxy/production behavior: default TRUSTED_PROXY_IPS is empty; explicit validated IP/networks only. Uvicorn's application middleware performs one trusted proxy pass; launch commands disable the server's implicit proxy processing. Nginx overwrites forwarded client/protocol headers, preserves Host, proxies API/media and serves the Vue build with deep-link fallback. Production Swagger/OpenAPI routes are disabled. Restart an older local backend using make dev-backend to adopt the new launch flag.
- Maintenance: dry-run by default; --apply removes expired sessions/counters and generated, unreferenced image files older than the grace period (default 24 hours). A fresh transaction and the upload business lock precede each reference recheck. Recent/referenced/unknown files and symlinks are preserved; removal errors are counted. The optional daily timer is a configuration artifact, not installed/enabled.
- Backup: scripts/backup.sh requires explicit --writes-paused and new private destination outside uploads; dumps the Compose database, archives images and writes checksums. Pause writes/maintenance yourself; the script never stops the current application. Copy completed backups off the VM. No production backup destination/scheduler was configured.
- Verification: make check passed (254 tests, one expected opt-in skip, lint/format including the deployment script, Vue build); make test-mysql passed (474 tests). Alembic check has no drift; head remains 0004. The local maintenance preview succeeded with apply=false. Existing TestClient deprecation warning remains.
- Deployment integration: isolated Nginx + two Uvicorn workers + fresh MySQL, using verified local TLS, passed config validation, frontend deep links, secure host-only cookies, registration, two businesses with owner/public isolation, draft/published transitions, image serving, logout/login and shared quotas despite spoofed forwarding. Media persisted across a backend restart. With this test backend stopped, the backup script created checksummed SQL/images; both restored into a new disposable database/folder with expected rows/images. Only generated test-project containers/volumes were removed; the normal blissbiz MySQL stayed healthy and the user's backend process was untouched.
- Local environment finding: Docker Hub's CloudFront certificate chain was rejected even outside the sandbox. Verified Google Docker Hub mirror images worked via test-only image overrides; no TLS verification, daemon trust store or global runtime setting was changed. Docker build metadata required scoped escalation on this Mac.
- Limits/external verification: real GoDaddy domain/DNS, public certificate issuance/renewal, firewall and systemd installation, off-VM backup delivery and final host-specific paths still require the intended VPS and deployment authorization. ARM64 local container verification does not certify the eventual server environment.
- Usage: docs/api.md has public GET/curl examples; deploy/README.md documents configuration, maintenance, backups/recovery and the reproducible make test-deployment check. No separate verification document was created.
- Acceptance/merge: pending; no commit, PR, merge or production deployment created. Frontend remains its development starter; choose a frontend slice only on user request.
