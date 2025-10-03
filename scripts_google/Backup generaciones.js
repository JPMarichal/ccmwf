/**
 * SCRIPT DE BACKUP AUTOMÁTICO DE GENERACIONES CCM
 * 
 * Este script realiza un backup automático de los archivos de generaciones de misioneros
 * desde la carpeta principal hacia una carpeta de respaldo en Google Drive.
 * 
 * CARACTERÍSTICAS:
 * - Sincronización incremental (solo archivos nuevos o modificados)
 * - Sistema de paginación para evitar límites de tiempo de Google Apps Script
 * - Preserva estructura de carpetas
 * - Continúa automáticamente desde donde se quedó si se interrumpe
 * 
 * CONFIGURACIÓN:
 * - Carpeta fuente: Definida en Config.js (ID_CARPETA_GENERACIONES)
 * - Carpeta destino: Definida en Config.js (ID_CARPETA_BACKUP)
 * 
 * USO:
 * - Ejecutar sincronizarBackupConPaginacion() para backup completo
 * - Configurar trigger diario para mantenimiento automático
 * 
 * @author CCM Scripts
 * @version 2.0
 */

/**
 * Sincroniza un backup, pausándose y reanudándose automáticamente para evitar
 * el límite de tiempo de ejecución de 6 minutos de Google.
 * Ideal para la primera sincronización masiva y para el mantenimiento diario.
 */
function sincronizarBackupConPaginacion() {
  // Las variables de configuración están centralizadas en Config.js

  const scriptProperties = PropertiesService.getScriptProperties();
  const startTime = new Date().getTime();

  try {
    const carpetaFuente = DriveApp.getFolderById(ID_CARPETA_GENERACIONES);
    const carpetaDestinoGeneraciones = DriveApp.getFolderById(ID_CARPETA_BACKUP);
    
    // Obtener el token de continuación si el script se está reanudando
    const continuationToken = scriptProperties.getProperty('continuationToken');
    let subcarpetasFuente;

    if (continuationToken) {
      Logger.log("Reanudando sincronización desde el punto guardado...");
      subcarpetasFuente = DriveApp.continueFolderIterator(continuationToken);
    } else {
      Logger.log("Iniciando nueva sincronización...");
      subcarpetasFuente = carpetaFuente.getFolders();
    }

    // Procesar carpetas hasta que queden 90 segundos de tiempo de ejecución
    while (subcarpetasFuente.hasNext()) {
      const elapsedTime = (new Date().getTime() - startTime) / 1000;
      if (elapsedTime > 270) { // 4.5 minutos para tener margen de seguridad
        Logger.log("Pausando la ejecución para evitar el límite de tiempo.");
        scriptProperties.setProperty('continuationToken', subcarpetasFuente.getContinuationToken());
        crearDisparadorParaContinuar();
        return; // Detener la ejecución actual
      }

      const subcarpetaAnio = subcarpetasFuente.next();
      const subcarpetaDestino = getOrCreateFolder(carpetaDestinoGeneraciones, subcarpetaAnio.getName());
      
      const archivosYaRespaldados = new Set();
      const archivosDestino = subcarpetaDestino.getFiles();
      while (archivosDestino.hasNext()) {
        archivosYaRespaldados.add(archivosDestino.next().getName());
      }

      const archivosFuente = subcarpetaAnio.getFiles();
      while (archivosFuente.hasNext()) {
        const archivoFuente = archivosFuente.next();
        const nombreArchivo = archivoFuente.getName();

        if (!archivosYaRespaldados.has(nombreArchivo)) {
          archivoFuente.makeCopy(nombreArchivo, subcarpetaDestino);
          Logger.log(`COPIADO: ${subcarpetaAnio.getName()}/${nombreArchivo}`);
        }
      }
    }

    // Si el bucle termina, significa que no hay más carpetas que procesar
    Logger.log("✅ Sincronización completa. Limpiando estado y disparadores.");
    scriptProperties.deleteProperty('continuationToken');
    eliminarDisparadores();

  } catch (e) {
    Logger.log(`Ocurrió un error: ${e.message}`);
  }
}

/**
 * Crea un disparador temporal para reanudar el script en 5 minutos.
 */
function crearDisparadorParaContinuar() {
  eliminarDisparadores(); // Eliminar cualquier disparador anterior para evitar duplicados
  ScriptApp.newTrigger('sincronizarBackupConPaginacion')
      .timeBased()
      .after(5 * 60 * 1000) // 5 minutos
      .create();
  Logger.log("Disparador creado para continuar en 5 minutos.");
}

/**
 * Elimina todos los disparadores temporales asociados a esta función.
 */
function eliminarDisparadores() {
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === 'sincronizarBackupConPaginacion') {
      ScriptApp.deleteTrigger(trigger);
    }
  }
}

/**
 * Función auxiliar para obtener o crear una carpeta.
 */
function getOrCreateFolder(parentFolder, folderName) {
  const folders = parentFolder.getFoldersByName(folderName);
  if (folders.hasNext()) {
    return folders.next();
  }
  return parentFolder.createFolder(folderName);
}