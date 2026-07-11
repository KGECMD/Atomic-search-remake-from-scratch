# SuperNova Search - PowerShell Quick Start
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "||  SuperNova Search - Privacy-First Search  ||" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting SuperNova Search on http://localhost:8080" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

python -m atomic_search.main
