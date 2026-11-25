$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    uv run --frozen --extra ragas ruff check backend tests scripts
    if ($LASTEXITCODE -ne 0) { throw 'Python lint failed.' }
    uv run --frozen --extra ragas ruff format --check backend tests scripts
    if ($LASTEXITCODE -ne 0) { throw 'Python formatting failed.' }
    uv run --frozen --extra ragas pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    npm --prefix eval-ui run build
    if ($LASTEXITCODE -ne 0) { throw 'Eval Lab build failed.' }
} finally { Pop-Location }
