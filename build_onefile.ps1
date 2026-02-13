$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

try { Stop-Process -Name AntoshkaApp -Force -ErrorAction SilentlyContinue } catch {}

.\.venv\Scripts\python.exe -m PyInstaller Antoshka_onefile.spec

if (Test-Path .\dist\Antoshka_onefile.exe) {
  Compress-Archive -Force -Path .\dist\Antoshka_onefile.exe -DestinationPath .\dist\Antoshka_onefile_Windows.zip
  Write-Host "Build OK: dist\\Antoshka_onefile.exe"
  Write-Host "ZIP OK: dist\\Antoshka_onefile_Windows.zip"
  Write-Host "Running self-test..."
  & .\dist\Antoshka_onefile.exe --self-test
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Self-test FAILED" -ForegroundColor Red
    exit 1
  }
  Write-Host "Self-test PASSED"
} else {
  Write-Host "Build failed: dist\\Antoshka_onefile.exe not found" -ForegroundColor Red
  exit 1
}
