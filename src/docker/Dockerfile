# ==========================================
# CCM Email Service - Dockerfile
# ==========================================

FROM python:3.13-slim

# Configurar variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema requeridas por mysqlclient, healthchecks, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias desde la raíz del proyecto
COPY ../../src/requirements.txt /tmp/requirements.txt

# Instalar dependencias Python
RUN pip install --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt

# Crear estructura de aplicación
RUN mkdir -p /app/logs

# Copiar código fuente y recursos necesarios desde la raíz
COPY ../../ /app/

# Crear usuario no-root para seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Puerto expuesto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
