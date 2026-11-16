# Implementation workflow

Build BlissBiz in small, tested iterations across backend and frontend contributors. This is an execution plan, not authorization to implement every item at once. Complete one claimed item, provide review evidence, and stop for user review before starting the next.

## Start any development session

1. Read `AGENTS.md`, `README.md`, `memory.md`, this workflow, and the relevant sections of [the API contract](api.md).
2. Read [the progress tracker](progress.md), then inspect the actual code and working-tree changes. Chat history and tracker entries alone do not establish what is implemented or accepted.
3. Identify the requested task ID and confirm its prerequisites are accepted. If no implementation task is authorized, propose the next eligible item rather than coding it.
4. Claim the item in the tracker with contributor name, branch/worktree, and files owned. For separate developers, coordinate the claim in the shared repository/PR system; an unshared local edit is not a lock.
5. Use a task branch, such as `codex/b01-session-csrf`. Use separate checkouts/worktrees for concurrent coding; do not run branch-switching commands in another contributor's checkout.
6. Run the setup steps in the README. State what is being built and how it will be verified before editing.

## Complete one iteration

1. Confirm inputs, outputs, errors, and acceptance checks against `docs/api.md`. Propose contract changes there before either side relies on them; coordinate changes with the paired contributor.
2. Implement the smallest complete slice. Keep backend routes thin and use model, repository, and service classes where useful. Keep Vue API access in the shared client.
3. Add focused behavioral tests. Use failure cases and business isolation checks, not just success paths.
4. Run the relevant checks below. Record exact commands and results, including skipped checks and limitations.
5. Update the API contract, setup instructions, and environment examples when behavior/configuration changes. Record durable environment lessons in `memory.md`.
6. Update the tracker and handoff. Set the item to `review`, link the changed files or PR, and stop. A passing test run does not mean user acceptance.
7. After explicit acceptance, record who accepted it and the review/commit reference. Follow the project's merge permissions; acceptance alone does not authorize deployment.

## Backend workstream

Paths in this table are under `backend/`. IDs are stable even if an item is later split into smaller reviewable parts.

| ID | Depends on | Implementation | Acceptance checks |
| --- | --- | --- | --- |
| B00 | — | Existing foundation: owner/business models, migration `0001`, slug policy, repository/service, and availability endpoint. | Review current code; verify normalization, reserved/taken/invalid slugs, uniqueness, safe database errors, and existing health endpoints. |
| B01 | B00 | Session and CSRF foundation: session model/migration, session repository/service, `GET /auth/csrf`, expiry, host-only cookie configuration, CSRF validation, and rotation helpers. | Anonymous CSRF bootstrap works; missing/mismatched tokens are rejected for mutations; expired sessions fail; production cookie attributes and origin checks work; anonymous sessions can be rotated safely. |
| B02 | B01 | `POST /registrations`: schemas, normalized email/slug, password hashing through a maintained library, transactional owner/business creation and session rotation, trusted URL generation, registration rate limiting. | Valid form creates one owner/business and returns URLs/session; reserved/taken slugs, duplicate emails, invalid fields, and missing CSRF fail correctly; failure rolls back all related records; passwords/session tokens never appear in responses or logs. |
| B03 | B02 | Login, logout, and current owner: `/auth/login`, `/auth/logout`, `/auth/me`; credential checks, rotation, expiry, and login rate limiting. | Generic invalid-login errors; expired/missing session gives `401`; login prevents session fixation; logout invalidates the server session; a rotated CSRF token is required afterward. |
| B04 | B03 | Owner business list/detail/update APIs; ownership dependency/service, response schemas, partial-update validation. | Owner A cannot read/update Owner B's business; only supplied editable fields change; private owner data is excluded from business responses; slug/currency cannot be changed. |
| B05a | B04 | Product model/migration, schemas, repository/service; admin product create/list/detail with search and pagination. | New products are drafts; decimal prices validate exactly; filters/page limits work; owner/business/product boundaries are enforced on every query; cross-business IDs give `404`. |
| B05b | B05a | Product update/delete and draft/published transitions; product/image cleanup coordination points. | PATCH preserves omitted fields; invalid prices/statuses fail; publication behaves consistently; non-owners cannot modify/delete; deletion cannot affect another business. |
| B06 | B05b | Persistent image storage service; business logo and product image PUT/DELETE endpoints; validated public image serving and cleanup. | JPEG/PNG/WebP and 5 MiB rules are checked against actual content; ownership/path traversal tests pass; failed replacement preserves the old image; cleanup respects DB commit/rollback and shared file references. |
| B07 | B04 | Trusted hostname configuration/resolution and `GET /storefront`; separate public response schema. May run independently of product work after dependencies are accepted. | Known host resolves its business; unknown/malformed hosts return `404`; arbitrary tenant/forwarded headers cannot bypass host validation; only explicitly public fields are exposed. |
| B08 | B05b, B07 | Public product list/detail, search/pagination, and published-only filtering. | Draft/deleted/other-business products return no data; direct product IDs cannot cross host boundaries; list/detail agree; responses expose no private account or storage fields. |
| B09 | B06, B08 | Backend integration and deployment preparation: trusted proxy handling, rate-limit behavior, production settings, Nginx `/api` and media configuration, persistence/backup instructions. Prepare configuration without deploying. | Local multi-host smoke checks pass; HTTPS/proxy assumptions are documented; errors are consistent; production startup/config validation and persistence are verified in a safe environment. |

