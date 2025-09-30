# Plan de Trabajo Fase 2 - Procesamiento Inicial del Email

## Objetivo General
Procesar el contenido del correo recibido desde Gmail, validando su estructura y extrayendo datos relevantes (texto, tabla HTML, adjuntos) para preparar la información rumbo a las siguientes fases (organización en Drive, persistencia y reporteo).

## Alcance
- Parsing completo del contenido HTML del correo.
- Normalización y validación de los datos extraídos.
- Manejo robusto de errores de estructura y contenido.
- Generación de artefactos (logs, reportes internos) que permitan auditar el procesamiento.

## Dependencias
- Servicio de correo funcional (Fase 1 completada).
- Credenciales OAuth/IMAP configuradas y validadas.
- Modelo `ProcessingResult` en `app/models.py` (se reutiliza para registrar detalles del procesamiento).
- Documentación y guías actualizadas (`docs/development_guide.md`, `docs/api_documentation.md`).

## Entregables
- Funcionalidad para extraer y estructurar tabla HTML desde el cuerpo del correo.
- Validación de datos (existencia de filas, columnas requeridas, tipos esperados).
- Manejo de errores y registro detallado (logs + `ProcessingResult.details`).
- Tests unitarios y de integración que cubran los nuevos flujos.
- Actualización de documentación (`docs/plan_fase2.md`, `docs/plan_fase1.md`, guías técnicas).

## Plan Semanal

### Semana 5 – Análisis y Diseño
- **Día 1-2**
  - **Revisión de contenido HTML** de correos reales (ejemplos de la hermana Natalia) para identificar estructura de la tabla.
  - **Definir esquema de datos** esperado (columnas, nombres, formatos).
- **Día 3-4**
  - **Diseñar parser** (utilidades en `EmailService` o módulo dedicado) para convertir HTML a objetos Python (lista de dicts).
  - **Plan de validación**: reglas de negocio (campos obligatorios, tipos, normalización de texto).
- **Día 5**
  - **Plan de pruebas**: Fixtures de correos con versiones correctas y variantes con errores.

### Semana 6 – Implementación
- **Día 6-7**
  - Implementar helpers de parsing (`beautifulsoup4` u otra librería) y normalización.
  - Integrar el parser al flujo `process_incoming_emails()` (OAuth/IMAP) para que los resultados se agreguen al `ProcessingResult`.
- **Día 8**
  - Añadir **validaciones y manejo de errores**: códigos específicos (`table_missing`, `column_missing`, `value_invalid`).
  - Incluir métricas/resumen en logs.
- **Día 9**
  - **Tests unitarios** para validaciones y parsing (casos normales y edge cases).
  - **Tests de integración** comprobando que `/process-emails` refleja los datos estructurados y errores cuando aparecen.

### Semana 7 – Optimización y Documentación
- **Día 10**
  - Revisar performance (tiempos de parsing, manejo de grandes tablas).
  - Ajustar logging y mensajes de error.
- **Día 11**
  - Actualizar documentación (`docs/api_documentation.md`, `docs/development_guide.md`, `docs/plan_fase1.md`).
- **Día 12**
  - Retroalimentación y preparación para la Fase 3 (organización en Google Drive): definir qué datos del parsing serán insumo directo.

## Riesgos y Mitigaciones
- **Variaciones en la estructura HTML**: mantener parser tolerante y agregar reglas configurables.
- **Datos incompletos**: reportar errores específicos para trabajar con el equipo remitente.
- **Dependencias de librerías**: asegurar `beautifulsoup4` u otra librería en `requirements.txt`.

## Métricas de Éxito
- Parsing exitoso de ≥95% de correos válidos.
- Reporte de errores detallados para casos restantes.
- Tests (>85% coverage en módulos de parsing/validación).
- Documentación lista para el siguiente equipo (Drive / DB).
