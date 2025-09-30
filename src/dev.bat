@echo off
REM Script de desarrollo para CCM Email Service (Windows)
REM Uso: dev.bat [comando]

setlocal enabledelayedexpansion

if "%1"=="help" goto :help
if "%1"=="status" goto :status
if "%1"=="setup" goto :setup
if "%1"=="install" goto :install
if "%1"=="test" goto :test
if "%1"=="dev" goto :dev
if "%1"=="prod" goto :prod
if "%1"=="config" goto :config
if "%1"=="" goto :help

:help
echo Uso: dev.bat [COMANDO]
echo.
echo Comandos disponibles:
echo   status      Mostrar estado del proyecto
echo   setup       Configurar entorno completo
echo   install     Instalar dependencias
echo   test        Ejecutar tests
echo   dev         Ejecutar en modo desarrollo
echo   prod        Ejecutar en modo produccion
echo   config      Verificar configuracion
echo   help        Mostrar esta ayuda
echo.
echo Ejemplos:
echo   dev.bat setup    # Configurar todo el proyecto
echo   dev.bat dev      # Ejecutar en desarrollo
echo   dev.bat test     # Ejecutar tests
goto :end

:status
echo === ESTADO DEL PROYECTO CCM EMAIL SERVICE ===
echo.

echo 📁 Estructura de archivos:
if exist "app\main.py" (
    if exist "app\config.py" (
        if exist "app\services\email_service.py" (
            echo ✅ Archivos principales del proyecto
        ) else (
            echo ❌ Faltan archivos principales
        )
    ) else (
        echo ❌ Faltan archivos principales
    )
) else (
    echo ❌ Faltan archivos principales
)

echo.
echo 🐍 Python:
python --version >nul 2>&1
if errorlevel 1 (
    echo No instalado
) else (
    python --version
)

echo.
echo 🐳 Docker:
docker --version >nul 2>&1
if errorlevel 1 (
    echo No instalado
) else (
    docker --version
)

echo.
echo 📄 .env:
if exist "..\.env" (
    echo ✅ Archivo .env configurado
) else (
    echo ⚠️  Archivo .env no encontrado
)

echo.
echo 📊 Resumen:
echo 📂 Directorio actual: %cd%
goto :end

:setup
echo Configurando proyecto completo...
call :check_dependencies
call :check_config
echo ✅ Setup completado!
goto :end

:install
echo Instalando dependencias...
if exist "venv" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
) else (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
)
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error instalando dependencias
) else (
    echo ✅ Dependencias instaladas
)
goto :end

:test
echo Ejecutando tests...
call :activate_venv
python -m pytest tests/ -v --tb=short
goto :end

:dev
echo Iniciando aplicación en modo desarrollo...
call :activate_venv
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
goto :end

:prod
echo Iniciando aplicación en modo producción...
call :activate_venv
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
goto :end

:config
echo Verificando configuración...
if not exist "..\.env" (
    echo ❌ No se encontró archivo .env
    echo Copiar .env.example a .env y configurar las credenciales:
    echo copy ..\env.example ..\.env
    goto :end
) else (
    echo ✅ Archivo .env encontrado
)

findstr "tu-email@gmail.com" ..\env >nul
if errorlevel 1 (
    echo ✅ Variables de entorno configuradas
) else (
    echo ⚠️  Variables de entorno no configuradas
    echo Editar ..\.env con las credenciales reales
)
goto :end

:check_dependencies
echo Verificando dependencias...
python -c "import fastapi, uvicorn, pydantic, imapclient, structlog" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Faltan algunas dependencias. Instalando...
    call :install
) else (
    echo ✅ Todas las dependencias están instaladas
)
goto :end

:activate_venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Instalando dependencias...
    pip install -r requirements.txt
)
goto :end

:end
