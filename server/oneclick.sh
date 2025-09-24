#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DOMAIN="ahmedhussein.online"

echo "==> FarmApp Licensing API one-click deploy"

# Ensure data/keys dir
mkdir -p data/keys

# Create .env if missing
if [ ! -f .env ]; then
  echo "==> Generating .env"
  POSTGRES_PASSWORD="$(openssl rand -hex 16 2>/dev/null || echo "ChangeMe$(date +%s)")"
  ADMIN_PASSWORD="$(openssl rand -hex 16 2>/dev/null || echo "ChangeMe$(date +%s)")"
  ADMIN_SESSION_SECRET="$(openssl rand -base64 32 2>/dev/null || uuidgen)"
  cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_SESSION_SECRET=${ADMIN_SESSION_SECRET}
PAYMOB_HMAC_KEY=
PAYMOB_API_KEY=
EOF
else
  echo "==> .env exists. Skipping."
fi

# Generate keys if missing
if [ ! -f data/keys/private.pem ] || [ ! -f data/keys/public.pem ]; then
  echo "==> Generating ES256 keys"
  if command -v openssl >/dev/null 2>&1; then
    openssl ecparam -genkey -name prime256v1 -noout -out data/keys/private.pem
    openssl ec -in data/keys/private.pem -pubout -out data/keys/public.pem
  elif command -v docker >/dev/null 2>&1; then
    docker run --rm -v "$PWD/data/keys:/keys" alpine:3 sh -c "apk add --no-cache openssl >/dev/null && openssl ecparam -genkey -name prime256v1 -noout -out /keys/private.pem && openssl ec -in /keys/private.pem -pubout -out /keys/public.pem"
  else
    echo "ERROR: Need openssl or docker to generate keys." >&2
    exit 1
  fi
else
  echo "==> Keys already exist. Skipping."
fi

echo "==> Starting Docker stack"
docker compose up -d --build

echo
echo "All set!"
echo "- Admin: https://${DOMAIN}/api -> redirects to /api/admin"
echo "- Activate: POST https://${DOMAIN}/api/v1/activate"
echo "- Verify: GET https://${DOMAIN}/api/v1/verify"
echo
echo "To see logs: docker compose logs -f caddy api"