/**
 * SCRIPT DE EXTRACCIÓN DE ATTACHMENTS DE CORREOS DE LLEGADAS
 * 
 * Este script automatiza la extracción de archivos adjuntos desde correos
 * con asunto "Misioneros que llegan " y los guarda en Google Drive organizados
 * por fecha de generación.
 * 
 * FUNCIÓN PRINCIPAL:
 * - Busca correos no leídos con asunto que empiece con "Misioneros que llegan "
 * - Extrae la fecha de generación del cuerpo del correo
 * - Crea carpetas organizadas por fecha (formato YYYYMMDD)
 * - Guarda todos los archivos adjuntos en la carpeta correspondiente
 * - Marca el correo como leído para evitar reprocesamiento
 * 
 * CARACTERÍSTICAS:
 * - Prevención de procesamiento duplicado marcando correos como leídos
 * - Organización automática por fecha de generación
 * - Manejo robusto de errores y logging detallado
 * - Soporte para múltiples formatos de archivos adjuntos
 * - Creación automática de estructura de carpetas
 * 
 * CONFIGURACIÓN:
 * - Criterio de búsqueda: SEARCH_QUERY_MISIONEROS (Config.js)
 * - Carpeta base: ID_CARPETA_ATTACHMENTS (Config.js)
 * - Etiqueta de procesados: PROCESSED_LABEL_MISIONEROS (Config.js)
 * 
 * FORMATO DE FECHA ESPERADO:
 * - El correo debe contener: "Generación del [dd] de [mes] de [yyyy]"
 * - Ejemplo: "Generación del 11 de agosto de 2025"
 * - Se convierte a: "20250811"
 * 
 * USO:
 * - Ejecutar extraerAttachmentsLlegadas() manualmente o con trigger
 * - Ideal para trigger cada hora o diario
 * 
 * @author CCM Scripts
 * @version 1.0
 */

/**
 * Función principal que extrae attachments de correos de llegadas de misioneros
 */
function extraerAttachmentsLlegadas() {
  try {
    Logger.log("🚀 Iniciando extracción de attachments de correos de llegadas...");
    
    // Crear la etiqueta si no existe
    let label = GmailApp.getUserLabelByName(PROCESSED_LABEL_MISIONEROS);
    if (!label) {
      label = GmailApp.createLabel(PROCESSED_LABEL_MISIONEROS);
      Logger.log(`✅ Etiqueta "${PROCESSED_LABEL_MISIONEROS}" creada.`);
    }
    
    // Buscar correos no leídos que coincidan con el criterio
    const threads = GmailApp.search(SEARCH_QUERY_MISIONEROS);
    
    if (threads.length === 0) {
      Logger.log("ℹ️ No se encontraron correos nuevos que coincidan con la búsqueda.");
      return {
        exito: true,
        mensaje: "No hay correos nuevos para procesar",
        procesados: 0
      };
    }
    
    Logger.log(`📧 Se encontraron ${threads.length} correos para procesar.`);
    
    const resultados = {
      exito: true,
      procesados: 0,
      errores: 0,
      detalles: []
    };
    
    // Procesar cada hilo de correo
    for (let i = 0; i < threads.length; i++) {
      const thread = threads[i];
      const messages = thread.getMessages();
      
      // Procesar cada mensaje en el hilo
      for (let j = 0; j < messages.length; j++) {
        const message = messages[j];
        
        try {
          const resultado = procesarMensaje(message, label);
          resultados.detalles.push(resultado);
          
          if (resultado.exito) {
            resultados.procesados++;
            Logger.log(`✅ Mensaje procesado: ${resultado.asunto}`);
          } else {
            resultados.errores++;
            Logger.log(`❌ Error procesando mensaje: ${resultado.error}`);
          }
          
          // Pausa para evitar límites de API
          Utilities.sleep(1000);
          
        } catch (e) {
          resultados.errores++;
          Logger.log(`❌ Error procesando mensaje: ${e.toString()}`);
          resultados.detalles.push({
            exito: false,
            error: e.toString(),
            asunto: message.getSubject()
          });
        }
      }
    }
    
    const resumen = `✅ Proceso completado - Procesados: ${resultados.procesados}, Errores: ${resultados.errores}`;
    Logger.log(resumen);
    
    return resultados;
    
  } catch (e) {
    const errorMsg = `❌ ERROR CRÍTICO en extraerAttachmentsLlegadas: ${e.toString()}`;
    Logger.log(errorMsg);
    Logger.log(`Stack trace: ${e.stack}`);
    
    return {
      exito: false,
      error: errorMsg,
      procesados: 0
    };
  }
}

