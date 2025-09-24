# FarmApp Server Deployment (Licensing API only)

This sets up:
- api.ahmedhussein.online -> FastAPI licensing API (+ admin panel)

## Prereqs on VPS (Ubuntu recommended)
1) Install Docker + Docker Compose plugin
2) Add DNS records:
   - A api.ahmedhussein.online -> VPS IP

## Secrets
- Place ES256 keys under `server/data/keys/`:
  - private.pem (PEM, ES256)
  - public.pem (PEM, ES256)
- Optional: set PAYMOB_HMAC_KEY, PAYMOB_API_KEY as env variables

## Build & Run
ssh to the VPS, clone or copy this `server/` folder, then:

- Set env (PowerShell example):
  - $env:POSTGRES_PASSWORD = "StrongPass!234"
  - $env:ADMIN_USERNAME = "admin"
  - $env:ADMIN_PASSWORD = "VeryStrong!Pass"
  - $env:ADMIN_SESSION_SECRET = "ChangeMe_LongRandomSecret"
- docker compose build
- docker compose up -d

Caddy will request and manage TLS certificates automatically (Let's Encrypt).

## API endpoints
- POST https://api.ahmedhussein.online/api/v1/activate
- GET  https://api.ahmedhussein.online/api/v1/verify
- POST https://api.ahmedhussein.online/api/v1/deactivate
- POST https://api.ahmedhussein.online/webhook/paymob

## Generate ES256 keypair (OpenSSL examples)
```
openssl ecparam -genkey -name prime256v1 -noout -out private.pem
openssl ec -in private.pem -pubout -out public.pem
```
Place them at `server/data/keys/` before running compose.

## Test locally (after deploy)
- Activate (demo license accepts keys starting with FA-):
```
curl -sS -X POST \
  https://api.ahmedhussein.online/api/v1/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key":"FA-TEST-001","hwid":"HWID123","device_limit":1}'
```
- Verify:
```
curl -sS -H "Authorization: Bearer <TOKEN>" \
  https://api.ahmedhussein.online/api/v1/verify
```
- Deactivate:
```
curl -sS -X POST -H "Content-Type: application/json" \
  -d '{"token":"<TOKEN>"}' \
  https://api.ahmedhussein.online/api/v1/deactivate
```

## Notes
- Sample uses JSON persistence on disk (`server/data/` volume). For production, replace with a database (e.g., Postgres).
- Implement Paymob webhook parsing to issue real license keys tied to successful payments.