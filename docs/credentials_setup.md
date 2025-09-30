# ==========================================
# PASO A PASO: OBTENER CREDENTIALS.JSON
# ==========================================

## 🎯 Objetivo
Obtener el archivo `credentials.json` necesario para autenticación OAuth 2.0 con Gmail API.

## 🚀 Guía Completa - Google Cloud Console

### **Paso 1: Acceder a Google Cloud Console**

1. **Abrir navegador** y ir a: https://console.cloud.google.com/
2. **Iniciar sesión** con tu cuenta de Google (puede ser la misma `jpmarichal@train.missionary.org`)
3. **Seleccionar proyecto** o crear uno nuevo:
   - Si es primera vez: "Crear proyecto"
   - Nombre sugerido: "CCM Email Service" o "CCM Project"

### **Paso 2: Habilitar Gmail API**

1. **Ir a "APIs y Servicios"** en el menú lateral
2. **Hacer clic en "Habilitar APIs y servicios"**
3. **Buscar "Gmail API"**
4. **Seleccionar "Gmail API"**
5. **Hacer clic en "Habilitar"**

```txt
✅ Gmail API habilitada correctamente
```

### **Paso 3: Crear Credenciales OAuth 2.0**

1. **Ir a "Credenciales"** en el menú lateral
2. **Hacer clic en "Crear credenciales"**
3. **Seleccionar "ID de cliente OAuth"**
4. **Configurar OAuth consent screen** (primera vez):

   **Pantalla de consentimiento OAuth:**
   - **Tipo de usuario**: "Externo" (recomendado)
   - **Nombre de la aplicación**: "CCM Email Service"
   - **Email de soporte**: Tu email
   - **Dominios autorizados**: Agregar dominios si es necesario
   - **Alcance**: Dejar por defecto
   - **Usuarios de prueba**: Agregar tu email si es "Externo"

5. **Crear credenciales OAuth**:
   - **Tipo de aplicación**: "Aplicación de escritorio"
   - **Nombre**: "CCM Desktop App"
   - **No necesitas redirect URIs para aplicación de escritorio**

6. **Descargar JSON**:
   - Se descargará automáticamente `credentials.json`
   - **Guardar en lugar seguro**

### **Paso 4: Configurar en el Proyecto**

```bash
# 1. Copiar credentials.json al directorio del proyecto
cp ~/Downloads/credentials.json ./credentials.json

# 2. Cambiar permisos (seguridad)
chmod 600 credentials.json

# 3. Verificar que existe
ls -la credentials.json
```

### **Paso 5: Configurar Variables de Entorno**

```bash
# Crear archivo .env (si no existe)
cp .env.example .env

# Editar .env con:
GMAIL_USER=jpmarichal@train.missionary.org
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
GOOGLE_TOKEN_PATH=/app/token.pickle
```

### **Paso 6: Primera Ejecución - OAuth Flow**

```bash
# Ejecutar aplicación (activará flow OAuth)
python -m uvicorn app.main:app --reload

# El navegador se abrirá automáticamente
# 1. Seleccionar cuenta Google
# 2. Autorizar permisos para Gmail
# 3. Se creará token.pickle automáticamente
```

## 📋 Verificación de Setup

### **Comprobar archivos creados:**

```bash
# Verificar estructura
ls -la
# Deberías ver:
# - credentials.json (archivo descargado)
# - token.pickle (se crea automáticamente después del flow)
# - .env (configurado)
```

### **Test de conexión:**

```bash
# Test endpoint de health
curl http://localhost:8000/health

# Debería mostrar:
{
  "status": "healthy",
  "service": "email-service",
  "version": "1.0.0"
}
```

## 🔧 Configuración Docker

### **Si usas Docker:**

```yaml
# docker-compose.yml
services:
  email-service:
    volumes:
      - ./credentials.json:/app/credentials.json:ro
      - ./token.pickle:/app/token.pickle
```

```bash
# Ejecutar con Docker
docker run -v $(pwd)/credentials.json:/app/credentials.json \
           -p 8000:8000 \
           email-service
```

## ⚠️ Troubleshooting

### **Error: "No se encontró archivo de credenciales"**
```bash
# Verificar que credentials.json existe
ls -la credentials.json

# Verificar ruta en .env
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS
```

### **Error: "Flow OAuth fallido"**
```bash
# Eliminar token corrupto e intentar de nuevo
rm -f token.pickle
python -m uvicorn app.main:app --reload
```

### **Error: "Insufficient Permission"**
```bash
# Verificar en Google Cloud Console:
# 1. Gmail API habilitada
# 2. OAuth consent screen configurado
# 3. Scopes incluyen Gmail
```

## 🔒 Seguridad Importante

### **Archivos a proteger:**
```bash
# Agregar a .gitignore
echo "credentials.json" >> .gitignore
echo "token.pickle" >> .gitignore
echo "*.env" >> .gitignore
```

### **Permisos correctos:**
```bash
# Solo el propietario puede leer
chmod 600 credentials.json token.pickle
```

## 📊 Scopes Solicitados

El sistema solicitará estos permisos:
- ✅ `https://www.googleapis.com/auth/gmail.readonly` - Leer correos
- ✅ `https://www.googleapis.com/auth/gmail.modify` - Marcar como leído
- ✅ `https://www.googleapis.com/auth/gmail.labels` - Gestionar etiquetas

## 🎯 Resultado Final

Después de completar estos pasos tendrás:

1. ✅ **Archivo credentials.json** válido
2. ✅ **Token OAuth** generado automáticamente
3. ✅ **Acceso completo a Gmail API**
4. ✅ **Sistema listo para procesar emails**

## 🚨 Notas Importantes

- **El archivo credentials.json es único** por aplicación OAuth
- **No compartir credentials.json** entre proyectos
- **El token.pickle se regenera** automáticamente cuando expira
- **Para producción**: Considerar usar Service Account en lugar de Desktop App

¿Necesitas ayuda con algún paso específico de esta configuración?
