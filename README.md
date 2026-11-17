# BlissBiz

Small-business website platform built with Vue 3 + Vite, FastAPI, and MySQL. Backend APIs through B09 support registration, login/logout, owner settings, product CRUD/publication, image uploads, and hostname-based public storefronts. Business frontend screens remain planned.

Registration, owner dashboard, and storefront endpoints are documented in [the API plan](docs/api.md).

Public storefront GET examples are in [the API document](docs/api.md#end-customer-website). [Deployment preparation](deploy/README.md) covers production settings, Nginx/service files, persistent storage, maintenance and backups. `make test-deployment` runs an isolated local HTTPS/Nginx/MySQL check; `make maintenance-preview` reports expired security records and orphan images without deleting anything. No production deployment is performed by setup or tests.

For coordinated development across contributors and chats, follow [the implementation workflow](docs/implementation-workflow.md) and claim/update work in [the progress tracker](docs/progress.md).

Iteration 1 implements the owner/business schema and public slug availability endpoint. API routes use request/response schemas, services for rules, and repositories for persistence.

B01 adds server-side session storage and CSRF/security helpers; see [the session contract](docs/session-security.md). B02 adds transactional registration, Argon2id password hashing, generated business URLs, and shared rate limiting; see [the registration review guide](docs/registration.md). B03 adds login/logout/profile and login throttling; [basic request examples](docs/api.md#basic-authentication-requests) include the login body. Optional login limits and defaults are listed in `backend/.env.example`; existing local environment files can use these defaults. No B03 migration is needed.

## Start on this Mac

The project uses a local Node.js installation in `.tools/node` because the existing system Node installation cannot start. The provided commands select it automatically. Python runs in `backend/.venv`, isolated from other projects. MySQL runs in Docker through your existing Rancher Desktop installation.

From this folder:

```sh
make db-up
make db-migrate
```

Then open two terminal tabs in the project folder:

```sh
# Terminal 1: Python backend, reloads when Python files change
make dev-backend
```

```sh
# Terminal 2: Vue frontend, updates when frontend files change
make dev-frontend
```

- Frontend: <http://127.0.0.1:5173>
- Interactive API documentation: <http://127.0.0.1:8000/api/docs>
- Backend health: <http://127.0.0.1:8000/api/health>
- Backend + database readiness: <http://127.0.0.1:8000/api/ready>
- Session/CSRF bootstrap: <http://127.0.0.1:8000/api/v1/auth/csrf>

The frontend displays connection status for the backend and database. Its `/api` requests are forwarded to FastAPI by Vite, so no separate browser CORS configuration is needed locally. The backend command enables file polling for reliable automatic reloads on this Mac.

Stop either development server with **Ctrl+C**. Stop MySQL with `make db-stop`; its data remains in a Docker volume. These servers and configuration are for local development only.

## Setup on another machine

Install Node.js 24 LTS (the tested patch is recorded in `.nvmrc`), Python 3.11–3.13, Docker with Compose, and Make. The `.tools` runtime is local to this Mac and is not committed. If you already use nvm, `nvm install` selects the recorded Node version.

```sh
make setup
make db-up
make db-migrate
```

`make setup` creates local `.env` files with randomly generated database passwords, creates an isolated Python environment, installs the locked dependencies, and leaves existing configuration intact. If Python is not found automatically:

```sh
PYTHON_BIN=/path/to/python3.13 make setup
```

Start Docker/Rancher Desktop before `make db-up`. MySQL is exposed only on `127.0.0.1:3307` to avoid conflicting with an existing installation on port 3306. The application uses a dedicated database user rather than root.

## Where to work

```text
frontend/src/
  views/          Vue pages
  router/         Page routes
  api/            Shared API client
backend/
  app/main.py     FastAPI application
  app/api/        Request handlers
  app/core/       Environment configuration
  app/db/         Models, repositories, engine, base, and sessions
  app/schemas/    Pydantic request/response schemas
  app/services/   Business rules
  migrations/     Alembic schema migrations
  tests/          Backend tests
```

Database models inherit from `app.db.session.Base`; import model modules in `backend/migrations/env.py` so Alembic discovers them. Migration `0001` creates owners/businesses, `0002` adds sessions, and `0003` adds shared rate-limit counters. Database timestamps are stored as UTC.

B04–B06 add business settings, product CRUD/search/publication and image APIs; migration `0004` creates products. Run `make setup` to install the updated locked dependencies (Pillow and python-multipart), then `make db-migrate`. [Basic request bodies](docs/api.md#basic-businessproduct-requests) and [upload fields](docs/api.md#image-uploads) are in the API document and `/api/docs`.

Image storage defaults to ignored `backend/uploads`, resolved from the backend project location. To choose another location, set an absolute `UPLOAD_DIR` in `backend/.env`. Production requires a directory outside this checkout/deployment folder, such as `/var/lib/blissbiz/uploads`, writable by the backend service. Keep it across releases and back it up alongside MySQL. Only image paths are stored in MySQL; restoring the database alone does not restore pictures. FastAPI serves `/media` and Vite proxies it locally; production Nginx routing and backup procedures are prepared under `deploy/`. Never mount the whole upload root as executable web content.

For your IDE, select `backend/.venv/bin/python3` as the Python interpreter and `.tools/node/bin/node` as the Node interpreter on this Mac. Activating Python manually is optional; the Make commands already use the virtual environment.

## Checks and dependencies

```sh
make check
```

This runs Python linting, formatting checks, backend tests, and the Vue production build. Default database tests use isolated SQLite databases and do not require MySQL. For the same tests against local MySQL as well:

```sh
make db-up
make db-migrate
make test-mysql
```

Run this only with a local development `DATABASE_URL`. Business/session test writes are contained in outer transactions and rolled back; tests do not create/drop MySQL tables or commit business records. The MySQL rate-limit concurrency test commits security counters and removes only its own uniquely keyed counter afterward.

Try the first endpoint in `/api/docs` or open <http://127.0.0.1:8000/api/v1/business-slugs/Happy-Bakery/availability>. The response normalizes the address, for example `{ "slug": "happy-bakery", "available": true }`. Reserved or taken names return `available: false`; malformed names return a field-specific `422`. Availability does not reserve an address.

Use the Node wrapper on this Mac instead of the broken global npm:

```sh
./scripts/npm.sh --prefix frontend install package-name
```

Backend dependencies are declared in `backend/pyproject.toml`; exact resolved versions are in `backend/requirements.lock`. After intentionally changing dependencies, update and validate the lock:

```sh
backend/.venv/bin/python3 -m pip install -e './backend[dev]'
backend/.venv/bin/python3 -m pip freeze --exclude-editable > backend/requirements.lock
make check
```

Commit dependency declarations and lockfiles together. Never commit `.env`, `.venv`, `.tools`, `node_modules`, or uploaded images.

## Database configuration and migrations

Root `.env` configures the local MySQL container. `backend/.env` contains the backend's `DATABASE_URL`. Both are generated locally and ignored by Git; `.env.example` files document the configuration.

Changing container credentials after initial startup does not change credentials in the existing MySQL data volume. Keep both configuration files aligned; change existing database credentials explicitly rather than deleting the volume.

After adding models, create and inspect a migration before applying it to your local database:

```sh
cd backend
.venv/bin/python3 -m alembic revision --autogenerate -m "describe schema change"
.venv/bin/python3 -m alembic upgrade head
```

The MySQL driver and connection options are isolated in backend configuration and persistence code. Switching database engines also requires reviewing migrations and transferring data.

For deployment later, Nginx will serve `frontend/dist` and forward `/api` to FastAPI; it must also fall back to `index.html` for Vue page routes. Production requires HTTPS, an appropriate production process setup, database access restrictions, and persistent database/upload backups. Product features and production deployment are separate from this development setup.
