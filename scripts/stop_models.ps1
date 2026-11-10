$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logRoot = Join-Path $projectRoot 'state/model_servers'
if (Test-Path -LiteralPath $logRoot) {
    Get-ChildItem -LiteralPath $logRoot -Filter '*.json' | ForEach-Object {
        $record = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
        $serverProcess = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
        if ($serverProcess -and $serverProcess.Path -eq $record.executable) { Stop-Process -Id $record.pid }
    }
}
