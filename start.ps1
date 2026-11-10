# Optional Windows equivalent. No privileged installs and no model-weight downloads.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host "`nExpenseGuard AI — Starting...`n"
$Python = $null
$Candidates = @('python3.12', 'python3.11', 'python')
if ($env:EXPENSEGUARD_PYTHON) { $Candidates = @($env:EXPENSEGUARD_PYTHON) }
foreach ($Candidate in $Candidates) {
    if (Get-Command $Candidate -ErrorAction SilentlyContinue) {
        & $Candidate -c 'import sys; raise SystemExit(0 if sys.version_info[:2] in [(3,11),(3,12)] else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { $Python = $Candidate; break }
    }
}
if (!$Python) { throw 'Install Python 3.11 or 3.12 or set EXPENSEGUARD_PYTHON.' }
if (!(Test-Path '.venv')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
$Venv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $Venv)) { throw 'Incomplete .venv; rename it and retry.' }
& $Venv -c 'import sys; assert sys.version_info[:2] in [(3,11),(3,12)]'
if ($LASTEXITCODE -ne 0) { throw 'Existing .venv uses unsupported Python.' }
Write-Host '[OK] Python environment ready'
$Lock = Join-Path $PSScriptRoot '.venv\.expenseguard-setup.lock'
New-Item -ItemType Directory -Path $Lock -ErrorAction Stop | Out-Null
try {
    $Stamp = Join-Path $PSScriptRoot '.venv\.expenseguard-dependencies.sha256'
    $Digest = & $Venv -c 'import hashlib,platform,sys; from pathlib import Path; print(hashlib.sha256(Path("requirements.txt").read_bytes()+sys.version.encode()+platform.machine().encode()).hexdigest())'
    if ($LASTEXITCODE -ne 0) { throw 'Could not compute dependency fingerprint.' }
    $Ready = $false
    if ((Test-Path $Stamp) -and ((Get-Content $Stamp -Raw).Trim() -eq $Digest)) {
        & $Venv scripts/check_environment.py --dependencies-only 2>$null
        $Ready = $LASTEXITCODE -eq 0
    }
    if (!$Ready) {
        & $Venv -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Retry when online.' }
        & $Venv scripts/check_environment.py --dependencies-only
        if ($LASTEXITCODE -ne 0) { throw 'Dependency validation failed.' }
        Set-Content -Path $Stamp -Value $Digest
        Write-Host '[OK] Dependencies installed'
    } else { Write-Host '[OK] Dependencies already installed — skipping installation' }
    if (!(Test-Path '.env')) { Copy-Item '.env.example' '.env' }
    New-Item -ItemType Directory -Force -Path 'data', '.local/logs', '.local/cache' | Out-Null
    if (!(Test-Path 'data/synthetic_expenses.csv')) {
        & $Venv scripts/generate_data.py --rows 1200 --seed 42
        if ($LASTEXITCODE -ne 0) { throw 'Demo generation failed.' }
    }
    Write-Host '[OK] Demo dataset available'
    & $Venv scripts/check_environment.py
    if ($LASTEXITCODE -ne 0) { throw 'Check .env and project configuration.' }
    Write-Host '[OK] Application configuration ready'
} finally { Remove-Item -Path $Lock -Force -ErrorAction SilentlyContinue }
Write-Host "`nStarting ExpenseGuard AI...`n"
& $Venv -m streamlit run app/main.py --server.address 127.0.0.1 @args
exit $LASTEXITCODE
