param(
    [string]$VpsHost = "37.60.224.136",
    [string]$VpsUser = "root",
    [string]$AppDir = "/root",
    # Use root domain (no subdomains)
    [string]$DomainApi = "ahmedhussein.online",
    [string]$DomainUpdates = "ahmedhussein.online",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "Strong#2025",
    [string]$LocalServerPath = "d:\ahmed2025\server",
    [string]$LogFile = "d:\ahmed2025\deploy_to_vps.log"
)

# Fail on error
$ErrorActionPreference = "Stop"

function Ensure-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "Missing command: $Name. Install OpenSSH Client from Windows Optional Features."
        exit 1
    }
}

# Start logging
"==== $(Get-Date -Format 'u') | Start Deploy ====" | Out-File -FilePath $LogFile -Encoding UTF8 -Append
"VpsHost=$VpsHost VpsUser=$VpsUser AppDir=$AppDir" | Out-File -FilePath $LogFile -Append
"LocalServerPath=$LocalServerPath" | Out-File -FilePath $LogFile -Append

Ensure-Command "scp"
Ensure-Command "ssh"

if (-not (Test-Path $LocalServerPath)) {
    $msg = "Local server folder not found: $LocalServerPath"
    $msg | Tee-Object -FilePath $LogFile -Append | Write-Error
    Read-Host "Press Enter to exit"
    exit 1
}

# Faster upload: archive server folder into a single tar.gz
Write-Host "[1/3] Packing and uploading server/ as a single archive ..." -ForegroundColor Cyan
"[1/3] tar+scp start" | Out-File -FilePath $LogFile -Append
$TmpArchive = Join-Path $env:TEMP ("server-" + (Get-Date -Format "yyyyMMddHHmmss") + ".tar.gz")
# Create archive from repo root to keep 'server' as top-level folder
# Exclude local Postgres data dir (locked/huge); it's recreated on VPS
& tar -C "d:\ahmed2025" --exclude "server/data/pg" --exclude "server/data/pg/*" -czf "$TmpArchive" server
if ($LASTEXITCODE -ne 0) {
    $msg = "Failed to create archive: $TmpArchive"
    $msg | Tee-Object -FilePath $LogFile -Append | Write-Error
    Read-Host "Press Enter to exit"
    exit 1
}
& scp -o StrictHostKeyChecking=no "$TmpArchive" "$VpsUser@${VpsHost}:/tmp/farmapp_server.tgz"
$code=$LASTEXITCODE
"[1/3] scp exit code: $code" | Out-File -FilePath $LogFile -Append
Remove-Item -Force "$TmpArchive" -ErrorAction SilentlyContinue
if ($code -ne 0) {
    $msg = "Upload failed (scp) with code $code"
    $msg | Tee-Object -FilePath $LogFile -Append | Write-Error
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[2/3] Running remote install script ..." -ForegroundColor Cyan
$remoteCmd = "export APP_DIR='$AppDir' DOMAIN_API='$DomainApi' DOMAIN_UPDATES='$DomainUpdates' ADMIN_USERNAME='$AdminUsername' ADMIN_PASSWORD='$AdminPassword'; bash -lc 'mkdir -p $AppDir; tar -xzf /tmp/farmapp_server.tgz -C $AppDir; cd $AppDir/server; chmod +x deploy_vps.sh; ./deploy_vps.sh'"
"[2/3] ssh start" | Out-File -FilePath $LogFile -Append
& ssh -o StrictHostKeyChecking=no "$VpsUser@${VpsHost}" $remoteCmd
$code=$LASTEXITCODE
"[2/3] ssh exit code: $code" | Out-File -FilePath $LogFile -Append
if ($code -ne 0) {
    $msg = "Remote install failed with code $code"
    $msg | Tee-Object -FilePath $LogFile -Append | Write-Error
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[3/3] Done. Check:" -ForegroundColor Green
Write-Host "  - https://$DomainApi/api/admin"
Write-Host "  - https://$DomainApi/updates/"
"==== $(Get-Date -Format 'u') | Deploy OK ====" | Out-File -FilePath $LogFile -Append

Read-Host "Press Enter to exit"