# Environment Variables Guide

Este documento describe las variables de entorno utilizadas por el servicio **CCM Email Service**. Todas las variables se leen desde el archivo `.env` ubicado en la raíz del proyecto (`d:/myapps/ccmwf/.env`).

## Variables Principales

| Variable | Obligatoria | Descripción | Ejemplo |
|----------|-------------|-------------|---------|
| `GMAIL_USER` | ✅ | Cuenta de Gmail que será monitoreada | `misioneros.ccm@gmail.com` |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ (para OAuth) | Ruta absoluta al archivo `credentials.json` descargado de Google Cloud Console | `d:/myapps/ccmwf/src/credentials.json` |
| `GOOGLE_TOKEN_PATH` | ✅ (para OAuth) | Ruta absoluta a `token.pickle` (se crea automáticamente tras completar el flow OAuth) | `d:/myapps/ccmwf/src/token.pickle` |
| `GMAIL_APP_PASSWORD` | Opcional (fallback IMAP) | App Password usado cuando no se dispone de OAuth | `abcd-efgh-ijkl-mnop` |
| `EMAIL_SUBJECT_PATTERN` | ✅ | Patrón de asunto para identificar correos relevantes | `Misioneros que llegan` |
| `PROCESSED_LABEL` | Opcional | Etiqueta de Gmail para marcar correos procesados | `misioneros-procesados` |
| `APP_ENV` | ✅ | Entorno de ejecución (`development`, `staging`, `production`) | `development` |
| `LOG_LEVEL` | ✅ | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `INFO` |
| `LOG_FILE_PATH` | Opcional | Ruta absoluta del archivo de logs. Por defecto `logs/email_service.log` | `d:/myapps/ccmwf/logs/email_service.log` |
| `API_HOST` | Opcional | Host donde escucha FastAPI | `0.0.0.0` |
| `API_PORT` | Opcional | Puerto de FastAPI | `8000` |

## Rutas de Credenciales

- Coloca `credentials.json` (OAuth) en `d:/myapps/ccmwf/src/credentials.json`.
- El flow OAuth generará automáticamente `token.pickle` en la ruta definida por `GOOGLE_TOKEN_PATH`.

Ambos archivos **no deben commitearse**; están listados en `.gitignore`.

## Variables para Fases Futuras

| Variable | Descripción |
|----------|-------------|
| `GOOGLE_DRIVE_CREDENTIALS_PATH` | Ruta a credenciales para integración con Google Drive |
| `GOOGLE_DRIVE_TOKEN_PATH` | Ruta al token de Google Drive |
| `DATABASE_URL` | Cadena de conexión a MySQL |
| `TELEGRAM_ENABLED` | Activa o desactiva por completo el servicio de notificaciones Telegram |
| `TELEGRAM_BOT_TOKEN` | Token del bot generado por @BotFather |
| `TELEGRAM_CHAT_ID` | Chat o canal destino (números negativos para canales) |
| `TELEGRAM_TIMEOUT_SECONDS` | Tiempo máximo de espera de la petición HTTP a Telegram |
| `SECRET_KEY` / `ENCRYPTION_KEY` | Claves para futuras características de seguridad |

Estas variables pueden permanecer vacías hasta que se aborden las fases correspondientes.

## Buenas Prácticas

- Mantén `.env` fuera del control de versiones y usa `.env.example` como plantilla.
- Crea un `.env` por entorno (desarrollo, staging, producción).
- Para Windows puedes usar rutas con barras normales (`d:/ruta/archivo`) o dobles barras invertidas (`d:\ruta\archivo`).
- Documenta cualquier cambio en este archivo para el resto del equipo.
