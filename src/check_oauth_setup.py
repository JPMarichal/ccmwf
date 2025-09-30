#!/usr/bin/env python3
"""
Script de verificación rápida de configuración OAuth
"""

import os
import json
import pickle
from pathlib import Path

def check_oauth_setup():
    """Verificar configuración OAuth completa"""
    print("=== VERIFICACIÓN DE CONFIGURACIÓN OAUTH ===")
    print()

    # 1. Verificar dependencias
    print("1. Verificando dependencias...")
    try:
        import google.auth
        import google.oauth2.credentials
        import googleapiclient.discovery
        print("   ✅ Dependencias de Google instaladas")
    except ImportError as e:
        print(f"   ❌ Faltan dependencias: {e}")
        return False

    # 2. Verificar credentials.json
    print("\n2. Verificando credentials.json...")
    if os.path.exists('credentials.json'):
        try:
            with open('credentials.json', 'r') as f:
                data = json.load(f)
            if 'client_id' in data and 'client_secret' in data:
                print("   ✅ credentials.json válido")
                print(f"   📧 Client ID: {data['client_id'][:20]}...")
            else:
                print("   ❌ credentials.json incompleto")
                return False
        except:
            print("   ❌ credentials.json corrupto")
            return False
    else:
        print("   ❌ No se encontró credentials.json")
        return False

    # 3. Verificar .env
    print("\n3. Verificando .env...")
    env_path = Path('../.env')
    if env_path.exists():
        print("   ✅ Archivo .env encontrado")
        content = env_path.read_text()
        if 'jpmarichal@train.missionary.org' in content:
            print("   ✅ GMAIL_USER configurado")
        else:
            print("   ⚠️  GMAIL_USER no configurado correctamente")

        if 'GOOGLE_APPLICATION_CREDENTIALS' in content:
            print("   ✅ Variables OAuth configuradas")
        else:
            print("   ⚠️  Variables OAuth no configuradas")
    else:
        print("   ⚠️  No se encontró .env")
        print("   💡 Copiar .env.example a .env")

    # 4. Verificar token.pickle
    print("\n4. Verificando token.pickle...")
    if os.path.exists('token.pickle'):
        try:
            with open('token.pickle', 'rb') as f:
                creds = pickle.load(f)
            if hasattr(creds, 'valid') and creds.valid:
                print("   ✅ Token válido y activo")
            else:
                print("   ⚠️  Token expirado - se refrescará automáticamente")
        except:
            print("   ⚠️  Token corrupto - se recreará")
    else:
        print("   ⚠️  Token no encontrado - se creará en primera ejecución")

    # 5. Test de importación
    print("\n5. Verificando servicios...")
    try:
        from app.services.gmail_oauth_service import GmailOAuthService
        from app.config import Settings
        print("   ✅ Servicios importados correctamente")
    except Exception as e:
        print(f"   ❌ Error importando servicios: {e}")
        return False

    # 6. Test de configuración
    print("\n6. Verificando configuración...")
    try:
        settings = Settings()
        print("   ✅ Configuración cargada")
        print(f"   👤 Usuario: {settings.gmail_user}")
        print(f"   🔧 Método: {'OAuth' if settings.google_application_credentials else 'IMAP'}")
    except Exception as e:
        print(f"   ❌ Error en configuración: {e}")
        return False

    print("\n=== RESULTADO ===")
    return True

if __name__ == "__main__":
    success = check_oauth_setup()
    if success:
        print("\n🎉 ¡Configuración OAuth lista!")
        print("\n🚀 Próximos pasos:")
        print("1. Ejecutar: python -m uvicorn app.main:app --reload")
        print("2. Completar flow OAuth en el navegador")
        print("3. Verificar: curl http://localhost:8000/health")
    else:
        print("\n❌ Configuración incompleta")
        print("\n📋 Revisar los errores anteriores")
        print("📚 Guía completa: docs/credentials_setup.md")
