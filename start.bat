@echo off
REM SuperNova Search - Windows Quick Start
REM ================================
echo.
echo  ================================================
echo  ^|^|  SuperNova Search - Privacy-First Search
echo  ================================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting SuperNova Search on http://localhost:8080
echo Press Ctrl+C to stop
echo.
python -m atomic_search.main
pause
