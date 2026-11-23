$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    uv run --frozen ruff check backend tests scripts
    if ($LASTEXITCODE -ne 0) { throw 'Python lint failed.' }
    uv run --frozen ruff format --check backend tests scripts
    if ($LASTEXITCODE -ne 0) { throw 'Python formatting failed.' }
    uv run --frozen pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    npm --prefix frontend run format:check
    if ($LASTEXITCODE -ne 0) { throw 'Frontend formatting failed.' }
    npm --prefix frontend run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    npm --prefix eval-ui run build
    if ($LASTEXITCODE -ne 0) { throw 'Eval Lab build failed.' }
} finally { Pop-Location }
