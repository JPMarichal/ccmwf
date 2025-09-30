#!/bin/bash
# Script de desarrollo para CCM Email Service
# Uso: ./dev.sh [comando]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar si estamos en el directorio correcto
if [ ! -f "requirements.txt" ] || [ ! -d "app" ]; then
    error "No se encontró la estructura del proyecto. Ejecutar desde el directorio src/"
    exit 1
fi

# Función para activar entorno virtual
activate_venv() {
    if [ -d "venv" ]; then
        log "Activando entorno virtual..."
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
    else
        warning "No se encontró entorno virtual. Creando uno..."
        python -m venv venv
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
        log "Instalando dependencias..."
        pip install -r requirements.txt
    fi
}

# Función para verificar dependencias
check_dependencies() {
    log "Verificando dependencias..."
    python -c "import fastapi, uvicorn, pydantic, imapclient, structlog" 2>/dev/null
    if [ $? -eq 0 ]; then
        success "Todas las dependencias están instaladas"
    else
        warning "Faltan algunas dependencias. Instalando..."
        activate_venv
        pip install -r requirements.txt
    fi
}

# Función para ejecutar tests
run_tests() {
    log "Ejecutando tests..."
    activate_venv
    python -m pytest tests/ -v --tb=short
}

# Función para ejecutar aplicación en modo desarrollo
run_dev() {
    log "Iniciando aplicación en modo desarrollo..."
    activate_venv
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Función para ejecutar aplicación en modo producción
run_prod() {
    log "Iniciando aplicación en modo producción..."
    activate_venv
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
}

# Función para verificar configuración
check_config() {
    log "Verificando configuración..."

    # Verificar archivo .env
    if [ ! -f "../.env" ]; then
        error "No se encontró archivo .env"
        echo "Copiar .env.example a .env y configurar las credenciales:"
        echo "cp ../.env.example ../.env"
        return 1
    else
        success "Archivo .env encontrado"
    fi

    # Verificar variables críticas
    if grep -q "tu-email@gmail.com" ../.env; then
        warning "Variables de entorno no configuradas"
        echo "Editar ../.env con las credenciales reales"
    else
        success "Variables de entorno configuradas"
    fi
}

# Función para mostrar estado del proyecto
show_status() {
    echo -e "${BLUE}=== ESTADO DEL PROYECTO CCM EMAIL SERVICE ===${NC}"
    echo ""

    # Verificar estructura de archivos
    echo -e "${BLUE}📁 Estructura de archivos:${NC}"
    if [ -f "app/main.py" ] && [ -f "app/config.py" ] && [ -f "app/services/email_service.py" ]; then
        success "✅ Archivos principales del proyecto"
    else
        error "❌ Faltan archivos principales"
    fi

    # Verificar dependencias
    if python -c "import fastapi" 2>/dev/null; then
        success "✅ Dependencias de Python instaladas"
    else
        warning "⚠️  Dependencias de Python no instaladas"
    fi

    # Verificar Docker
    if command -v docker &> /dev/null; then
        success "✅ Docker instalado"
    else
        warning "⚠️  Docker no instalado"
    fi

    # Verificar .env
    if [ -f "../.env" ]; then
        success "✅ Archivo .env configurado"
    else
        warning "⚠️  Archivo .env no encontrado"
    fi

    echo ""
    echo -e "${BLUE}📊 Resumen:${NC}"
    echo "📂 Directorio actual: $(pwd)"
    echo "🐍 Python: $(python --version 2>/dev/null || echo 'No instalado')"
    echo "🐳 Docker: $(docker --version 2>/dev/null | cut -d' ' -f3 || echo 'No instalado')"
}

# Menú de ayuda
show_help() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponibles:"
    echo "  status      Mostrar estado del proyecto"
    echo "  setup       Configurar entorno completo"
    echo "  install     Instalar dependencias"
    echo "  test        Ejecutar tests"
    echo "  dev         Ejecutar en modo desarrollo"
    echo "  prod        Ejecutar en modo producción"
    echo "  config      Verificar configuración"
    echo "  help        Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 setup    # Configurar todo el proyecto"
    echo "  $0 dev      # Ejecutar en desarrollo"
    echo "  $0 test     # Ejecutar tests"
}

# Procesar argumentos
case "${1:-help}" in
    "status")
        show_status
        ;;
    "setup")
        log "Configurando proyecto completo..."
        check_dependencies
        check_config
        success "Setup completado!"
        ;;
    "install")
        activate_venv
        pip install -r requirements.txt
        success "Dependencias instaladas"
        ;;
    "test")
        run_tests
        ;;
    "dev")
        run_dev
        ;;
    "prod")
        run_prod
        ;;
    "config")
        check_config
        ;;
    "help"|*)
        show_help
        ;;
esac
