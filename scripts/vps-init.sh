#!/bin/sh
# Generate fresh VPS-only credentials and a short-lived pre-DNS test certificate.
# Does not contact Docker, start services, or change DNS/firewall settings.
set -eu
umask 077
project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
if [ -e deploy/vps.env ] || [ -e deploy/tls ]; then
  echo 'Existing deploy/vps.env or deploy/tls found; leaving both unchanged.' >&2
  exit 1
fi
command -v openssl >/dev/null
mkdir -m 700 deploy/tls
cat > deploy/tls/request.cnf <<'EOF'
[req]
distinguished_name = subject
x509_extensions = extensions
prompt = no
[subject]
CN = blissbiz.biz
[extensions]
subjectAltName = DNS:blissbiz.biz,DNS:*.blissbiz.biz
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
EOF
openssl req -x509 -newkey rsa:3072 -nodes -days 14 \
  -config deploy/tls/request.cnf \
  -keyout deploy/tls/privkey.pem -out deploy/tls/fullchain.pem
{
  printf 'MYSQL_PASSWORD=%s\n' "$(openssl rand -hex 32)"
  printf 'MYSQL_ROOT_PASSWORD=%s\n' "$(openssl rand -hex 32)"
  printf 'RELEASE_TAG=local\n'
} > deploy/vps.env
echo 'Created private deploy/vps.env and 14-day test TLS files in deploy/tls.'
echo 'These are for verified pre-DNS testing. Replace TLS before public launch.'
