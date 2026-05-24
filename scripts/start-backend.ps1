$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $Root "backend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Port = if ($env:FOCUS_GUARD_PORT) { $env:FOCUS_GUARD_PORT } else { "8787" }

if (-not (Test-Path $VenvDir)) {
    Write-Host "Backend virtualenv not found — running setup ..."
    & (Join-Path $PSScriptRoot "setup-backend.ps1")
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Set-Location $BackendDir

Write-Host "Starting Focus Guard backend on http://127.0.0.1:${Port}"
& $VenvPython -m uvicorn main:app `
    --reload `
    --reload-dir $BackendDir `
    --reload-include "*.py" `
    --reload-exclude "config.json" `
    --reload-exclude "gaze_calibration.json" `
    --reload-exclude "assets/*" `
    --reload-exclude "yolov8n.pt" `
    --reload-exclude "__pycache__/*" `
    --host 127.0.0.1 `
    --port $Port

exit $LASTEXITCODE
