# Deployment preparation (B09)

Prepared for one GoDaddy **Linux VPS** with Nginx, Python 3.11–3.13 and MySQL 8.4. Shared website hosting is not assumed to support this process layout. These files do not install services or deploy anything. Frontend business screens remain separate work.

## Production layout

```text
/opt/blissbiz/releases/<release>/   application checkout and built frontend
/opt/blissbiz/current -> releases/<release>
/etc/blissbiz/backend.env          private environment file
/var/lib/blissbiz/uploads/         persistent images, outside releases
```

1. Choose the real domain and provision DNS for the root, `admin`, and wildcard business subdomains. Obtain an HTTPS certificate covering both the root domain and `*.your-domain`. DNS and certificate issuance require the actual hosting account.
2. Create a dedicated `blissbiz` OS user. Give it write access to `/var/lib/blissbiz/uploads`; keep application code owned by the deployment user. Copy `backend.env.example` to `/etc/blissbiz/backend.env`, replace placeholders, and restrict that file to the service user/root (mode `0600`). URL-encode special characters in DATABASE_URL credentials. Use TLS for remote MySQL; keep local MySQL bound to loopback, as Compose already does.
3. In a new release directory, create `backend/.venv`, install `backend/requirements.lock` and the backend package with `--no-deps`; run `scripts/npm.sh --prefix frontend ci`, then set public build-time `VITE_STOREFRONT_BASE_URL=https://your-domain` and `VITE_ADMIN_BASE_URL=https://admin.your-domain` (matching the backend URL/origin settings) before `scripts/npm.sh --prefix frontend run build`. These values are compiled into the frontend; rebuild after changing them and never put secrets in Vite variables. Run Alembic `upgrade head` once using the same production environment before starting workers. Back up first; migrations are not an automatic rollback mechanism.
4. Review `blissbiz.service`, replace deployment paths if needed, and install it under `/etc/systemd/system`. The backend binds only `127.0.0.1:8000`; only Nginx's HTTP/HTTPS ports should be public. Do not use development reload in production.
5. Copy `nginx/site.conf` to the Nginx configuration directory and `nginx/proxy.conf` to `/etc/nginx/blissbiz-proxy.conf`. Replace **both** `example.com` and regex-escaped `example\.com` with the real domain equivalents; set the certificate and frontend paths. Remove/conflict-resolve any existing default server blocks, run `nginx -t`, and reload only after successful validation. Nginx serves the Vue build and proxies `/api` and `/media`; no upload directory is exposed as an executable/static directory.
6. When deploying, change `current` to the prepared release, restart the backend service, and check `/api/ready` through HTTPS plus one known storefront. Retain the previous release. If reverting application code, first verify that it is compatible with the current schema; do not blindly downgrade migrations. Never remove the persistent upload root or database volume during deployment.

Nginx overwrites forwarded client-IP/protocol headers and preserves Host including the port. `TRUSTED_PROXY_IPS` must name only the actual proxy addresses (`127.0.0.1/32` and `::1/128` for this same-VPS layout). The application handles proxy headers once; all supplied launch commands use Uvicorn `--no-proxy-headers` to avoid a second, broader trust policy. Rate limits therefore use the verified client IP. Untrusted forwarded headers are ignored, and X-Forwarded-Host is never used to choose a storefront. Do not expose port 8000 or trust `*`/all-IP ranges. Proxy settings follow [Uvicorn](https://uvicorn.dev/settings/) and [Nginx](https://nginx.org/en/docs/http/ngx_http_proxy_module.html).

Owner cookies are host-only, HttpOnly, Secure and SameSite=Lax in production. Registration/login and owner APIs use `https://admin.<domain>`. Public Swagger/OpenAPI routes are disabled in production. Storefront JSON has no shared cache and exposes only published products and explicit public fields; uploaded images remain public assets, including draft images.

## Maintenance

Preview locally with `make maintenance-preview`, or from the configured backend environment:

```sh
.venv/bin/python3 -m app.maintenance
.venv/bin/python3 -m app.maintenance --apply --grace-hours 24
```

Default is **dry run**. `--apply` removes expired sessions/rate counters and generated image files older than the grace period with no remaining logo/product reference. Each candidate is rechecked in a fresh transaction while holding the same business lock as uploads; recent, referenced, unknown-format and symlinked files are preserved. Counts are printed without tokens or owner details. A failed file removal is counted and retried on the next run. Keep the grace period at least 24 hours in production. The optional reviewed service/timer files run this daily; they are not enabled by this repository. Only install/enable them during an approved deployment.

## Backup and recovery

Back up **both MySQL and uploads**. Pause backend writes, including maintenance, for a consistent DB/file pair. For the Compose MySQL layout, from the repository root:

```sh
sh scripts/backup.sh --writes-paused /var/lib/blissbiz/uploads /absolute/new-private-backup-directory
```

The command does not stop anything for you. It creates `database.sql`, `uploads.tar.gz` and `SHA256SUMS` with private permissions. A destination inside uploads is rejected. Failed/incomplete directories have no completion guarantee; do not use them for recovery. For externally managed MySQL, use its corresponding snapshot/dump facility with the same paused-write boundary.

Copy completed backups to an access-controlled **off-VM** destination; a backup on the same VM is not disaster recovery. Configure retention and encryption for the chosen destination. No cloud account, offsite target or scheduler has been configured automatically.

Validate checksums before restoring. Restore the SQL into a **new disposable database** first and extract the trusted image archive into a new empty upload directory. Check row counts, migration head, referenced images and the API before switching any live configuration. Never import a test backup over an existing business database. Exact production restore/switch commands depend on the chosen database/backup provider and require an approved recovery operation.

## Isolated local deployment check

`make test-deployment` builds the Vue assets, then starts a uniquely named disposable MySQL + two-worker backend + Nginx stack. It creates a one-day local TLS certificate, uses verified local HTTPS and private test credentials, and checks host routing, secure cookies, publication, owner isolation, spoofed headers, shared rate limits, restart persistence and a checksummed backup/restore into a new test database. The script removes only its own generated project/volumes afterward. It never points to the normal `blissbiz` database or backend process. Docker and OpenSSL are required; the first run downloads/builds images.

If Docker Hub's download certificate chain is unavailable on a corporate network, the test supports `TEST_NGINX_IMAGE` / `TEST_PYTHON_IMAGE` overrides, for example Google's [Docker Hub cache](https://docs.cloud.google.com/artifact-registry/docs/pull-cached-dockerhub-images). Certificate verification stays enabled; no daemon restart or trust-store change is required:

```sh
TEST_NGINX_IMAGE=mirror.gcr.io/library/nginx:stable-alpine \
TEST_PYTHON_IMAGE=mirror.gcr.io/library/python:3.13-slim make test-deployment
```

Real GoDaddy DNS, certificate renewal, firewall access, OS/service installation, offsite backup delivery and final domain-specific configuration still require verification on the intended VPS. The local stack does not prove those external systems are configured.
