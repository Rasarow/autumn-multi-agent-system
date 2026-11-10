$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$serverExe = Join-Path $projectRoot 'runtime/llama/llama-server.exe'
$modelRoot = Join-Path $projectRoot 'models'
$logRoot = Join-Path $projectRoot 'state/model_servers'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$specifications = @(@('0.8B','0.8b',8181),@('2B','2b',8182),@('4B','4b',8183))
foreach ($modelSpec in $specifications) {
    $modelFile = Join-Path $modelRoot ('Qwen3.5-' + $modelSpec[0] + '-Q4_K_M.gguf')
    $argumentList = @('-m',('"' + $modelFile + '"'),'--alias',('qwen35-' + $modelSpec[1]),'--host','127.0.0.1','--port',$modelSpec[2],'-c','4096','-ngl','99','--device','Vulkan0','-t','4','-b','128','-ub','128','--parallel','1','--no-webui','--reasoning-budget','0')
    $serverProcess = Start-Process -FilePath $serverExe -ArgumentList $argumentList -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot ($modelSpec[1] + '.out.log')) -RedirectStandardError (Join-Path $logRoot ($modelSpec[1] + '.err.log')) -PassThru
    @{pid=$serverProcess.Id; executable=$serverExe; port=$modelSpec[2]} | ConvertTo-Json | Set-Content (Join-Path $logRoot ($modelSpec[1] + '.json'))
    Write-Output ('Starting ' + $modelSpec[0] + ' on port ' + $modelSpec[2])
}
Write-Output 'Wait for each /health endpoint to return ok before asking questions. See server logs on failure.'
