# BlissBiz VPS containers

Target: Ubuntu Server 26.04, 4 CPU cores, 8 GB RAM, 200 GB SSD; domain `blissbiz.biz`. Nginx serves a production Vue build and proxies `/api` and `/media` to two Uvicorn workers. MySQL 8.4 and FastAPI have no published ports. Docker volumes preserve the database and uploads outside this checkout. Logs rotate at 3 × 10 MB per service.

The frontend image builds with Node 24; Node and Python do not need installing on the VPS. Website origins are compiled into the frontend image and match the backend's exact HTTPS admin origin. The proxy has a fixed private IP so the backend trusts that single address, rather than arbitrary forwarding headers. If the configured network overlaps an existing network, choose an unused subnet and corresponding proxy IP in `deploy/vps.env` before starting containers.

## Copy the prepared files from the Mac

Run on the Mac after the initial project copy:

```sh
cd /Users/samanwaydey/Work/blissbiz
rsync -az --exclude=vps.env --exclude=tls/ deploy scripts .dockerignore .gitignore samanwaydey@97.74.89.213:~/blissbiz/
```

This deliberately excludes server credentials and certificate files. The `deploy/` and `scripts/` directory names in this command have no trailing slash. Never copy a local `.env`, development database, or upload folder over the VPS.

## First startup on the VPS

Run in the existing VPS SSH session. Finish Ubuntu package updates first. Verify `sudo docker compose version` works.

```sh
cd ~/blissbiz
sh scripts/vps-init.sh
sudo sh scripts/vps-compose.sh config --quiet
sudo sh scripts/vps-compose.sh build backend proxy
sudo sh scripts/vps-compose.sh up -d --wait db
sudo sh scripts/vps-compose.sh run --rm --no-deps migrate
sudo sh scripts/vps-compose.sh up -d --wait backend proxy
sudo sh scripts/vps-compose.sh exec -T proxy nginx -t
sudo sh scripts/vps-compose.sh ps
```

Run these one at a time; stop on an error. Initialization creates mode-0600 `deploy/vps.env` with two independently generated URL-safe passwords, and mode-0700 `deploy/tls` holding a 14-day self-signed certificate for `blissbiz.biz` and `*.blissbiz.biz`. It refuses to overwrite either existing location. If initialization is interrupted, inspect the partial output before retrying; do not delete existing server credentials. Do not share environment files or full rendered Compose output, which contains credentials. `config --quiet` validates without printing them.

The migration is a separate, explicit step; restarting the backend does not apply schema changes. For later releases take a verified database/images backup before running it. Never run `down --volumes`, `docker volume prune`, or delete data to resolve a startup issue. Editing passwords in the environment file after first startup does not rotate MySQL's stored passwords.

Only Nginx publishes ports 80 and 443. These are IPv4 bindings by default; do not publish an IPv6 AAAA record until IPv6 routing/firewall/listeners are deliberately configured. Docker-published ports can bypass UFW: adding a public mapping for MySQL or FastAPI is not protected by simply leaving those ports out of UFW.

## API tests before public DNS

On the VPS, verify HTTPS and database readiness without changing DNS:

```sh
cd ~/blissbiz
curl --noproxy '*' --cacert deploy/tls/fullchain.pem \
  --resolve blissbiz.biz:443:127.0.0.1 https://blissbiz.biz/api/ready
curl --noproxy '*' --cacert deploy/tls/fullchain.pem \
  --resolve admin.blissbiz.biz:443:127.0.0.1 https://admin.blissbiz.biz/login
curl --noproxy '*' --cacert deploy/tls/fullchain.pem \
  --resolve admin.blissbiz.biz:443:127.0.0.1 https://admin.blissbiz.biz/api/v1/auth/csrf
```

Readiness should return HTTP 200, `/login` returns the Vue HTML, and CSRF bootstrap returns JSON. `--resolve` sets both TLS hostname and HTTP Host correctly. Visiting the raw IP will return an unknown-host response. Do not use `curl -k`, disable secure cookies, or switch the backend to development mode.

For the same checks from the Mac, copy **only the public certificate** over the already verified SSH connection:

```sh
scp samanwaydey@97.74.89.213:~/blissbiz/deploy/tls/fullchain.pem /tmp/blissbiz-vps-test.pem
curl --noproxy '*' --cacert /tmp/blissbiz-vps-test.pem \
  --resolve blissbiz.biz:443:97.74.89.213 https://blissbiz.biz/api/ready
```

