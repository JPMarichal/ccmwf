@echo off
REM Script de setup inicial para OAuth (Windows)
REM Uso: setup_oauth.bat

setlocal enabledelayedexpansion

echo === SETUP INICIAL DE OAUTH ===
echo.

REM Verificar directorio
if not exist "requirements.txt" (
    echo ❌ Ejecutar desde el directorio src/
    goto :end
)

echo Iniciando setup de OAuth...

REM 1. Copiar .env si no existe
if not exist "..\.env" (
    echo Copiando plantilla .env...
    copy ..\env.example ..\.env
    echo ✅ Archivo .env creado
) else (
    echo ✅ Archivo .env ya existe
)

REM 2. Verificar si ya tenemos credentials.json
if not exist "credentials.json" (
    echo.
    echo ⚠️  No se encontro credentials.json
    echo.
    echo 📋 Siguientes pasos para obtener credentials.json:
    echo.
    echo 1. 🌐 Ir a: https://console.cloud.google.com/
    echo 2. 🔑 Iniciar sesion con tu cuenta Google
    echo 3. 📁 Crear proyecto: "CCM Email Service"
    echo 4. ⚙️  Habilitar Gmail API:
    echo    - APIs y Servicios ^> Biblioteca
    echo    - Buscar "Gmail API" ^> Habilitar
    echo 5. 🔐 Crear credenciales OAuth:
    echo    - Credenciales ^> Crear credenciales ^> ID de cliente OAuth
    echo    - Tipo: Aplicacion de escritorio
    echo    - Descargar credentials.json
    echo 6. 📄 Copiar credentials.json aqui
    echo.
    echo 📚 Guia detallada: docs\credentials_setup.md
    echo.
    echo 💡 Una vez que tengas credentials.json, ejecuta:
    echo    check_oauth_setup.bat
    goto :end
) else (
    echo ✅ credentials.json encontrado

    REM 3. Verificar dependencias
    echo.
    echo Verificando dependencias...
    python -c "
import google.auth
import google.oauth2.credentials
import googleapiclient.discovery
print('✅ Dependencias OAuth instaladas')
" 2>nul
    if errorlevel 1 (
        echo Instalando dependencias OAuth...
        pip install google-api-python-client google-auth google-auth-oauthlib
    ) else (
        echo ✅ Dependencias OAuth instaladas
    )

    echo.
    echo ✅ Setup OAuth completado!
    echo.
    echo 🚀 Listo para ejecutar:
    echo    python -m uvicorn app.main:app --reload
    echo.
    echo 🔍 Verificar setup: check_oauth_setup.bat
)

:end