All backend paths above are relative to `/api/v1`, except the existing operational endpoints. The complete endpoint list and payloads remain in `docs/api.md`.

B01 must define the session/CSRF contract before B02 or frontend authentication integration starts: anonymous versus authenticated sessions, expiry, cookie scope, token rotation, accepted origins, and expected error responses. Library choices and any major dependencies require discussion under `AGENTS.md`; do not implement password hashing yourself.

B02 and B03 must define the rate-limit storage/identity/window and test reset behavior. Prefer a solution compatible with the chosen single-VPS setup; any additional service requires agreement. Do not label authentication complete while these controls are missing.

## Frontend workstream

Paths are under `frontend/src/`. Mocked UI may be prepared against the agreed contract before an API is ready, but mark it explicitly; integrated acceptance requires the listed backend dependency.

| ID | Depends on for integrated acceptance | Implementation | Acceptance checks |
| --- | --- | --- | --- |
| F00 | — | Existing Vue/Vite/Router foundation, shared GET client, and development connection-status page. | Review startup, build, health/readiness display, and `/api` proxy behavior. |
| F01 | F00 | Public landing page and “Start a business today” navigation; retain a reachable development diagnostics route. | Responsive layout, keyboard navigation, clear CTA, and correct navigation to the admin registration origin. No business mutation occurs here. |
| F02 | F00, B01 | Extend shared client for JSON mutations, multipart uploads, `204`, structured errors, session cookies, and CSRF; add a small reactive owner-session composable. | JSON and empty responses work; CSRF bootstrap/rotation/error handling match B01; passwords/tokens are not persisted; redirects do not cause loops; multipart boundaries are browser-generated. |
| F03 | F01, F02, B02 | Registration form, slug availability feedback, field errors, pending/duplicate-submit handling, and success page displaying both URLs. | Availability requests cannot overwrite newer input with stale results; `409` after a positive check is handled; private owner/public business fields are separate; real registration completes through the API. |
| F04 | F02, B03 | Login page, logout, session restoration with `/auth/me`, and admin route guards. | Refresh restores a valid session; expired sessions return to login cleanly; no client-only authorization assumption; passwords are cleared after submission and never logged. |
| F05 | F04, B04 | Admin shell, owned-business navigation, settings view/edit, loading/empty/error states. | Routes resolve slug to an authorized business ID; unknown/non-owned businesses show a safe error; saves update the UI; slug/currency remain read-only. |
| F06a | F05, B05a | Product list/search/pagination and product creation form. | Draft creation works; decimal prices remain strings in requests; empty/loading/error states are usable; navigation uses the current business. |
| F06b | F06a, B05b | Product editing, publication controls, and explicit delete confirmation. | Partial edits preserve untouched fields; failed saves retain edits; publish/unpublish/delete update list and detail state; duplicate submissions are prevented. |
| F07 | F05, F06b, B06 | Logo/product image selection, preview, replace/remove, and upload feedback. | File errors are shown inline; failed replacement preserves the current image; temporary preview URLs are released; refresh shows persisted images. |
| F08 | F01, B07, B08 | Host-based storefront routing, business profile, product grid/search/pagination, product detail, and unknown-store page. | Correct business appears for each host; no admin/private information is rendered; drafts stay hidden; direct URL refresh works; content renders as text rather than unsafe HTML. |
| F09 | F03, F04, F05, F06b, F07, F08, B09 | Full browser integration, mobile/accessibility pass, and production build/deep-link checks. | Complete the shared end-to-end checks below using real APIs and two businesses; document any gaps before accepting the MVP. |

