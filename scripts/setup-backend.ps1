$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir = Join-Path $Root "backend"
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $BackendDir "requirements.txt"

function Get-Python312 {
    $candidates = @(
        @{ Command = "py"; Args = @("-3.12") },
        @{ Command = "python3.12"; Args = @() },
        @{ Command = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        try {
            $versionOutput = & $candidate.Command @($candidate.Args + @("--version")) 2>&1
            if ($LASTEXITCODE -ne 0 -and $candidate.Command -ne "python") {
                continue
            }
            $versionText = ($versionOutput | Out-String).Trim()
            if ($versionText -match "3\.12\.") {
                return @{ Command = $candidate.Command; Args = $candidate.Args }
            }
        } catch {
            continue
        }
    }

    return $null
}

$python = Get-Python312
if ($null -eq $python) {
    Write-Host "Python 3.12 is required but was not found on PATH."
    Write-Host "Install from https://www.python.org/downloads/"
    Write-Host 'Enable "Add python.exe to PATH" and the Python launcher (py) during setup.'
    exit 1
}

if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating backend virtualenv at backend\.venv ..."
    & $python.Command @($python.Args + @("-m", "venv", $VenvDir))
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host "Installing backend Python dependencies ..."
& $VenvPython -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Backend setup complete."
