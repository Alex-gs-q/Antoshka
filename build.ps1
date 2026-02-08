$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

if (Test-Path .\dist\AntoshkaApp.exe) {
  try { Stop-Process -Name AntoshkaApp -Force -ErrorAction SilentlyContinue } catch {}
}

.\.venv\Scripts\python.exe -m PyInstaller Antoshka_pyinstaller.spec

if (Test-Path .\dist\AntoshkaApp.exe) {
  Compress-Archive -Force -Path .\dist\AntoshkaApp.exe -DestinationPath .\dist\AntoshkaApp_Windows.zip
  Write-Host "Build OK: dist\\AntoshkaApp.exe"
  Write-Host "ZIP OK: dist\\AntoshkaApp_Windows.zip"
} else {
  Write-Host "Build failed: dist\\AntoshkaApp.exe not found" -ForegroundColor Red
  exit 1
}
