@echo off
setlocal
title VoceoStock - Setup Frontend (Persona 3)

echo ============================================================
echo   VoceoStock - Instalacion de entorno FRONTEND (Persona 3)
echo ------------------------------------------------------------
echo   Instala Node.js si falta, las dependencias del frontend
echo   y verifica corriendo las pruebas con vitest.
echo   Idempotente: lo que ya este instalado se omite.
echo ============================================================
echo.

REM La carpeta del .bat = raiz del repo
cd /d "%~dp0"

if not exist "frontend\package.json" (
    echo [ERROR] No encuentro frontend\package.json.
    echo         Ejecuta este .bat desde la raiz del repo VoceoStock.
    goto :fin
)

REM ------------------------------------------------------------
REM 1) Node.js LTS
REM ------------------------------------------------------------
set "NODE_OK="
where node >nul 2>nul && set "NODE_OK=1"
if not defined NODE_OK if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_OK=1"

if not defined NODE_OK (
    echo [..] Instalando Node.js LTS con winget...
    winget install --id OpenJS.NodeJS.LTS -e --source winget --accept-package-agreements --accept-source-agreements
    REM winget devuelve error si Node ya estaba sin upgrade: no confiamos en su
    REM codigo de salida, verificamos que node.exe exista.
    where node >nul 2>nul && set "NODE_OK=1"
    if not defined NODE_OK if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_OK=1"
)

if not defined NODE_OK (
    echo.
    echo [ERROR] No se pudo instalar Node.js.
    echo         Instalalo a mano desde https://nodejs.org y reintenta.
    goto :fin
)

REM Asegurar node/npm en el PATH de ESTA ventana (recien instalado no se refresca)
where node >nul 2>nul || set "PATH=%ProgramFiles%\nodejs;%PATH%"

echo [OK] Node.js:
node -v
echo [OK] npm:
call npm -v
echo.

REM ------------------------------------------------------------
REM 2) Dependencias del frontend
REM ------------------------------------------------------------
echo [..] Instalando dependencias del frontend (npm install)...
pushd frontend
call npm install
if errorlevel 1 (
    echo [ERROR] npm install fallo. Revisa la salida de arriba.
    popd
    goto :fin
)
echo [OK] Dependencias instaladas.
echo.

REM ------------------------------------------------------------
REM 3) Verificacion: pruebas
REM ------------------------------------------------------------
echo [..] Corriendo pruebas (vitest)...
call npm test
set "TEST_RC=%errorlevel%"
popd

echo.
if "%TEST_RC%"=="0" goto :ok
echo [AVISO] Las pruebas no pasaron. Revisa la salida de arriba.
goto :fin

:ok
echo ============================================================
echo   LISTO. Entorno frontend instalado y verificado.
echo.
echo   Desarrollo:   cd frontend  ^&^&  npm run dev
echo   Pruebas:      cd frontend  ^&^&  npm test
echo ============================================================

:fin
echo.
pause
endlocal