/**
 * Procesa un mensaje individual extrayendo sus attachments
 * @param {GmailMessage} message - El mensaje a procesar
 * @param {GmailLabel} label - La etiqueta para marcar como procesado
 * @returns {Object} Resultado del procesamiento
 */
function procesarMensaje(message, label) {
  const asunto = message.getSubject();
  const cuerpo = message.getPlainBody();
  const fechaCorreo = message.getDate();
  
  Logger.log(`🔄 Procesando: ${asunto}`);
  
  // Verificar que el asunto coincide con nuestro criterio
  if (!asunto.startsWith("Misioneros que llegan ")) {
    return {
      exito: false,
      error: "Asunto no coincide con criterio esperado",
      asunto: asunto
    };
  }
  
  // Extraer fecha de generación del cuerpo
  const fechaGeneracion = extraerFechaGeneracion(cuerpo);
  if (!fechaGeneracion) {
    return {
      exito: false,
      error: "No se pudo extraer fecha de generación del cuerpo",
      asunto: asunto,
      cuerpo: cuerpo.substring(0, 200) + "..."
    };
  }
  
  Logger.log(`📅 Fecha de generación extraída: ${fechaGeneracion}`);
  
  // Obtener attachments
  const attachments = message.getAttachments();
  if (attachments.length === 0) {
    // Marcar como leído aunque no tenga attachments
    message.markRead();
    message.getThread().addLabel(label);
    
    return {
      exito: true,
      mensaje: "Correo sin attachments, marcado como procesado",
      asunto: asunto,
      fechaGeneracion: fechaGeneracion,
      attachments: 0
    };
  }
  
  Logger.log(`📎 Se encontraron ${attachments.length} attachments`);
  
  // Crear/obtener carpeta de destino
  const carpetaDestino = crearCarpetaGeneracion(fechaGeneracion);
  if (!carpetaDestino) {
    return {
      exito: false,
      error: "No se pudo crear/obtener carpeta de destino",
      asunto: asunto,
      fechaGeneracion: fechaGeneracion
    };
  }
  
  // Guardar cada attachment
  const archivosGuardados = [];
  const erroresAttachments = [];
  
  for (let k = 0; k < attachments.length; k++) {
    const attachment = attachments[k];
    
    try {
      const nombreArchivo = limpiarNombreArchivo(attachment.getName());
      const nombreUnico = generarNombreUnico(carpetaDestino, nombreArchivo);
      
      Logger.log(`💾 Guardando attachment: ${nombreUnico}`);
      
      const archivo = carpetaDestino.createFile(attachment.copyBlob().setName(nombreUnico));
      archivosGuardados.push({
        nombre: nombreUnico,
        tamaño: attachment.getSize(),
        tipo: attachment.getContentType(),
        id: archivo.getId()
      });
      
      Logger.log(`✅ Archivo guardado: ${nombreUnico} (${attachment.getSize()} bytes)`);
      
    } catch (e) {
      const error = `Error guardando ${attachment.getName()}: ${e.toString()}`;
      erroresAttachments.push(error);
      Logger.log(`❌ ${error}`);
    }
  }
  
  // Marcar correo como procesado
  try {
    message.markRead();
    message.getThread().addLabel(label);
    Logger.log("✅ Correo marcado como leído y etiquetado");
  } catch (e) {
    Logger.log(`⚠️ Error marcando correo como procesado: ${e.toString()}`);
  }
  
  return {
    exito: true,
    asunto: asunto,
    fechaGeneracion: fechaGeneracion,
    carpetaDestino: carpetaDestino.getName(),
    carpetaId: carpetaDestino.getId(),
    attachments: attachments.length,
    archivosGuardados: archivosGuardados,
    erroresAttachments: erroresAttachments,
    fechaCorreo: fechaCorreo
  };
}

