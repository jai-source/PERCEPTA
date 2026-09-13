# PERCEPTA Windows launcher
param(
    [switch]$InstallOnly,
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$workspaceVenv = Join-Path $root '.venv'
$venv = if (Test-Path $workspaceVenv) { $workspaceVenv } else { Join-Path $backend 'venv' }
$python = Join-Path $venv 'Scripts\python.exe'
$readyMarker = Join-Path $venv 'percepta-ready.txt'

Write-Host 'PERCEPTA launcher' -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python was not found. Install Python 3.11 or newer.'
}
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js was not found. Install Node.js 18 or newer.'
}

if (-not (Test-Path $python)) {
    Write-Host 'Creating backend virtual environment...' -ForegroundColor Yellow
    & python -m venv $venv
}

if (-not (Test-Path $python)) {
    Write-Host 'Creating backend virtual environment...' -ForegroundColor Yellow
    & python -m venv $venv
}

if (-not $SkipInstall -and -not (Test-Path $readyMarker)) {
    Write-Host 'Installing backend dependencies...' -ForegroundColor Yellow
    & $python -c "import fastapi, uvicorn" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install -r (Join-Path $backend 'requirements.txt')
    }
    New-Item -ItemType File -Path $readyMarker -Force | Out-Null
} elseif (Test-Path $readyMarker) {
    Write-Host 'Backend dependencies already installed.' -ForegroundColor DarkGray
}

Write-Host 'Downloading and validating YOLO models...' -ForegroundColor Yellow
& $python (Join-Path $root 'scripts\download_models.py')

if (-not $SkipInstall -and -not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host 'Installing frontend dependencies...' -ForegroundColor Yellow
    Push-Location $frontend
    try {
        & npm install
    } finally {
        Pop-Location
    }
} elseif (Test-Path (Join-Path $frontend 'node_modules')) {
    Write-Host 'Frontend dependencies already installed.' -ForegroundColor DarkGray
}

if ($InstallOnly) {
    Write-Host 'PERCEPTA dependencies and cached models are ready.' -ForegroundColor Cyan
    exit 0
}

$envFile = Join-Path $backend '.env'
if (-not (Test-Path $envFile)) {
    $rootEnv = Join-Path $root '.env.example'
    $backendEnv = Join-Path $backend '.env.example'
    if (Test-Path $rootEnv) {
        Copy-Item $rootEnv $envFile
    } elseif (Test-Path $backendEnv) {
        Copy-Item $backendEnv $envFile
    }
}

Write-Host 'Checking backend at http://localhost:8000...' -ForegroundColor Yellow
$backendReady = $false
try {
    $health = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -TimeoutSec 3
    if ($health.StatusCode -eq 200) {
        $backendReady = $true
        Write-Host 'Backend is already running; reusing it.' -ForegroundColor DarkGray
    }
} catch {
    $backendReady = $false
}

if (-not $backendReady) {
    Write-Host 'Starting backend at http://localhost:8000' -ForegroundColor Green
    Start-Process -FilePath $python -WorkingDirectory $root -ArgumentList @('-m', 'uvicorn', 'backend.main:app', '--host', '0.0.0.0', '--port', '8000', '--log-level', 'info') -WindowStyle Normal
    Write-Host 'Waiting for backend health check...' -ForegroundColor Yellow
}

for ($attempt = 1; $attempt -le 90 -and -not $backendReady; $attempt++) {
    try {
        $health = Invoke-WebRequest -Uri 'http://localhost:8000/api/health' -UseBasicParsing -TimeoutSec 2
        if ($health.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {
        Write-Host "  Backend is still loading models... ($($attempt * 2)s)" -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }
}
if (-not $backendReady) {
    throw 'Backend did not become ready on http://localhost:8000. Check the backend PowerShell window for details.'
}

Write-Host 'Checking frontend at http://localhost:5173...' -ForegroundColor Yellow
$frontendReady = $false
try {
    $frontendHealth = Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 3
    if ($frontendHealth.StatusCode -eq 200) {
        $frontendReady = $true
        Write-Host 'Frontend is already running; reusing it.' -ForegroundColor DarkGray
    }
} catch {
    $frontendReady = $false
}
if (-not $frontendReady) {
    Write-Host 'Starting frontend at http://localhost:5173' -ForegroundColor Green
    $frontendCommand = "Set-Location '$frontend'; npm run dev"
    Start-Process powershell.exe -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $frontendCommand
}

for ($attempt = 1; $attempt -le 30 -and -not $frontendReady; $attempt++) {
    try {
        $frontendHealth = Invoke-WebRequest -Uri 'http://localhost:5173' -UseBasicParsing -TimeoutSec 2
        if ($frontendHealth.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $frontendReady) {
    throw 'Frontend did not become ready on http://localhost:5173. Check the frontend PowerShell window for details.'
}

Write-Host ''
Write-Host 'PERCEPTA is ready.' -ForegroundColor Cyan
Write-Host 'Backend:  http://localhost:8000  (models loaded, WebSocket listening)' -ForegroundColor Green
Write-Host 'Frontend: http://localhost:5173  (Vite ready)' -ForegroundColor Green
Start-Process 'http://localhost:5173'
