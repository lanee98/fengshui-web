$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
Set-Location -LiteralPath $projectDir
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
$pythonCandidates = @(
    (Join-Path $projectDir '.venv\Scripts\python.exe'),
    (Join-Path $projectDir 'venv\Scripts\python.exe'),
    'D:\anaconda3\python.exe'
)
foreach ($commandName in @('python','py')) {
    $command = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($command) { $pythonCandidates += $command.Source }
}
$chosenPython = $null
$availablePython = $null
foreach ($candidate in ($pythonCandidates | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    try { & $candidate -B -c 'import sys; sys.exit(0 if sys.version_info >= (3, 7) else 1)' 2>$null }
    catch { continue }
    if ($LASTEXITCODE -ne 0) { continue }
    if (-not $availablePython) { $availablePython = $candidate }
    $flaskProbe = "import sys`ntry:`n import flask`nexcept Exception:`n sys.exit(1)"
    try { & $candidate -B -c $flaskProbe 2>$null }
    catch { continue }
    if ($LASTEXITCODE -eq 0) { $chosenPython = $candidate; break }
}
if (-not $chosenPython) {
    if (-not $availablePython) { throw '未找到 Python。请先安装 Python 3.9 或以上版本，然后重新启动。' }
    Write-Host '正在创建项目环境并安装 Flask；首次安装需要联网。'
    $venvDir = Join-Path $projectDir '.venv'
    & $availablePython -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw '创建 Python 环境失败。' }
    $chosenPython = Join-Path $venvDir 'Scripts\python.exe'
    & $chosenPython -m pip install -r (Join-Path $projectDir 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw '依赖安装失败。请检查网络后重试。' }
}
& $chosenPython -B -u (Join-Path $projectDir 'start.py')
if ($LASTEXITCODE -ne 0) { throw '启动失败，请查看上方错误。' }
