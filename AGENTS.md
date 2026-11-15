# Project Guidelines

## Purpose and Stack
- Build a multi-tenant platform for small businesses: registration, owner dashboard, and public product storefronts.
- Frontend: Vue 3, Vite, and Vue Router. Backend: FastAPI with Uvicorn.
- Database: MySQL with SQLAlchemy and Alembic migrations.
- Deployment target: one GoDaddy Linux VPS; Nginx serves the built frontend and proxies `/api` to FastAPI.
- Store product images in a persistent upload directory outside deployment folders; store their paths in MySQL.
- Keep this stack. Discuss new frameworks, services, or major dependencies before introducing them.

## Structure and Style
- Keep frontend code in `frontend/` and backend code in `backend/`.
- Use Vue Single-File Components with Composition API and `<script setup>`; keep API calls in a shared client.
- Keep FastAPI routes thin: validate requests with Pydantic, put business rules in services, and scope database sessions to requests.
- Use model, service, and repository classes where they give responsibilities a clear home; avoid unnecessary inheritance or abstraction layers.
- Use `PascalCase.vue` for components, `snake_case` for Python, and descriptive domain names throughout.
- Prefer small, readable functions and reuse existing patterns. Avoid speculative abstractions and unrelated refactors.
- Use `python3` for Python commands. Follow the project's formatter and dependency lockfiles once established.
- Use `make setup`, `make dev-backend`, `make dev-frontend`, and `make check`; use `scripts/npm.sh` for npm commands so the project-local Node runtime is selected when present.

## Business Isolation and Security
- Serve all businesses from one application and shared schema; every product belongs to a business through `business_id`.
- Normalize business slugs, enforce uniqueness in the database, and reserve infrastructure names such as `admin`, `www`, and `api`.
- Resolve storefronts through validated hostnames and business records; unknown businesses return 404.
- Enforce authenticated ownership in the backend for every admin read, write, and upload. Never trust a client-supplied business ID as authorization.
- Scope tenant queries and any caches by business. Public responses expose only published products and public business fields.
- Hash passwords with a maintained password library. Use server-side sessions with Secure, HttpOnly cookies in production and CSRF protection for mutations.
- Validate image type and size; generate safe filenames, prevent path traversal, and never execute uploaded content.
- Keep secrets in environment variables. Commit only placeholder `.env.example` files; never log credentials, sessions, or private owner data.

## API and Data Changes
- Validate inputs on the backend; frontend validation is for usability.
- Use explicit request/response schemas, consistent errors, and appropriate HTTP status codes. Never expose tracebacks to clients.
- Use transactions for related writes and Alembic migrations for schema changes; never rely on manual production edits.
- Configure connections through `DATABASE_URL`; keep database access in backend persistence modules and use SQLAlchemy queries and portable types by default.
- Isolate and document unavoidable database-specific SQL or features. A database-engine switch requires migration review, data transfer, and integration tests; changing the connection URL alone is insufficient.
- Restrict database access to the backend through local or explicitly allowed connections; use TLS for remote database connections. Expose only intended HTTP endpoints and public images from upload storage.

## Verification and Collaboration
- Keep changes focused on the requested task; preserve other contributors' work.
- Deliver small, tested iterations and stop for user review before starting the next iteration.
- Before implementation, read `docs/implementation-workflow.md` and `docs/progress.md`; claim a task and leave its status, verification evidence, and handoff current when stopping.
- Add meaningful tests for business rules and bugs. Always cover ownership checks and cross-business access when changing tenant-sensitive code.
- Run relevant checks and the frontend production build when applicable. Report what passed, what was skipped, and any blockers; never invent results.
- Update setup instructions and `.env.example` when configuration changes. Document repeatable deployment steps and persistent storage requirements.
- Summarize the change and verification clearly. Never deploy, run destructive migrations, or delete business data without explicit authorization.
