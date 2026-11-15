## [2026-11-15] Local Vue and FastAPI runtimes
Context: BlissBiz development on macOS.
Signal: Global Node 21.6.2 cannot start because ICU 73 is missing; default pyenv Python is 3.9.6.
Root cause: Existing global runtimes are broken or older than this project's requirements.
Fix: Use verified official Node 24 from ignored `.tools/node` through `scripts/npm.sh`; use Homebrew Python 3.13 at `/opt/homebrew/opt/python@3.13/bin/python3.13` to create `backend/.venv`. The npm wrapper uses a project-local cache after the default cache rejected writes. Keep global runtimes unchanged.
Verification: `make setup`, Python checks and tests, Vue build, and live FastAPI-to-MySQL readiness through Vite passed. MySQL runs through Rancher Desktop on localhost port 3307.
Reuse hint: Use the Make targets and README; do not invoke global npm directly on this Mac. Never delete the MySQL volume to resolve credential drift.

## [2026-11-15] Backend reload needs file polling
Context: BlissBiz local FastAPI development.
Signal: The running reload-enabled backend continued returning 404 for a newly added route even though in-process API tests passed.
Root cause: Native file watching did not pick up the edits in this session; the underlying watcher failure was not established.
Fix: Enable `WATCHFILES_FORCE_POLLING=true` in `make dev-backend` and restart the existing development server.
Verification: Live API and Vite-proxied requests passed; touching `app/main.py` then triggered an automatic reload with the polling configuration.
Reuse hint: For stale local API behavior, compare the live OpenAPI routes with the source, use the Make command, and restart a server launched before this setting was added.

## [2026-11-15] Session rotation belongs to the caller transaction
Context: BlissBiz B01 session/CSRF foundation and future registration/login.
Signal: Registration/login must replace anonymous credentials without leaving partial owner/business/session writes or changing cookie scope.
Root cause: Design constraint: session rotation, credential issuance, and database commit must agree; independently committing a repository operation breaks atomicity.
Fix: SessionRepository/SessionService only flush; callers commit the complete operation before using SessionCookies. Use require_csrf_session for anonymous mutations, require_owner_mutation for owner mutations, and exact admin origins. See docs/session-security.md.
Verification: SQLite/MySQL tests cover rotation, invalid-owner rollback, expiry, CSRF/origin rejection, production cookies, and failed commits without Set-Cookie. In-process real-app checks left no persisted test sessions.
Reuse hint: Reuse these helpers for B02/B03 rather than writing separate session/cookie logic. Prefer in-process verification when a contributor owns their running backend terminal.

## [2026-11-15] Registration quotas and request rollbacks need separate boundaries
Context: BlissBiz B02 registration, rate limiting, and integration fixtures.
Signal: Failed registration must preserve the prior anonymous session while still consuming shared quota.
Root cause: A quota write in the registration transaction would roll back with the failure. Nested quota checkouts from the request's connection pool can also exhaust that pool. Test sessions joined in rollback-only mode can erase setup records when a route rolls back.
Fix: Commit quota operations through RateLimitSessionLocal with its own bounded pool; keep owner/business/rotation in the request transaction. Use create_savepoint when joining test sessions to their outer rollback transaction. Reuse the configured URL builder and normalize emails before duplicate checks.
Verification: 195 SQLite/MySQL tests passed, including concurrent native MySQL counters, preserved anonymous sessions after failure, and uniqueness races. Real-app smoke confirmed quota persisted across registration rollback and cleaned only its unique test counter.
Reuse hint: Apply these boundaries to B03 login throttling; do not consume quota in the credential transaction or share its nested connection checkout pool.