The temporary certificate is explicitly trusted for that curl command only. Use disposable test accounts; real customer onboarding waits for public HTTPS, backup delivery and launch verification. Browser end-to-end testing requires a trusted certificate and resolving each hostname to the VPS; a hosts-file change alone does not make this certificate trusted. A hosts file has no wildcard support, so add individual test store names when ready.

## Certificates, DNS and browser testing

A publicly trusted certificate must cover both `blissbiz.biz` and `*.blissbiz.biz`. DNS-01 validation can issue that certificate by adding TXT records before changing public A records. Prefer automated DNS validation/renewal where supported; manual TXT validation needs a repeatable renewal procedure. No certificate account, DNS credential, issuance, or renewal has been configured by these files.

Place the reviewed certificate chain/key as `deploy/tls/fullchain.pem` and `deploy/tls/privkey.pem`, preserve restrictive key permissions, then validate and reload Nginx:

```sh
sudo sh scripts/vps-compose.sh exec -T proxy nginx -t
sudo sh scripts/vps-compose.sh exec -T proxy nginx -s reload
```

The directory is mounted read-only into Nginx, so replacing certificate files on the host is visible inside it. If using symlinked certificate files, mount the full directory tree needed to resolve those links instead of copying broken symlinks. Arrange certificate refresh and an Nginx reload on renewal.

Once the public certificate is installed, map these names to `97.74.89.213` on the Mac for private browser testing: `blissbiz.biz`, `admin.blissbiz.biz`, `bakery.blissbiz.biz`, and `books.blissbiz.biz`. Use the existing README's two-business flow to verify registration/login, settings, image upload, publish/unpublish, private ownership, and direct-URL refresh. This mapping affects only the Mac. Public A records for `@`, `admin`, and `*` can be configured after the deployment checks pass; review existing records before changing them. Remove temporary Mac mappings afterward.

## Backups and upgrades

Volumes survive normal container replacement and `stop`/`start`; they do not survive VPS/SSD loss. Configure encrypted, access-controlled off-VPS delivery and retention before real customer use. The existing backup helper can be used with the VPS Compose file by copying uploads while **all backend writes, maintenance and migrations are paused**:

```sh
cd ~/blissbiz
sudo sh scripts/vps-compose.sh stop backend
# Use a fresh private destination for each backup. Do not reuse this example path.
sudo install -d -m 700 /var/backups/blissbiz/first-snapshot
sudo sh scripts/vps-compose.sh cp backend:/data/uploads/. /var/backups/blissbiz/first-snapshot/uploads
sudo env COMPOSE_PROJECT_NAME=blissbiz-vps \
  COMPOSE_FILE="$PWD/deploy/compose.vps.yaml" \
  COMPOSE_ENV_FILES="$PWD/deploy/vps.env" \
  sh scripts/backup.sh --writes-paused \
  /var/backups/blissbiz/first-snapshot/uploads \
  /var/backups/blissbiz/first-snapshot/backup
sudo sh scripts/vps-compose.sh start backend
```

On any backup failure inspect the error and restart the backend when safe; no script automatically pauses or resumes writes. Follow the disposable restore validation in `deploy/README.md`, verify checksums and copy successful backups off the VPS. These commands prepare a manual snapshot; they do not configure automatic backups.

For an upgrade, retain the previous source/image release, set a new `RELEASE_TAG` in `deploy/vps.env`, build images, back up with writes paused, explicitly run the migration, and recreate backend/proxy. `RELEASE_TAG` controls both app image names; database/upload volumes remain attached to the fixed `blissbiz-vps` project. Reverting code requires checking schema compatibility; never automatically downgrade a live database. Maintenance remains opt-in; preview with `sudo sh scripts/vps-compose.sh exec -T backend python3 -m app.maintenance`.

## Local verification of this exact container layout

```sh
backend/.venv/bin/python3 scripts/test_deployment.py --vps
```

This creates a randomly named disposable project, isolated subnet, random loopback host ports, fresh credentials/volumes and a one-day TLS certificate. It builds both actual VPS images, runs the explicit migration, checks verified HTTPS, ownership/storefront isolation, secure cookies, uploads, quotas, restart persistence and backup/restore, then removes only its own test resources. The real `blissbiz-vps` project and normal development database are not used. Optional corporate-network image overrides: `TEST_PYTHON_IMAGE`, `TEST_NGINX_IMAGE`, `TEST_NODE_IMAGE`, `TEST_MYSQL_IMAGE`. Real VPS firewall access, architecture, DNS, certificates and offsite backups still require verification there.
