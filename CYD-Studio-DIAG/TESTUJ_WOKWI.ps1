# Wokwi: build, launch actual emulated firmware, screenshot 7 scenes, test clicks.
# Requires installed PlatformIO, Wokwi CLI and an API token in $env:WOKWI_CLI_TOKEN.
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Demo = Join-Path $Root 'examples\15_LVGL_Galeria_Komponentow_PlatformIO'
$Pio = Get-Command pio -ErrorAction SilentlyContinue
if ($Pio) { $PioPath = $Pio.Source }
else { $PioPath = Join-Path $env:USERPROFILE '.platformio\penv\Scripts\pio.exe' }
if (!(Test-Path $PioPath)) { throw 'BRAK PlatformIO: zainstaluj wtyczke PlatformIO w VS Code.' }
$Wokwi = Get-Command wokwi-cli -ErrorAction SilentlyContinue
if (!$Wokwi) { throw 'BRAK Wokwi CLI: https://docs.wokwi.com/wokwi-ci/cli-installation' }
if (!$env:WOKWI_CLI_TOKEN) { throw 'BRAK WOKWI_CLI_TOKEN: ustaw token z https://wokwi.com/dashboard/ci' }
Push-Location $Demo
try {
  New-Item -ItemType Directory -Force 'sim_screens' | Out-Null
  & $PioPath run -e sim
  if ($LASTEXITCODE -ne 0) { throw 'Kompilacja ESP32 nieudana' }
  $Full = '.pio\build\sim\firmware.merged.bin'
  if (!(Test-Path $Full)) { throw 'Nie powstal pelny obraz Flash do Wokwi' }
  & $Wokwi.Source . --scenario screens.test.yaml --timeout 60000 --serial-log-file sim_screens\wokwi_screens.log
  if ($LASTEXITCODE -ne 0) { throw 'Symulator zatrzymal sie z bledem (screens)' }
  & $Wokwi.Source . --scenario clicks.test.yaml --timeout 90000 --serial-log-file sim_screens\wokwi_clicks.log
  if ($LASTEXITCODE -ne 0) { throw 'Symulator zatrzymal sie z bledem (clicks)' }
  $Captured = @(Get-ChildItem 'sim_screens\scene_*.png' -ErrorAction SilentlyContinue)
  if ($Captured.Count -ne 7) { throw "Oczekiwano 7 zrzutow LVGL, znaleziono $($Captured.Count)." }
  Write-Host 'GOTOWE: 7 ekranow z prawdziwego renderera LVGL Wokwi i testy klikniec' -ForegroundColor Green
  Write-Host (Join-Path $Demo 'sim_screens') -ForegroundColor Cyan
} finally { Pop-Location }