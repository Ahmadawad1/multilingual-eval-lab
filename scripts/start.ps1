param([switch]$Reload)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv')) { throw 'Run .\scripts\setup.ps1 first.' }
    if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) { throw 'Build the frontend: npm --prefix frontend run build' }
    # Parse only supported keys as literal strings; never evaluate .env as shell code.
    if (Test-Path -LiteralPath '.env') {
        foreach ($line in Get-Content -LiteralPath '.env') {
            if ($line -match '^\s*(EVAL_DATA_DIR|LOCAL_LLM_PROVIDER|LOCAL_LLM_URL|LOCAL_LLM_MODEL)\s*=(.*)$') {
                $configName = $Matches[1]
                $configValue = $Matches[2].Trim().Trim('"').Trim("'")
                [Environment]::SetEnvironmentVariable($configName, $configValue, 'Process')
            }
        }
    }
    $serverArguments = @('run', '--frozen', '--no-sync', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000')
    if ($Reload) { $serverArguments += '--reload' }
    Write-Host 'Multilingual Eval Lab: http://127.0.0.1:8000 (Ctrl+C to stop)'
    & uv @serverArguments
    if ($LASTEXITCODE -ne 0) { throw 'Local server stopped with an error. Check port 8000 and the log above.' }
} finally { Pop-Location }