/**
 * Extrae la fecha de generación del cuerpo del correo
 * @param {string} cuerpo - El cuerpo del correo
 * @returns {string|null} Fecha en formato YYYYMMDD o null si no se encuentra
 */
function extraerFechaGeneracion(cuerpo) {
  try {
    // Patrón para buscar "Generación del DD de MES de YYYY"
    const patron = /Generación del (\d{1,2}) de (\w+) de (\d{4})/i;
    const coincidencia = cuerpo.match(patron);
    
    if (!coincidencia) {
      Logger.log("⚠️ No se encontró patrón de fecha en el cuerpo del correo");
      return null;
    }
    
    const dia = coincidencia[1].padStart(2, '0');
    const mesTexto = coincidencia[2].toLowerCase();
    const año = coincidencia[3];
    
    // Mapeo de meses en español
    const meses = {
      'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
      'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
      'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    };
    
    const mes = meses[mesTexto];
    if (!mes) {
      Logger.log(`⚠️ Mes no reconocido: ${mesTexto}`);
      return null;
    }
    
    const fechaFormateada = `${año}${mes}${dia}`;
    Logger.log(`📅 Fecha extraída: ${dia} de ${mesTexto} de ${año} -> ${fechaFormateada}`);
    
    return fechaFormateada;
    
  } catch (e) {
    Logger.log(`❌ Error extrayendo fecha: ${e.toString()}`);
    return null;
  }
}

/**
 * Crea o obtiene la carpeta para una fecha de generación específica
 * @param {string} fechaGeneracion - Fecha en formato YYYYMMDD
 * @returns {GoogleAppsScript.Drive.Folder|null} La carpeta creada/encontrada o null si hay error
 */
function crearCarpetaGeneracion(fechaGeneracion) {
  try {
    const carpetaBase = DriveApp.getFolderById(ID_CARPETA_ATTACHMENTS);
    Logger.log(`📁 Carpeta base obtenida: ${carpetaBase.getName()}`);
    
    // Buscar si ya existe la carpeta con este nombre
    const carpetasExistentes = carpetaBase.getFoldersByName(fechaGeneracion);
    
    if (carpetasExistentes.hasNext()) {
      const carpetaExistente = carpetasExistentes.next();
      Logger.log(`📁 Carpeta existente encontrada: ${carpetaExistente.getName()}`);
      return carpetaExistente;
    }
    
    // Crear nueva carpeta
    const nuevaCarpeta = carpetaBase.createFolder(fechaGeneracion);
    Logger.log(`📁 Nueva carpeta creada: ${nuevaCarpeta.getName()} (ID: ${nuevaCarpeta.getId()})`);
    
    return nuevaCarpeta;
    
  } catch (e) {
    Logger.log(`❌ Error creando/obteniendo carpeta: ${e.toString()}`);
    return null;
  }
}

/**
 * Limpia el nombre del archivo removiendo caracteres no válidos
 * @param {string} nombreOriginal - Nombre original del archivo
 * @returns {string} Nombre limpio
 */
function limpiarNombreArchivo(nombreOriginal) {
  // Remover caracteres problemáticos pero mantener puntos para extensiones
  return nombreOriginal
    .replace(/[<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, '_')
    .substring(0, 100); // Limitar longitud
}

/**
 * Genera un nombre único para evitar conflictos en la carpeta
 * @param {GoogleAppsScript.Drive.Folder} carpeta - La carpeta donde se guardará
 * @param {string} nombreBase - Nombre base del archivo
 * @returns {string} Nombre único
 */
function generarNombreUnico(carpeta, nombreBase) {
  try {
    // Verificar si ya existe un archivo con este nombre
    const archivosExistentes = carpeta.getFilesByName(nombreBase);
    
    if (!archivosExistentes.hasNext()) {
      return nombreBase; // El nombre está disponible
    }
    
    // Generar nombre único agregando timestamp
    const timestamp = new Date().getTime();
    const puntoExtension = nombreBase.lastIndexOf('.');
    
    if (puntoExtension > 0) {
      const nombre = nombreBase.substring(0, puntoExtension);
      const extension = nombreBase.substring(puntoExtension);
      return `${nombre}_${timestamp}${extension}`;
    } else {
      return `${nombreBase}_${timestamp}`;
    }
    
  } catch (e) {
    Logger.log(`⚠️ Error generando nombre único: ${e.toString()}`);
    // Fallback: usar timestamp
    return `${nombreBase}_${new Date().getTime()}`;
  }
}

/**
 * Función de utilidad para listar correos que coinciden con la búsqueda (sin procesar)
 * Útil para debugging y verificación
 */
function listarCorreosLlegadas() {
  try {
    Logger.log("🔍 Listando correos que coinciden con la búsqueda...");
    
    const threads = GmailApp.search(SEARCH_QUERY_MISIONEROS);
    Logger.log(`📧 Se encontraron ${threads.length} hilos de correo`);
    
    threads.forEach((thread, index) => {
      const messages = thread.getMessages();
      Logger.log(`\n--- Hilo ${index + 1} ---`);
      
      messages.forEach((message, msgIndex) => {
        const asunto = message.getSubject();
        const fecha = message.getDate();
        const attachments = message.getAttachments();
        const isUnread = message.isUnread();
        
        Logger.log(`Mensaje ${msgIndex + 1}:`);
        Logger.log(`  Asunto: ${asunto}`);
        Logger.log(`  Fecha: ${fecha}`);
        Logger.log(`  No leído: ${isUnread}`);
        Logger.log(`  Attachments: ${attachments.length}`);
        
        if (attachments.length > 0) {
          attachments.forEach((att, attIndex) => {
            Logger.log(`    ${attIndex + 1}. ${att.getName()} (${att.getSize()} bytes)`);
          });
        }
      });
    });
    
  } catch (e) {
    Logger.log(`❌ Error listando correos: ${e.toString()}`);
  }
}

/**
 * Función de prueba para verificar extracción de fecha
 * @param {string} textoPrueba - Texto de prueba opcional
 */
function probarExtraccionFecha(textoPrueba) {
  const textoDefault = textoPrueba || "Estimados hermanos, adjunto la información de la Generación del 11 de agosto de 2025. Saludos cordiales.";
  
  Logger.log("🧪 Probando extracción de fecha...");
  Logger.log(`Texto de prueba: ${textoDefault}`);
  
  const fechaExtraida = extraerFechaGeneracion(textoDefault);
  Logger.log(`Resultado: ${fechaExtraida}`);
  
  return fechaExtraida;
}

/**
 * Función de limpieza para remover etiquetas de prueba (uso administrativo)
 */
function limpiarEtiquetasPrueba() {
  try {
    const label = GmailApp.getUserLabelByName(PROCESSED_LABEL_MISIONEROS);
    if (label) {
      const threads = label.getThreads();
      Logger.log(`🧹 Removiendo etiqueta de ${threads.length} hilos...`);
      
      threads.forEach(thread => {
        thread.removeLabel(label);
      });
      
      Logger.log("✅ Etiquetas removidas exitosamente");
    } else {
      Logger.log("ℹ️ No se encontró la etiqueta para limpiar");
    }
  } catch (e) {
    Logger.log(`❌ Error limpiando etiquetas: ${e.toString()}`);
  }
}
