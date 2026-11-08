$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
  $pio = Get-Command pio -ErrorAction SilentlyContinue
  if ($pio) { $cmd=$pio.Source }
  else { $cmd=Join-Path $env:USERPROFILE '.platformio\penv\Scripts\pio.exe' }
  if (-not (Test-Path $cmd)) { throw 'Brak PlatformIO (pio.exe). Zainstaluj PlatformIO w VS Code.' }
  & $cmd run -e sim
  if ($LASTEXITCODE -ne 0) { throw 'Kompilacja SIM nie powiodla sie. Sprawdz bledy powyzej.' }
  Write-Host 'BIN symulatora: .pio\build\sim\firmware.merged.bin' -ForegroundColor Green
  Write-Host 'W VS Code nacisnij F1 > Wokwi: Start Simulator.' -ForegroundColor Cyan
  Write-Host 'Opcjonalnie: wokwi-cli . --scenario screens.test.yaml' -ForegroundColor Cyan
  Write-Host 'Uwaga: Wokwi nie emuluje XPT2046. Komenda @SIM TAP x y testuje tylko logike.'
} finally { Pop-Location }