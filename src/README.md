# CCM Email Service - Fase 1

Servicio para recepción y procesamiento automático de correos electrónicos con información de misioneros del Centro de Capacitación Misional México (CCM).

## 📋 Descripción

Este microservicio reemplaza la funcionalidad de Google Apps Script con una solución basada en contenedores que:

- ✅ Se conecta a Gmail via IMAP
- ✅ Busca correos con asunto "Misioneros que llegan"
- ✅ Extrae fecha de generación del cuerpo del correo
- ✅ Descarga y procesa archivos adjuntos
- ✅ Marca correos como procesados
- ✅ Proporciona API REST para integración

## 🚀 Inicio Rápido

### 1. Configuración de Entorno

```bash
# Clonar el proyecto
git clone <repository-url>
cd src

# Configurar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

```bash
# Copiar plantilla
cp ../.env.example .env

# Editar .env con tus credenciales:
# GMAIL_USER=tu-email@gmail.com
# GMAIL_APP_PASSWORD=tu-app-password-generado
```

### 3. Ejecutar la Aplicación

```bash
# Desarrollo
uvicorn app.main:app --reload

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Visitar: http://localhost:8000/docs
```

### 4. Docker (Recomendado)

```bash
# Construir e iniciar
docker-compose up --build

# Solo ejecutar
docker-compose up
```

## 📚 API Endpoints

### Health Check
```http
GET /health
```

### Procesar Emails
```http
POST /process-emails
```

### Buscar Emails (Testing)
```http
GET /emails/search?query=SUBJECT "Misioneros que llegan"
```

## 🔧 Configuración

### Variables de Entorno Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `GMAIL_USER` | Email de Gmail | `tu-email@gmail.com` |
| `GMAIL_APP_PASSWORD` | App Password de Gmail | `abcd-efgh-ijkl-mnop` |
| `EMAIL_SUBJECT_PATTERN` | Patrón de búsqueda | `Misioneros que llegan` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |

### Generar App Password de Gmail

1. Ir a [Google Account](https://myaccount.google.com/)
2. **Seguridad** → **Verificación en dos pasos** → **App passwords**
3. Generar contraseña para "Correo" → "Otro"

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │───▶│  Email Service   │───▶│   Gmail IMAP    │
│                 │    │                  │    │                 │
│ - /health       │    │ - Conexión IMAP  │    │ - Búsqueda      │
│ - /process      │    │ - Procesamiento  │    │ - Descarga      │
│ - /search       │    │ - Logging        │    │ - Parsing       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Tests con coverage
pytest tests/ --cov=app --cov-report=html
```

## 📝 Logging

Los logs se generan en formato estructurado JSON en:
- **Consola**: Durante desarrollo
- **Archivo**: `/app/logs/email_service.log` (rotativo)

Ejemplo de log:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.services.email_service",
  "message": "✅ Mensaje procesado correctamente",
  "subject": "Misioneros que llegan el 15 de enero",
  "attachments": 3
}
```

## 🔒 Seguridad

- ✅ **App Passwords** para Gmail (más seguros que contraseñas regulares)
- ✅ **Variables de entorno** para configuración sensible
- ✅ **Validación de entrada** en todos los endpoints
- ✅ **Logging seguro** (sin credenciales en logs)

## 🚀 Deploy

### Docker Compose (Desarrollo)
```bash
docker-compose up -d
```

### Variables de Producción
```bash
APP_ENV=production
LOG_LEVEL=WARNING
DEBUG=False
```

## 🔍 Debugging

### Comandos útiles:

```bash
# Ver logs en tiempo real
docker-compose logs -f email-service

# Ver logs de un contenedor específico
docker logs src

# Ejecutar comando dentro del contenedor
docker exec -it src bash

# Ver variables de entorno
docker exec src env | grep GMAIL
```

### Troubleshooting común:

1. **Error de conexión IMAP**:
   - Verificar `GMAIL_APP_PASSWORD`
   - Asegurar que "Acceso de aplicaciones menos seguras" esté habilitado temporalmente

2. **No encuentra correos**:
   - Verificar `EMAIL_SUBJECT_PATTERN`
   - Revisar que los correos no estén marcados como leídos

3. **Error de permisos**:
   - Verificar que el contenedor tenga acceso a la red
   - Revisar configuración de firewall

## 📊 Métricas y Monitoreo

El servicio incluye métricas básicas:
- Número de correos procesados
- Tasa de errores
- Tiempo de procesamiento
- Estado de conexión IMAP

Para monitoreo avanzado, integrar con Prometheus/Grafana.

## 🤝 Contribución

1. Fork el proyecto
2. Crear rama para feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Add nueva funcionalidad'`
4. Push rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📄 Licencia

Este proyecto es parte del sistema CCM y está bajo licencia interna.

---

**Versión**: 1.0.0
**Estado**: 🚧 En desarrollo - Fase 1
**Siguiente fase**: Integración con Google Drive Service
