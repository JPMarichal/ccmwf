# Plan de Trabajo - Containerización de la Aplicación CCM

## Objetivo General
Estabilizar la ejecución del servicio CCM mediante un entorno contenedorizado único que orqueste FastAPI/Uvicorn, Redis y la conexión a la base MySQL existente, garantizando paridad entre desarrollo local, QA y producción en el VPS.

## Alcance
- Empaquetar la aplicación Python en un contenedor (Dockerfile) con todas las dependencias (incluido `mysqlclient`, `redis`, `structlog`, etc.).
- Definir `docker-compose.yml` (o equivalente) que levante:
  - Servicio `ccm-api` (Uvicorn + aplicación).
  - Servicio `redis` local.
  - Configuración de red para conectarse a la base MySQL real ya provisionada (no se creará contenedor de MySQL).
- Integrar variables de entorno desde `.env` (sin exponer secretos) y volúmenes necesarios (logs, certificados, credenciales OAuth).
- Documentar el flujo de operación y pruebas dentro del entorno contenedorizado.

## Dependencias y Consideraciones
- **Base de datos**: la instancia MySQL remota debe ser accesible desde los contenedores (firewall, puertos, IP pública o túnel seguro).
- **Credenciales**: `.env` y archivos OAuth deberán montarse como volúmenes o gestionarse mediante secretos.
- **Logs**: mantener estructura de logs en español y formato JSON; evaluar rotación dentro del contenedor.
- **Pruebas**: pytest debe ejecutarse dentro del contenedor para validar endpoints `/telegram/*` con datos reales.
- **Observabilidad**: planificar salud del servicio (healthchecks de Uvicorn/Redis) para despliegue continuo.

## Plan Paso a Paso
1. **Auditoría de requisitos técnicos**  
   - Inventariar dependencias Python actuales (`poetry.lock`/`requirements.txt`).  
   - Confirmar conectividad desde redes de desarrollo al MySQL remoto (IP/puerto 3306).

2. **Diseño de arquitectura de contenedores**  
   - Especificar servicios en `docker-compose.yml`.  
   - Definir red interna (`backend`) y reglas de salida hacia MySQL externo.

3. **Construcción de Dockerfile de la aplicación**  
   - Base `python:3.13-slim` (o aprobada).  
   - Instalar dependencias del sistema (build-essential, libmysqlclient-dev).  
   - Copiar código bajo `/app`, instalar requirements mediante `pip`.  
   - Configurar usuario sin privilegios y directorios de logs.

4. **Orquestación con Docker Compose**  
   - Servicio `ccm-api` enlazado al Dockerfile.  
   - Servicio `redis` (imagen oficial).  
   - Montar `.env` y credenciales como volúmenes (modo `ro`).  
   - Declarar variables `CACHE_PROVIDER=redis`, `DATABASE_URL=mysql://...` y puertos publicados (`8000`).

5. **Configuración de Entrypoint y ejecución**  
   - Definir `entrypoint.sh` para aplicar migraciones futuras y lanzar `uvicorn --host 0.0.0.0 --port 8000 app.main:app`.  
   - Añadir `PYTHONPATH=/app/src` y rotación de logs (logrotate o supervisión).

6. **Healthchecks y monitoreo básico**  
   - Añadir healthcheck HTTP (`/health` o `/docs`) en `ccm-api`.  
   - Healthcheck de Redis basado en `redis-cli ping`.  
   - Registrar métricas mínimas (tiempo de arranque, latencias) en logs estructurados.

7. **Estrategia de secretos y credenciales**  
   - Definir cómo obtendrá el contenedor las credenciales OAuth (`GOOGLE_APPLICATION_CREDENTIALS`) y tokens.  
   - Documentar uso de volúmenes cifrados o variables en entorno seguro.

8. **Pruebas dentro del contenedor**  
   - Ejecutar `pytest` mediante `docker compose run ccm-api pytest`.  
   - Validar endpoints `/telegram/proximos-ingresos`, `/telegram/proximos-cumpleanos`, `/telegram/alerta` enviando mensajes reales.  
   - Documentar resultados y casos negativos (sin Redis, sin DB, etc.).

9. **Documentación y onboarding**  
   - Actualizar `docs/plan.md`, `docs/workflow.md` con flujo contenedorizado.  
   - Crear guía rápida (`docs/container_setup.md`) con comandos `docker compose up`, logs y troubleshooting.

10. **Despliegue en VPS**  
    - Publicar imágenes en registro (GitHub Container Registry u otro).  
    - Configurar VPS Ubuntu para ejecutar `docker compose` con los mismos archivos.  
    - Programar monitoreo (systemd, cron, watchtower) para mantener contenedores activos.  
    - Validar operación permanente (reinicios automáticos, restart policies).

11. **Cierre y seguimiento**  
    - Revisar checklists con símbolos ✅/⚠️/ℹ️.  
    - Registrar lecciones aprendidas y ajustar backlog para futuras automatizaciones (CI/CD, backups).

## Entregables Esperados
- `Dockerfile` y `docker-compose.yml` actualizados en `src/docker/`.  
- Script/entrypoint y configuraciones auxiliares para logs y healthchecks.  
- Documentación operativa actualizada con símbolos de estado.  
- Validación documentada de los endpoints de Telegram ejecutados dentro del contenedor contra la base MySQL real.

## Seguimiento Issue 30 (Dockerfile base)
- **✅ Dockerfile actualizado**: `src/docker/Dockerfile` ahora usa `python:3.13-slim`, instala `build-essential`, `default-libmysqlclient-dev`, `pkg-config`, `curl`, define `PYTHONPATH=/app/src` y copia el proyecto completo.
- **✅ Dependencias Python ajustadas**: `src/requirements.txt` incluye `redis==5.0.4` y `mysqlclient==2.2.7`.
- **✅ Build verificado**: `docker build -f src/docker/Dockerfile -t ccm-api:issue30 .` finaliza correctamente.
- **✅ Ejecución básica**: `docker run --rm --env-file .env -p 8000:8000 ccm-api:issue30` expone Swagger (`/docs`) sin errores.
- **ℹ️ Próximos pasos**: Issue 31 (docker-compose + redis), Issue 32 (entrypoint/healthchecks), Issue 33 (secretos) e Issue 34 (pruebas E2E).
