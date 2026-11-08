    $ErrorActionPreference = 'Stop'
    Set-Location $PSScriptRoot
    $candidates = @(
        (Join-Path $env:USERPROFILE '.platformio\penv\Scripts\python.exe'),
        (Join-Path $env:USERPROFILE '.platformio\python3\python.exe')
    )
    $py = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($py) {
        & $py (Join-Path $PSScriptRoot 'launch_studio.py')
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 (Join-Path $PSScriptRoot 'launch_studio.py')
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python (Join-Path $PSScriptRoot 'launch_studio.py')
    } else {
        Write-Host 'BLAD: Nie znaleziono Python 3. Zainstaluj PlatformIO/Python.' -ForegroundColor Red
        exit 1
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }