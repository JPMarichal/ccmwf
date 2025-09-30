# Plan de Trabajo - Fase 1: Recepción de Email

## 🎯 Objetivo de la Fase
Implementar el sistema de recepción y monitoreo de correos electrónicos con información de misioneros, reemplazando la funcionalidad de Google Apps Script con una solución basada en contenedores y microservicios.

## 📋 Alcance de la Fase
- ✅ Configuración del entorno de desarrollo
- ✅ Instalación de dependencias base
- ✅ Implementación de conexión IMAP a Gmail
- ✅ Búsqueda y filtrado de correos específicos
- ✅ Extracción básica de información de correos
- ✅ Sistema de logging estructurado
- ✅ Configuración de variables de entorno
- ✅ Tests unitarios básicos

## 🏗️ Arquitectura de la Fase

```mermaid
graph TB
    A[Email Service] --> B[Gmail IMAP]
    A --> C[Local Storage]
    A --> D[Logging Service]
    A --> E[Configuration Service]

    B --> F[Email Reception]
    C --> G[Temporary Files]
    D --> H[Structured Logs]
    E --> I[Environment Variables]
```

## 📅 Plan de Trabajo Detallado

### **SEMANA 1: Setup y Configuración Base**

#### **Día 1: Entorno de Desarrollo**
- [ ] **Instalar Python 3.11+**
  - Verificar instalación: `python --version`
  - Configurar virtual environment: `python -m venv venv`

- [ ] **Instalar Docker y Docker Compose**
  - Docker Desktop para desarrollo local
  - Verificar instalación: `docker --version`

- [ ] **Configurar IDE (VS Code recomendado)**
  - Instalar extensiones: Python, Docker, Git
  - Configurar workspace settings

#### **Día 2: Estructura del Proyecto**
- [ ] **Crear estructura de directorios**:
  ```
  src/
  ├── app/
  │   ├── main.py
  │   ├── config.py
  │   ├── models.py
  │   └── services/
  │       └── email_service.py
  ├── tests/
  ├── docker/
  │   ├── Dockerfile
  │   └── docker-compose.yml
  ├── .env
  ├── requirements.txt
  └── README.md
  ```

- [ ] **Inicializar proyecto**:
  - `git init`
  - Crear `.gitignore`
  - Documentar estructura en README.md

#### **Día 3: Dependencias Base**
- [ ] **Crear requirements.txt**:
  ```txt
  fastapi==0.104.1
  uvicorn==0.24.0
  pydantic==2.5.0
  python-dotenv==1.0.0
  imapclient==2.3.0
  python-decouple==3.8
  structlog==23.2.0
  pytest==7.4.3
  pytest-asyncio==0.21.1
  httpx==0.25.2
  ```

- [x] **Instalar dependencias**:
  - `pip install -r requirements.txt`

### **SEMANA 2: Implementación Core**

#### **Día 4: Configuración de Variables de Entorno**
- [x] **Crear archivo .env** con todas las variables necesarias
- [x] **Implementar config.py** para cargar configuración
- [x] **Crear validación de variables requeridas**

#### **Día 5: Servicio de Email Base**
- [x] **Implementar EmailService class**:
  - Conexión IMAP a Gmail
  - Búsqueda de correos por asunto
  - Extracción de información básica
  - Manejo de errores robusto

- [x] **Crear modelos Pydantic**:
  ```python
  class EmailMessage(BaseModel):
      subject: str
      sender: str
      date: datetime
      body: str
      attachments: List[str]

  class ProcessingResult(BaseModel):
      success: bool
      processed: int
      errors: int
      details: List[dict]
  ```

#### **Día 6: API Endpoints**
- [x] **Crear FastAPI application**:
  ```python
  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "service": "email-service"}

  @app.post("/process-emails")
  async def process_emails():
      result = await email_service.process_incoming_emails()
      return result

  @app.get("/emails/search")
  async def search_emails(query: str = None):
      emails = await email_service.search_emails(query)
      return {"emails": emails}
  ```

### **SEMANA 3: Logging y Testing**

- [x] **Configurar structlog**:
  - Logging estructurado JSON
  - Diferentes niveles (DEBUG, INFO, ERROR)
  - Integración con configuración

- [x] **Implementar logging en todos los servicios**:
  - Logs de conexión IMAP
  - Logs de procesamiento de correos
  - Logs de errores con contexto

- [x] **Crear tests para EmailService**:
  ```python
  def test_imap_connection():
      # Test conexión sin credenciales reales

  def test_email_search():
      # Test búsqueda de correos

  def test_date_extraction():
      # Test extracción de fecha del cuerpo
  ```

- [x] **Crear tests para API endpoints**:
  ```python
  def test_health_endpoint():
      # Test endpoint de health

  def test_process_emails_endpoint():
      # Test endpoint de procesamiento
  ```

- [x] **Crear Dockerfile**:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [x] **Crear docker-compose.yml**:
  ```yaml
  version: '3.8'
  services:
    email-service:
      build: .
      ports:
        - "8000:8000"
      env_file:
        - .env
      volumes:
        - ./logs:/app/logs
  ```

### **SEMANA 4: Testing y Refinamiento**

#### **Día 10: Integration Testing**
- [x] **Crear tests de integración**:
  - Test completo de flujo de recepción
  - Test de manejo de errores
  - Test de logging end-to-end

#### **Día 11: Documentación**
- [x] **Documentar API con OpenAPI/Swagger**
- [x] **Crear guía de desarrollo**
- [x] **Documentar variables de entorno**

#### **Día 12: Review y Optimización**
- [ ] **Code review interno**
- [ ] **Optimización de performance**
- [ ] **Preparar para siguiente fase**
  - Cobertura actual: 68% (`pytest --cov=app`). Pendiente elevar >80% cubriendo ramas IMAP y errores adicionales.

## 🎯 Entregables de la Fase

### **Software Desarrollado**
- [x] **Email Service** completo y funcional
- [x] **API REST** para operaciones de email
- [x] **Sistema de logging** estructurado
- [ ] **Tests unitarios** con cobertura >80%
- [ ] **Documentación** de API y setup

### **Configuración e Infraestructura**
- [x] **Dockerfile** y docker-compose.yml
- [x] **Archivo .env** con todas las variables
- [x] **requirements.txt** completo
- [x] **Estructura de proyecto** escalable

### **Documentación**
- [x] **README.md** con instrucciones de setup
- [x] **API documentation** (Swagger)
- [x] **Guía de desarrollo** para siguiente fase

## ⚙️ Variables de Entorno (.env)

```env
# Gmail Configuration
GMAIL_USER=tu-email@gmail.com
GMAIL_APP_PASSWORD=tu-app-password
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993

# Search Configuration
EMAIL_SUBJECT_PATTERN=Misioneros que llegan
PROCESSED_LABEL=misioneros-procesados

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Google Drive Configuration (para siguiente fase)
GOOGLE_DRIVE_CREDENTIALS_PATH=/app/credentials.json
GOOGLE_DRIVE_TOKEN_PATH=/app/token.json

# Database Configuration (para siguiente fase)
DATABASE_URL=mysql://user:password@localhost:3306/ccm_db

# Security
SECRET_KEY=tu-secret-key-aqui
```

## 🔧 Comandos Útiles para Desarrollo

```bash
# Setup inicial
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

pip install -r requirements.txt

# Desarrollo
uvicorn app.main:app --reload

# Testing
pytest tests/ -v

# Docker
docker-compose up --build

# Logs
tail -f logs/email_service.log
```

## 📊 Métricas de Éxito

- ✅ **Conexión IMAP estable** durante 24h continuas
- ✅ **Procesamiento correcto** de correos de prueba
- ✅ **Logging estructurado** funcionando
- ✅ **Tests pasando** con cobertura >80%
- ✅ **API respondiendo** correctamente
- ✅ **Docker container** ejecutándose sin errores

## 🚨 Riesgos y Mitigación

| **Riesgo** | **Probabilidad** | **Impacto** | **Mitigación** |
|------------|------------------|-------------|----------------|
| Problemas de autenticación Gmail | Media | Alto | Usar app passwords, documentación clara |
| Límites de IMAP | Baja | Medio | Implementar retry logic y rate limiting |
| Errores de parsing de emails | Media | Alto | Testing exhaustivo con emails reales |
| Problemas de Docker | Baja | Medio | Documentación detallada de setup |

## 🔗 Dependencias con Otras Fases

- **Fase 2**: Recibirá emails procesados por esta fase
- **Fase 3**: Usará la estructura de archivos creada
- **Fase 4**: Se integrará con la base de datos
- **Fase 9**: Usará los logs generados

## 📝 Notas Importantes

1. **Seguridad**: Nunca commitear credenciales reales a Git
2. **Testing**: Usar emails de prueba para desarrollo
3. **Escalabilidad**: Diseñar para manejar múltiples correos simultáneos
4. **Monitoreo**: Preparar estructura para métricas futuras

---

*Este plan se actualizará semanalmente según el progreso real del proyecto.*
