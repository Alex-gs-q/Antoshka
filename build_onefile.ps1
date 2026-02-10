$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

try { Stop-Process -Name AntoshkaApp -Force -ErrorAction SilentlyContinue } catch {}

.\.venv\Scripts\python.exe -m PyInstaller Antoshka_pyinstaller.spec --onefile

if (Test-Path .\dist\AntoshkaApp.exe) {
  Compress-Archive -Force -Path .\dist\AntoshkaApp.exe -DestinationPath .\dist\AntoshkaApp_Windows_onefile.zip
  Write-Host "Build OK: dist\\AntoshkaApp.exe"
  Write-Host "ZIP OK: dist\\AntoshkaApp_Windows_onefile.zip"
  Write-Host "Running self-test..."
  & .\dist\AntoshkaApp.exe --self-test
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Self-test FAILED" -ForegroundColor Red
    exit 1
  }
  Write-Host "Self-test PASSED"
} else {
  Write-Host "Build failed: dist\\AntoshkaApp.exe not found" -ForegroundColor Red
  exit 1
}
