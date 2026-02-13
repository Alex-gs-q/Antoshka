$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

if (Test-Path .\dist\AntoshkaApp\AntoshkaApp.exe) {
  try { Stop-Process -Name AntoshkaApp -Force -ErrorAction SilentlyContinue } catch {}
}

.\.venv\Scripts\python.exe -m PyInstaller Antoshka_pyinstaller.spec

if (Test-Path .\dist\AntoshkaApp\AntoshkaApp.exe) {
  Compress-Archive -Force -Path .\dist\AntoshkaApp\* -DestinationPath .\dist\AntoshkaApp_Windows.zip
  Write-Host "Build OK: dist\\AntoshkaApp\\AntoshkaApp.exe"
  Write-Host "ZIP OK: dist\\AntoshkaApp_Windows.zip"
  Write-Host "Running self-test..."
  & .\dist\AntoshkaApp\AntoshkaApp.exe --self-test
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Self-test FAILED" -ForegroundColor Red
    exit 1
  }
  Write-Host "Self-test PASSED"
} else {
  Write-Host "Build failed: dist\\AntoshkaApp\\AntoshkaApp.exe not found" -ForegroundColor Red
  exit 1
}
