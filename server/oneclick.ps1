#requires -Version 5.1
$ErrorActionPreference = 'Stop'

# ========== Simple logger ==========
$logFile = Join-Path $PSScriptRoot 'oneclick.log'
Function Log($msg) { $ts = (Get-Date).ToString('s'); "$ts`t$msg" | Tee-Object -FilePath $logFile -Append }

# ========== Docker Desktop helpers ==========
Function Start-DockerDesktop {
    # Detect running processes for Docker Desktop/engine
    $running = @(Get-Process -Name 'com.docker.backend','Docker Desktop' -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) { return }

    $candidates = @(
        (Join-Path $Env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'),
        (Join-Path ${Env:ProgramFiles(x86)} 'Docker\Docker\Docker Desktop.exe'),
        (Join-Path $Env:LocalAppData 'Docker\Docker\Docker Desktop.exe')
    )
    $exe = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if ($exe) {
        Log "Starting Docker Desktop: $exe"
        Start-Process -FilePath $exe | Out-Null
    } else {
        throw 'Docker Desktop not found. Please install Docker Desktop for Windows.'
    }
}

Function Wait-DockerEngine {
    Param([int]$TimeoutSec = 180)
    $start = Get-Date
    while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds($TimeoutSec)) {
        try {
            $null = & docker version 2>$null
            if ($LASTEXITCODE -eq 0) { Log 'Docker engine is ready.'; return }
        } catch {}
        Start-Sleep -Seconds 3
        Write-Host '.' -NoNewline
    }
    Write-Host ''
    throw 'Timed out waiting for Docker engine.'
}

try {
    # Move to script directory
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptDir

    $DOMAIN = 'ahmedhussein.online'
    Log '==> FarmApp Licensing API one-click deploy (Windows)'

    # Check Docker CLI
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker CLI is not installed or not in PATH.'
    }

    # Ensure Docker Desktop is running and engine ready
    Start-DockerDesktop
    Log 'Waiting for Docker engine to be ready...'
    Wait-DockerEngine -TimeoutSec 240

    # Detect compose command
    $composeCmd = 'docker compose'
    $composeVersion = (& docker compose version) 2>$null
    if (-not $composeVersion) {
        $composeVersion = (& docker-compose --version) 2>$null
        if ($composeVersion) { $composeCmd = 'docker-compose' } else { throw 'docker compose is not available.' }
    }
    Log "Using compose command: $composeCmd"

    # Ensure data\keys dir
    $newKeysDir = Join-Path $scriptDir 'data\keys'
    New-Item -ItemType Directory -Path $newKeysDir -Force | Out-Null

    # Create .env if missing
    $envPath = Join-Path $scriptDir '.env'
    if (-not (Test-Path $envPath)) {
        Log 'Generating .env'
        $POSTGRES_PASSWORD = [Guid]::NewGuid().ToString('N')
        $ADMIN_PASSWORD = [Guid]::NewGuid().ToString('N')
        $ADMIN_SESSION_SECRET = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes([Guid]::NewGuid().ToString() + [Guid]::NewGuid().ToString()))
        @"
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD
ADMIN_SESSION_SECRET=$ADMIN_SESSION_SECRET
PAYMOB_HMAC_KEY=
PAYMOB_API_KEY=
"@ | Set-Content -Encoding UTF8 $envPath
    } else {
        Log '.env exists. Skipping.'
    }

    # Generate ES256 keys if missing
    $privKey = Join-Path $newKeysDir 'private.pem'
    $pubKey  = Join-Path $newKeysDir 'public.pem'
    if (-not (Test-Path $privKey) -or -not (Test-Path $pubKey)) {
        Log 'Generating ES256 keys'
        if (Get-Command openssl -ErrorAction SilentlyContinue) {
            & openssl ecparam -genkey -name prime256v1 -noout -out $privKey
            & openssl ec -in $privKey -pubout -out $pubKey
        } else {
            Log 'OpenSSL not found. Using Docker (alpine with openssl)'
            & docker run --rm -v "$($newKeysDir):/keys" alpine:3 sh -c "apk add --no-cache openssl >/dev/null && openssl ecparam -genkey -name prime256v1 -noout -out /keys/private.pem && openssl ec -in /keys/private.pem -pubout -out /keys/public.pem"
        }
    } else {
        Log 'Keys already exist. Skipping.'
    }

    Log 'Starting Docker stack'
    if ($composeCmd -eq 'docker-compose') {
        & docker-compose up -d --build
    } else {
        & docker compose up -d --build
    }

    Write-Host ''
    Write-Host 'All set!'
    Write-Host "- Admin: https://$DOMAIN/api -> redirects to /api/admin"
    Write-Host "- Activate: POST https://$DOMAIN/api/v1/activate"
    Write-Host "- Verify: GET https://$DOMAIN/api/v1/verify"
    Write-Host ''
    if ($composeCmd -eq 'docker-compose') {
        Write-Host 'To see logs: docker-compose logs -f caddy api'
    } else {
        Write-Host 'To see logs: docker compose logs -f caddy api'
    }

} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Log "ERROR: $($_.Exception.ToString())"
} finally {
    Write-Host ''
    Write-Host "Log saved to: $logFile"
    Read-Host 'Press Enter to close'
}