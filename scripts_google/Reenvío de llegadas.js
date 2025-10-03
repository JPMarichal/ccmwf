/**
 * SCRIPT DE REENVÍO AUTOMÁTICO DE CORREOS DE LLEGADAS
 * 
 * Este script automatiza el reenvío de correos específicos (ajustes de llegadas)
 * desde la cuenta personal hacia la cuenta misional del CCM.
 * 
 * FUNCIÓN:
 * - Busca correos con criterios específicos (definidos en Config.js)
 * - Reenvía automáticamente al correo misional
 * - Etiqueta los correos procesados para evitar duplicados
 * - Mueve correos procesados a la papelera para mantener orden
 * 
 * CARACTERÍSTICAS:
 * - Previene procesamiento duplicado con etiquetas
 * - Conserva asunto original en el reenvío
 * - Logging detallado del proceso
 * - Manejo seguro de errores
 * 
 * CONFIGURACIÓN:
 * - Criterio de búsqueda: SEARCH_QUERY_REENVIO (Config.js)
 * - Email destino: DESTINATION_EMAIL_REENVIO (Config.js)
 * - Etiqueta de procesados: PROCESSED_LABEL_REENVIO (Config.js)
 * 
 * USO:
 * - Ejecutar reenviarCorreosHistoricos() manualmente o con trigger
 * - Ideal para trigger diario automático
 * 
 * @author CCM Scripts
 * @version 2.0
 */

/**
 * Reenvía correos históricos que coincidan con criterios específicos
 * Los etiqueta como procesados y los mueve a la papelera para limpiar el buzón
 */
function reenviarCorreosHistoricos() {
  // Las variables de configuración están centralizadas en Config.js

  // Crear la etiqueta si no existe
  let label = GmailApp.getUserLabelByName(PROCESSED_LABEL_REENVIO);
  if (!label) {
    label = GmailApp.createLabel(PROCESSED_LABEL_REENVIO);
  }

  // Buscar los hilos que coincidan y que NO hayan sido procesados antes
  const threads = GmailApp.search(`${SEARCH_QUERY_REENVIO} -label:${PROCESSED_LABEL_REENVIO}`);
  
  if (threads.length === 0) {
    Logger.log("No se encontraron correos nuevos que coincidan con la búsqueda para reenviar.");
    return;
  }

  Logger.log(`Se encontraron ${threads.length} correos para reenviar. Procesando...`);

  threads.forEach(thread => {
    const message = thread.getMessages()[0];
    const originalSubject = message.getSubject();

    try {
      // 1. Reenviar el mensaje
      message.forward(DESTINATION_EMAIL_REENVIO, {
        subject: originalSubject
      });
      
      // 2. Etiquetar el hilo para no volver a procesarlo
      thread.addLabel(label);
      
      // 3. (NUEVO) Mover el hilo a la papelera
      thread.moveToTrash();
      
      Logger.log(`Correo con asunto "${originalSubject}" reenviado y eliminado.`);

      // Pausa para no exceder los límites de Gmail
      Utilities.sleep(1000);

    } catch (e) {
      Logger.log(`Error al procesar el correo "${originalSubject}": ${e.message}`);
    }
  });

  Logger.log("Proceso de reenvío completado.");
}