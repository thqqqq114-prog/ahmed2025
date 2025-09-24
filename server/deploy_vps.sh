#!/usr/bin/env bash
set -euo pipefail

# ================================
# FarmApp VPS One-Click Installer
# - Installs Docker + Compose plugin (Ubuntu)
# - Clones the repo (if GIT_URL provided and target dir missing)
# - Generates ES256 keys if missing
# - Creates docker-compose.override.yml with admin creds and volumes
# - Templatizes Caddyfile with your domains
# - Builds and starts the stack (API + Caddy updates+proxy)
# ================================

# ----- Configurable via env vars -----
APP_DIR=${APP_DIR:-/opt/farmapp}
GIT_URL=${GIT_URL:-""}                 # e.g. https://github.com/you/farmapp.git
BRANCH=${BRANCH:-main}
DOMAIN_API=${DOMAIN_API:-ahmedhussein.online}
DOMAIN_UPDATES=${DOMAIN_UPDATES:-ahmedhussein.online}
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}

# Generate a random secret if not provided
if command -v openssl >/dev/null 2>&1; then
  ADMIN_SESSION_SECRET=${ADMIN_SESSION_SECRET:-$(openssl rand -hex 32)}
else
  ADMIN_SESSION_SECRET=${ADMIN_SESSION_SECRET:-$(date +%s%N | sha256sum | cut -c1-64)}
fi

# Optional payment integration envs
PAYMOB_HMAC_KEY=${PAYMOB_HMAC_KEY:-""}
PAYMOB_API_KEY=${PAYMOB_API_KEY:-""}

# Compose project name for consistent resources
export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME:-farmapp}

# ================================
# Helpers
# ================================
log() { echo -e "\e[1;34m[INFO]\e[0m $*"; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }
err() { echo -e "\e[1;31m[ERR ]\e[0m $*"; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    err "Please run as root: sudo $0"
    exit 1
  fi
}

ensure_pkg() {
  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "$@"
}

# ================================
# 1) System prerequisites
# ================================
require_root
log "Installing prerequisites (curl, git, openssl, ca-certificates, psmisc)..."
ensure_pkg curl git openssl ca-certificates psmisc

if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker Engine via convenience script..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
else
  log "Docker already installed"
fi

if ! docker compose version >/dev/null 2>&1; then
  log "Installing Docker Compose plugin..."
  ensure_pkg docker-compose-plugin
else
  log "Docker Compose plugin already installed"
fi

# Optional: open firewall if UFW is active
if command -v ufw >/dev/null 2>&1; then
  if ufw status | grep -q "Status: active"; then
    log "UFW is active; allowing 80/tcp and 443/tcp"
    ufw allow 80/tcp || true
    ufw allow 443/tcp || true
  fi
fi

# ================================
# 2) Use existing uploaded project
# ================================
mkdir -p "$APP_DIR"
if [[ ! -d "$APP_DIR/server" ]]; then
  err "server/ folder not found in $APP_DIR. Please push via deploy_to_vps.ps1 or set GIT_URL to clone."
  exit 1
fi
log "Using existing project at $APP_DIR"

cd "$APP_DIR/server"

# ================================
# 3) Keys and data directories
# ================================
log "Ensuring data directories..."
mkdir -p data/keys data/db updates/win

if [[ ! -f data/keys/private.pem ]]; then
  log "Generating ES256 keypair (private/public)..."
  openssl ecparam -genkey -name prime256v1 -noout -out data/keys/private.pem
  openssl ec -in data/keys/private.pem -pubout -out data/keys/public.pem
else
  log "Keys already exist in data/keys/"
fi

# Create a starter manifest if missing
if [[ ! -f updates/win/manifest.json ]]; then
  log "Creating starter updates/win/manifest.json"
  cat > updates/win/manifest.json <<'JSON'
{
  "latest_version": "1.0.0",
  "min_required_version": "1.0.0",
  "mandatory": false,
  "installer_url": "https://REPLACE_UPDATES_DOMAIN/win/FarmApp-1.0.0.exe",
  "sha256": ""
}
JSON
  sed -i "s|REPLACE_UPDATES_DOMAIN|$DOMAIN_UPDATES/updates|g" updates/win/manifest.json
fi

# ================================
# 4) docker-compose override + Caddyfile templating
# ================================
log "Generating docker-compose.override.yml with admin settings..."
cat > docker-compose.override.yml <<YML
services:
  api:
    environment:
      - ADMIN_USERNAME=$ADMIN_USERNAME
      - ADMIN_PASSWORD=$ADMIN_PASSWORD
      - ADMIN_SESSION_SECRET=$ADMIN_SESSION_SECRET
      - LICENSE_PUBKEY_PATH=/run/keys/public.pem
      - DATA_DIR=/run/data
      - PAYMOB_HMAC_KEY=${PAYMOB_HMAC_KEY}
      - PAYMOB_API_KEY=${PAYMOB_API_KEY}
    volumes:
      - ./data:/run/data
YML

log "Templating Caddyfile.updates with your domains..."
cat > Caddyfile.updates <<CADDY
$DOMAIN_UPDATES {
	encode gzip
	root * /srv
	file_server
	@forbidden {
		path_regexp pathlist ^/.+/$
	}
	respond @forbidden 403
}

$DOMAIN_API {
	encode gzip
	reverse_proxy api:8000
}
CADDY

# ================================
# 5) Build & Run
# ================================
# Proactively stop old stack and free ports (80/443) to avoid conflicts
log "Stopping any existing stack and removing orphans..."
docker compose down --remove-orphans || true

# Free up ports 80/443 from host daemons and stray processes
log "Freeing ports 80/443 (nginx/apache/caddy/traefik + stray listeners)..."
systemctl stop nginx || true
systemctl stop apache2 || true
systemctl stop caddy || true
systemctl stop traefik || true
# Kill any processes still listening on 80/443
if command -v fuser >/dev/null 2>&1; then
  fuser -k 80/tcp 2>/dev/null || true
  fuser -k 443/tcp 2>/dev/null || true
fi
# Remove any container publishing 80/443 regardless of project name
for c in $(docker ps -q --filter "publish=80" --filter "publish=443"); do
  docker rm -f "$c" || true
done

# Defensive cleanup for legacy containers with fixed names
log "Force-removing any legacy containers with static names (farmapp-*)..."
docker rm -f farmapp-db farmapp-api farmapp-caddy >/dev/null 2>&1 || true

log "Building containers... (this may take a while)"
docker compose build --pull

log "Starting stack..."
docker compose up -d

# ================================
# 6) Summary
# ================================
cat <<INFO

====================================
FarmApp stack is up!

Admin Dashboard:    https://$DOMAIN_API/api/admin
API Base:           https://$DOMAIN_API/api
Updates Root:       https://$DOMAIN_API/updates/

Admin credentials:
  USERNAME: $ADMIN_USERNAME
  PASSWORD: $ADMIN_PASSWORD

Data directory:     $APP_DIR/server/data
  - Keys:           $APP_DIR/server/data/keys (private.pem, public.pem)
  - Admin state:    $APP_DIR/server/data (mounted to /run/data in container)

To view logs:
  cd $APP_DIR/server
  docker compose logs -f

To update the stack after changes:
  docker compose build --no-cache
  docker compose up -d

====================================
INFO