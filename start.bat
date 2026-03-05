@echo off
echo Iniciando Cerebro Local AI...

echo.
echo Iniciando API (Backend)...
start cmd /k "python -m uvicorn api.main:app --port 8000"

echo.
echo Iniciando Frontend...
start cmd /k "python -m http.server 3000 --directory frontend"

echo.
echo Iniciando Bot de Telegram...
start cmd /k "python bot.py"

echo.
echo Todo iniciado.
echo API: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo Bot: Corriendo en consola separada.
