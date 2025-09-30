#!/bin/bash
# Script de setup inicial para OAuth
# Uso: ./setup_oauth.sh

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[SETUP] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar directorio
if [ ! -f "requirements.txt" ]; then
    echo "❌ Ejecutar desde el directorio src/"
    exit 1
fi

log "Iniciando setup de OAuth..."

# 1. Copiar .env si no existe
if [ ! -f "../.env" ]; then
    log "Copiando plantilla .env..."
    cp ../.env.example ../.env
    success "Archivo .env creado"
else
    success "Archivo .env ya existe"
fi

# 2. Verificar si ya tenemos credentials.json
if [ ! -f "credentials.json" ]; then
    warning "No se encontró credentials.json"
    echo ""
    echo "📋 Siguientes pasos para obtener credentials.json:"
    echo ""
    echo "1. 🌐 Ir a: https://console.cloud.google.com/"
    echo "2. 🔑 Iniciar sesión con tu cuenta Google"
    echo "3. 📁 Crear proyecto: 'CCM Email Service'"
    echo "4. ⚙️  Habilitar Gmail API:"
    echo "   - APIs y Servicios > Biblioteca"
    echo "   - Buscar 'Gmail API' > Habilitar"
    echo "5. 🔐 Crear credenciales OAuth:"
    echo "   - Credenciales > Crear credenciales > ID de cliente OAuth"
    echo "   - Tipo: Aplicación de escritorio"
    echo "   - Descargar credentials.json"
    echo "6. 📄 Copiar credentials.json aquí"
    echo ""
    echo "📚 Guía detallada: docs/credentials_setup.md"
    echo ""
    echo "💡 Una vez que tengas credentials.json, ejecuta:"
    echo "   ./check_oauth_setup.sh"
else
    success "credentials.json encontrado"

    # 3. Verificar dependencias
    log "Verificando dependencias..."
    python -c "
import google.auth
import google.oauth2.credentials
import googleapiclient.discovery
print('✅ Dependencias OAuth instaladas')
" 2>/dev/null || {
        warning "Instalando dependencias OAuth..."
        pip install google-api-python-client google-auth google-auth-oauthlib
    }

    success "Setup OAuth completado!"
    echo ""
    echo "🚀 Listo para ejecutar:"
    echo "   python -m uvicorn app.main:app --reload"
    echo ""
    echo "🔍 Verificar setup: ./check_oauth_setup.sh"
fi
