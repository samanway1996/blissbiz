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
| B00 | Models, initial migration, slug availability | review | Initial implementation; claim review owner | Files exist in `backend/`; previous run reported 49 tests across SQLite/MySQL plus project checks. Re-run before accepting; no explicit acceptance recorded. |
| F00 | Vue/Vite starter and API connection page | review | Initial implementation; claim review owner | Starter exists in `frontend/`; previous production build passed. No explicit acceptance recorded. |
| B01 | Session and CSRF foundation | review | Codex; `codex/b01-session-csrf`, uncommitted | Migration 0002 applied; `make check` passed (72 tests + lint/format/build), `make test-mysql` passed (130 tests), real-app in-process smoke and Alembic drift check passed. See handoff below. |
| B02 | Transactional business registration | review | Codex; `codex/b02-registration`, uncommitted | Migration 0003 applied; project checks passed (109 tests; 1 opt-in test skipped), MySQL suite 195 passed; real-app registration/quota rollback checks passed. See handoff below. |
| B03 | Login/logout/current owner | planned | Unassigned | B02. |
| B04 | Owner business APIs | planned | Unassigned | B03. |
| B05a | Product create/list/detail | planned | Unassigned | B04. |
| B05b | Product edit/delete/publication | planned | Unassigned | B05a. |
| B06 | Logo and product images | planned | Unassigned | B05b. |
| B07 | Host resolution and public business profile | planned | Unassigned | B04. |
| B08 | Public product catalog | planned | Unassigned | B05b, B07. |
| B09 | Backend integration and deployment preparation | planned | Unassigned | B06, B08. |
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
| B02 uses Argon2id and SQL-backed registration limits of 5 attempts/900 seconds; review [the contract](registration.md). Login-specific throttling remains B03 work. | B02 acceptance / B03 implementation |
| Frontend component library, if any; otherwise continue with existing CSS | F01 implementation |
| Frontend lint/format and automated UI testing tools | Adding those checks; discuss dependencies first |
| Confirm central admin hostname and verify local subdomain routing on each OS | F01 navigation/B01 origin integration, finalized by B07 |
| Persistent upload paths, image validation library, and cleanup strategy | B06 implementation |
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

Implementation is paused after B02. Slug availability, session/CSRF foundations, and transactional registration are implemented. Login/logout/profile, admin catalog, and storefront APIs remain unimplemented; the frontend remains a development status page. No production deployment has been performed. The user explicitly authorized each next slice without separate acceptance records, so earlier review statuses remain unchanged. B03 requires review and further authorization.

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
