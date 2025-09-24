Param(
    [string]$Message = "chore: one-click commit"
)

$ErrorActionPreference = "Stop"
$repo = "d:\ahmed2025"

Write-Host "Working directory: $repo"
Set-Location $repo

# 1) Ensure venv exists
if (!(Test-Path "$repo\venv\Scripts\Activate.ps1")) {
    Write-Host "Creating virtual environment..."
    python -m venv "$repo\venv"
}

# 2) Activate venv
Write-Host "Activating virtual environment..."
. "$repo\venv\Scripts\Activate.ps1"

# 3) Install dependencies (prod + tools)
Write-Host "Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r "$repo\requirements.txt"
# Ensure tools present for this script
pip install pytest pyinstaller

# 4) Run tests if present
if (Test-Path "$repo\tests") {
    Write-Host "Running tests..."
    pytest -q
}

# 5) Build EXE using existing build script
Write-Host "Building Windows executable..."
powershell -ExecutionPolicy Bypass -File "$repo\build_exe.ps1"

# 6) Install a pre-commit hook to block heavy/generated files (if missing)
$hookPath = Join-Path $repo ".git\hooks\pre-commit"
if (!(Test-Path $hookPath)) {
    Write-Host "Installing pre-commit hook to prevent committing heavy/generated artifacts..."
    $hookContent = @'
#!/bin/sh
set -e
files=$(git diff --cached --name-only)
blocked='^venv/|^\.venv/|^app/backups/|^app/data/.*\.db$|^build/|^dist/|^server/data/|^server/updates/win/.*\.(exe|zip|msi)$|^\.idea/|^\.vscode/|\.log$'
echo "$files" | grep -E "$blocked" >/dev/null 2>&1 && {
  echo "ERROR: Blocked files staged. Unstage heavy/generated artifacts and try again." 1>&2
  exit 1
}
exit 0
'@
    Set-Content -Path $hookPath -Value $hookContent -NoNewline
}

# 7) Git add/commit/push (fast settings)
Write-Host "Staging changes..."
git -C "$repo" add -A

Write-Host "Committing..."
try {
    git -C "$repo" commit -m "$Message"
} catch {
    Write-Host "No changes to commit (skipping)."
}

Write-Host "Determining branch..."
$branch = (git -C "$repo" rev-parse --abbrev-ref HEAD).Trim()

Write-Host "Pushing to origin/$branch (fast mode)..."
git -C "$repo" -c http.version=HTTP/2 -c protocol.version=2 -c pack.threads=0 -c pack.compression=1 push origin $branch

# 8) Launch the app (built EXE preferred, fallback to dev run)
$env:FARMAPP_DEV = "1"  # enable dev license bypass for local run
$exePath = Join-Path $repo "dist\FarmApp\FarmApp.exe"
if (Test-Path $exePath) {
    Write-Host "Launching built app: $exePath (dev bypass ON)"
    Start-Process -FilePath $exePath -Environment @{ FARMAPP_DEV = "1" }
} else {
    Write-Host "Built EXE not found, launching development app instead (dev bypass ON)..."
    python -m app.main
}

Write-Host "All done."