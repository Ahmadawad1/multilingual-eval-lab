$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' }
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'Install Node.js 22.12+ or 24 LTS first: https://nodejs.org/' }
    uv sync --extra ragas --frozen
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    npm --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    npm --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    npm --prefix eval-ui ci
    if ($LASTEXITCODE -ne 0) { throw 'Eval Lab dependency installation failed.' }
    npm --prefix eval-ui run build
    if ($LASTEXITCODE -ne 0) { throw 'Eval Lab build failed.' }
    Write-Host 'Setup complete. Run .\scripts\start.ps1, then open http://127.0.0.1:8000'
} finally { Pop-Location }
