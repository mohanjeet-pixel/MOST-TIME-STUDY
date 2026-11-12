# Bulls Eye - one-click start (Windows)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
# Python 3.12: its compiled packages are trusted by Windows Smart App Control (3.15 builds were blocked)
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Host "Created .env - add your GEMINI_API_KEY" }
Write-Host "Bulls Eye running at http://localhost:8000"
& .\.venv\Scripts\python.exe -m uvicorn bullseye.main:app --host 127.0.0.1 --port 8000
