@echo off
REM Script de verificación de configuración OAuth (Windows)
REM Uso: check_oauth_setup.bat

setlocal enabledelayedexpansion

echo === VERIFICACION DE CONFIGURACION OAUTH ===
echo.

REM Verificar si estamos en el directorio correcto
if not exist "requirements.txt" (
    echo ❌ Ejecutar desde el directorio src/
    goto :end
)
if not exist "app" (
    echo ❌ Ejecutar desde el directorio src/
    goto :end
)

echo Verificando dependencias de Google...
python -c "
try:
    import google.auth
    import google.oauth2.credentials
    import googleapiclient.discovery
    print('✅ Dependencias de Google instaladas')
except ImportError as e:
    print('❌ Faltan dependencias:', str(e))
    exit(1)
" 2>nul
if errorlevel 1 goto :end

echo.
echo Verificando archivo credentials.json...
if exist "credentials.json" (
    echo ✅ Archivo credentials.json encontrado

    REM Verificar estructura JSON básica
    python -c "import json; json.load(open('credentials.json')); print('✅ JSON valido')" 2>nul
    if errorlevel 1 (
        echo ❌ Archivo credentials.json tiene formato invalido
    ) else (
        echo ✅ Archivo credentials.json tiene formato valido
    )
) else (
    echo ❌ No se encontro archivo credentials.json
    echo.
    echo 📋 Pasos para obtener credentials.json:
    echo 1. Ir a https://console.cloud.google.com/
    echo 2. Crear/enable Gmail API
    echo 3. Crear OAuth 2.0 credentials
    echo 4. Descargar credentials.json
    echo.
    echo Ver guia completa: docs\credentials_setup.md
    goto :end
)

echo.
echo Verificando archivo .env...
if exist "..\.env" (
    echo ✅ Archivo .env encontrado

    REM Verificar variables críticas
    findstr "jpmarichal@train.missionary.org" ..\env >nul
    if errorlevel 1 (
        echo ⚠️  GMAIL_USER no esta configurado o es incorrecto
    ) else (
        echo ✅ GMAIL_USER configurado correctamente
    )

    findstr "GOOGLE_APPLICATION_CREDENTIALS" ..\env >nul
    if errorlevel 1 (
        echo ⚠️  Variables OAuth no configuradas
    ) else (
        echo ✅ Variables OAuth configuradas
    )
) else (
    echo ⚠️  No se encontro archivo .env
    echo Ejecutar: copy ..\env.example ..\.env
)

echo.
echo Verificando token de acceso...
if exist "token.pickle" (
    echo ✅ Token de acceso encontrado (OAuth completado)

    REM Verificar si el token es válido
    python -c "
import pickle
try:
    with open('token.pickle', 'rb') as f:
        creds = pickle.load(f)
        if creds.valid:
            print('✅ Token valido y activo')
        else:
            print('⚠️ Token expirado, se refrescará automaticamente')
except:
    print('❌ Token corrupto')
" 2>nul
) else (
    echo ⚠️  Token no encontrado - se creara en primera ejecucion
)

echo.
echo Verificando importacion de servicios...
python -c "
try:
    from app.services.gmail_oauth_service import GmailOAuthService
    print('✅ GmailOAuthService importado correctamente')
except Exception as e:
    print('❌ Error importando GmailOAuthService:', str(e))
" 2>nul
if errorlevel 1 goto :end

echo.
echo Verificando configuracion de settings...
python -c "
try:
    from app.config import Settings
    settings = Settings()
    print('✅ Configuracion cargada correctamente')
    print('   Usuario:', settings.gmail_user)
    print('   Metodo:', 'OAuth' if settings.google_application_credentials else 'IMAP')
except Exception as e:
    print('❌ Error en configuracion:', str(e))
" 2>nul
if errorlevel 1 goto :end

echo.
echo === RESUMEN DE VERIFICACION ===
echo.

if exist "credentials.json" if exist "..\.env" (
    echo ✅ 🎉 Configuracion OAuth lista!
    echo.
    echo 🚀 Proximos pasos:
    echo 1. Ejecutar: python -m uvicorn app.main:app --reload
    echo 2. Completar flow OAuth en el navegador
    echo 3. Verificar funcionamiento: curl http://localhost:8000/health
    echo.
    echo 📚 Documentacion completa: docs\oauth_setup_guide.md
) else (
    echo ❌ Configuracion incompleta
    echo.
    echo 📋 Completar los pasos en: docs\credentials_setup.md
)

:end
