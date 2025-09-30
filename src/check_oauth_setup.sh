#!/bin/bash
# Script de verificación de configuración OAuth
# Uso: ./check_oauth_setup.sh

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar si estamos en el directorio correcto
if [ ! -f "requirements.txt" ] || [ ! -d "app" ]; then
    error "Ejecutar desde el directorio src/"
    exit 1
fi

echo "=== VERIFICACIÓN DE CONFIGURACIÓN OAUTH ==="
echo ""

# 1. Verificar dependencias
log "Verificando dependencias de Google..."
python -c "
try:
    import google.auth
    import google.oauth2.credentials
    import googleapiclient.discovery
    print('✅ Dependencias de Google instaladas')
except ImportError as e:
    print('❌ Faltan dependencias:', str(e))
    exit(1)
"

# 2. Verificar archivo credentials.json
log "Verificando archivo credentials.json..."
if [ -f "credentials.json" ]; then
    success "Archivo credentials.json encontrado"

    # Verificar estructura JSON básica
    if python -c "import json; json.load(open('credentials.json')); print('✅ JSON válido')" 2>/dev/null; then
        success "Archivo credentials.json tiene formato válido"
    else
        error "Archivo credentials.json tiene formato inválido"
        exit 1
    fi
else
    error "No se encontró archivo credentials.json"
    echo ""
    echo "📋 Pasos para obtener credentials.json:"
    echo "1. Ir a https://console.cloud.google.com/"
    echo "2. Crear/enable Gmail API"
    echo "3. Crear OAuth 2.0 credentials"
    echo "4. Descargar credentials.json"
    echo ""
    echo "Ver guía completa: docs/credentials_setup.md"
    exit 1
fi

# 3. Verificar archivo .env
log "Verificando archivo .env..."
if [ -f "../.env" ]; then
    success "Archivo .env encontrado"

    # Verificar variables críticas
    if grep -q "jpmarichal@train.missionary.org" ../.env; then
        success "GMAIL_USER configurado correctamente"
    else
        warning "GMAIL_USER no está configurado o es incorrecto"
    fi

    if grep -q "GOOGLE_APPLICATION_CREDENTIALS" ../.env; then
        success "Variables OAuth configuradas"
    else
        warning "Variables OAuth no configuradas"
    fi
else
    warning "No se encontró archivo .env"
    echo "Ejecutar: cp ../.env.example ../.env"
fi

# 4. Verificar token.pickle
log "Verificando token de acceso..."
if [ -f "token.pickle" ]; then
    success "Token de acceso encontrado (OAuth completado)"

    # Verificar si el token es válido
    python -c "
import pickle
try:
    with open('token.pickle', 'rb') as f:
        creds = pickle.load(f)
        if creds.valid:
            print('✅ Token válido y activo')
        else:
            print('⚠️ Token expirado, se refrescará automáticamente')
except:
    print('❌ Token corrupto')
" 2>/dev/null || warning "No se pudo verificar token"
else
    warning "Token no encontrado - se creará en primera ejecución"
fi

# 5. Test de importación
log "Verificando importación de servicios..."
python -c "
try:
    from app.services.gmail_oauth_service import GmailOAuthService
    print('✅ GmailOAuthService importado correctamente')
except Exception as e:
    print('❌ Error importando GmailOAuthService:', str(e))
    exit(1)
"

# 6. Test básico de configuración
log "Verificando configuración de settings..."
python -c "
try:
    from app.config import Settings
    settings = Settings()
    print('✅ Configuración cargada correctamente')
    print('   Usuario:', settings.gmail_user)
    print('   Método:', 'OAuth' if settings.google_application_credentials else 'IMAP')
except Exception as e:
    print('❌ Error en configuración:', str(e))
    exit(1)
"

echo ""
echo "=== RESUMEN DE VERIFICACIÓN ==="
echo ""

if [ -f "credentials.json" ] && [ -f "../.env" ]; then
    success "🎉 Configuración OAuth lista!"
    echo ""
    echo "🚀 Próximos pasos:"
    echo "1. Ejecutar: python -m uvicorn app.main:app --reload"
    echo "2. Completar flow OAuth en el navegador"
    echo "3. Verificar funcionamiento: curl http://localhost:8000/health"
    echo ""
    echo "📚 Documentación completa: docs/oauth_setup_guide.md"
else
    error "❌ Configuración incompleta"
    echo ""
    echo "📋 Completar los pasos en: docs/credentials_setup.md"
fi
