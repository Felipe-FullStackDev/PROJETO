@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo             BIOACESSO - APS
echo ============================================
where py >nul 2>nul
if errorlevel 1 (
  set PY=python
) else (
  set PY=py
)
if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente Python...
  %PY% -m venv .venv
)
echo Instalando/verificando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRO ao instalar dependencias. Confira a conexao com a internet e a versao do Python.
  pause
  exit /b 1
)
echo.
echo Abrindo BioAcesso em http://127.0.0.1:5000
start "" http://127.0.0.1:5000
".venv\Scripts\python.exe" app.py
pause