Reuse Vue Composition API and the shared client. Do not add a state manager, UI framework, or test framework implicitly. Select missing frontend lint/format/test tooling as a small agreed task before relying on automated browser/component checks; those checks do not exist in the current scaffold.

## Coordination and safe parallel work

- Backend owner: the claimed task's `backend/app/` modules, migration, and focused backend tests.
- Frontend owner: the claimed task's components/views/composables and API integration in `frontend/src/`.
- One integration owner at a time: shared API contract, router entry points, `AGENTS.md`, README, Makefile, environment examples, and deployment configuration. Coordinate edits rather than overwriting them.
- Claim shared files explicitly. `backend/app/db/models.py`, `backend/app/main.py`, `frontend/src/router/index.js`, `frontend/src/api/client.js`, and lockfiles are likely collision points.
- One migration author at a time. Check the current Alembic head before creating a revision; do not rewrite an applied revision or independently assign the same revision ID. Coordinate divergent heads before merge.
- Use separate local databases/Compose project names and ports for simultaneous backend work against different schema versions. Never run competing migrations against the same development database. Verify backend `DATABASE_URL` matches the intended container.
- Contract-ready UI can proceed alongside backend work using clearly identified fixtures. Replace fixtures before integration acceptance; do not mark a mock-backed screen as integrated.
- Use the branch/PR as the durable code reference. Worktree paths are local hints, not portable references. Do not revert or clean another contributor's changes.
- This workflow does not automatically launch agents, create chats, send messages, or assign people. Those actions need the corresponding user request/authorization.

Suggested first concurrent pair after review: B01 (backend session/CSRF foundation) and F01 (landing page). F02 integration follows the accepted B01 contract. B05 and B07 may later proceed in separate checkouts after coordinating their shared files.

## Local and deployment assumptions

The proposed production layout remains the one in the API contract: root domain for the landing page, `admin.<domain>` for registration/login/dashboard, and `<slug>.<domain>` for public storefronts. A nested `admin.<slug>.<domain>` layout requires a separate domain/certificate decision before implementation.

For local multi-host development, plan to use `localhost:5173`, `admin.localhost:5173`, and `<slug>.localhost:5173`. B01/B07/F01 must align their trusted origins, generated URLs, Vite host handling, and host routing. Verify name resolution on each machine and document explicit hosts-file entries if needed. B07 now enables backend API hostname resolution and Vite Host forwarding; Vue storefront host routing/screens remain F08 work.

Use relative `/api` calls on each UI origin. Nginx/Vite must preserve the intended storefront host; the backend must trust forwarded host information only from explicitly trusted proxies. Do not enable wildcard credentialed CORS or share owner-session cookies with storefront hosts.

## Verification checkpoints

| Scope | Current commands/checks |
| --- | --- |
| Standard project gate | `make check` — Python lint/format/tests and frontend production build. |
| Local MySQL integration | `make db-up`, `make db-migrate`, then `make test-mysql`; use only a local development `DATABASE_URL`. |
| Backend manual check | Start `make dev-backend`; inspect `/api/docs` and `/api/ready`; exercise success and error responses. |
| Frontend manual check | Start `make dev-frontend`; verify browser behavior, network requests, loading/errors, and narrow-screen/keyboard usability. A successful build alone does not prove UI behavior. |
| Migration change | Review generated SQL/schema and constraints, apply to a safe development database, run Alembic drift check and affected tests. Test destructive rollback only with explicit authorization and disposable data. |

At F09, demonstrate: register Business A → receive URLs → add draft product → upload image → publish → view on A's public host → edit/unpublish → confirm public removal → logout/login. Repeat with Business B and verify A cannot access B's admin resources or products. Check draft/public separation, duplicate registration, expired sessions, rejected CSRF, unknown hosts, failed uploads, and direct page refreshes.

Do not run tests or migrations against production. Do not delete a MySQL volume to resolve credential/migration problems. Prepare deployment changes for review; deployment needs explicit authorization.

## Review and new-chat handoff

The tracker is the durable work queue. Use its handoff template for every paused or review-ready task. Include what changed, exact evidence, remaining work, unresolved decisions, and the next eligible item. Link code rather than reproducing large code excerpts in chat.

A new contributor should be able to resume from repository files plus the task's branch/PR without reading the previous chat. If the tracker disagrees with code or review evidence, record and resolve that mismatch before marking anything complete.

Deferred MVP scope remains in `docs/api.md`: checkout, orders, customer accounts, payments, inventory, staff roles, custom domains, account/business deletion, and recovery/email delivery. Do not expand these implicitly.
