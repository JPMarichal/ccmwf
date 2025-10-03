/**
 * SCRIPT DE ENVÍO DE REPORTES MISIONALES EN PDF
 * 
 * Este script convierte las hojas de cálculo principales (Branch in a Glance 
 * y Reporte Misional Concentrado) a PDF y las envía por correo electrónico
 * al liderazgo de la rama.
 * 
 * FUNCIONES PRINCIPALES:
 * - Convierte hojas de cálculo específicas a PDF
 * - Envía los PDFs por correo a destinatarios predefinidos
 * - Maneja errores y proporciona logs detallados
 * 
 * CONFIGURACIÓN:
 * - Todas las configuraciones están centralizadas en Config.js
 * - URLs, destinatarios y configuración de PDF en REPORTES_PDF_CONFIG
 * 
 * USO:
 * - Ejecutar enviarReportesPDFCompleto() manualmente o con trigger
 * - Ejecutar enviarReporteIndividual() para reportes específicos
 * 
 * @author CCM Scripts
 * @version 1.0
 */

/**
 * Función principal que envía ambos reportes en PDF en un solo correo
 */
function enviarReportesPDFCompleto() {
  console.log("Iniciando proceso de envío de reportes PDF...");
  
  try {
    // Generar ambos PDFs
    console.log("Generando PDF de Branch in a Glance...");
    const pdfBranch = generarPDFReporte('branchInAGlance');
    
    console.log("Generando PDF de Reporte Misional Concentrado...");
    const pdfReporte = generarPDFReporte('reporteMisionalConcentrado');
    
    if (!pdfBranch.exito || !pdfReporte.exito) {
      throw new Error(`Error generando PDFs: ${pdfBranch.error || pdfReporte.error}`);
    }
    
    console.log("Ambos PDFs generados exitosamente");
    
    // Enviar correo con ambos PDFs
    const resultadoCorreo = enviarCorreoConAmbosPDFs([pdfBranch.pdf, pdfReporte.pdf]);
    
    // Enviar resumen por correo
    enviarResumenEnvio([{
      exito: resultadoCorreo.exito,
      reporte: "Reportes Misionales Completos",
      correo: resultadoCorreo
    }]);
    
    console.log("Proceso completado exitosamente");
    return {
      exito: true,
      mensaje: "Reportes enviados correctamente en un solo correo",
      detalles: {
        pdfBranch: pdfBranch,
        pdfReporte: pdfReporte,
        correo: resultadoCorreo
      }
    };
    
  } catch (error) {
    console.error("Error en enviarReportesPDFCompleto:", error);
    return {
      exito: false,
      mensaje: "Error al enviar reportes",
      error: error.toString()
    };
  }
}

/**
 * Genera un PDF para un tipo de reporte específico
 * @param {string} tipoReporte - 'branchInAGlance' o 'reporteMisionalConcentrado'
 * @returns {Object} Resultado con el PDF generado
 */
function generarPDFReporte(tipoReporte) {
  try {
    // Validar tipo de reporte
    if (!REPORTES_PDF_CONFIG.spreadsheetIds[tipoReporte]) {
      throw new Error(`Tipo de reporte no válido: ${tipoReporte}`);
    }
    
    // Obtener configuración del reporte
    const spreadsheetId = REPORTES_PDF_CONFIG.spreadsheetIds[tipoReporte];
    const gid = REPORTES_PDF_CONFIG.gids[tipoReporte];
    const nombre = REPORTES_PDF_CONFIG.nombres[tipoReporte];
    
    console.log(`Generando PDF - ID: ${spreadsheetId}, GID: ${gid}, Nombre: ${nombre}`);
    
    // Generar PDF
    const pdfBlob = convertirHojaToPDF(spreadsheetId, gid, nombre);
    
    if (!pdfBlob) {
      throw new Error(`No se pudo generar el PDF para ${nombre}`);
    }
    
    // Obtener tamaño usando getBytes().length
    const tamañoPDF = pdfBlob.getBytes().length;
    console.log(`PDF generado exitosamente para ${nombre}, tamaño: ${tamañoPDF} bytes`);
    
    return {
      exito: true,
      reporte: nombre,
      tamañoPDF: tamañoPDF,
      pdf: pdfBlob
    };
    
  } catch (error) {
    console.error(`Error generando PDF para ${tipoReporte}:`, error);
    return {
      exito: false,
      reporte: tipoReporte,
      error: error.toString()
    };
  }
}

/**
 * Envía un reporte individual en PDF (para pruebas)
 * @param {string} tipoReporte - 'branchInAGlance' o 'reporteMisionalConcentrado'
 */
function enviarReporteIndividualPrueba(tipoReporte) {
  console.log(`Procesando reporte individual para prueba: ${tipoReporte}`);
  
  try {
    // Generar PDF
    const resultadoPDF = generarPDFReporte(tipoReporte);
    
    if (!resultadoPDF.exito) {
      throw new Error(`No se pudo generar el PDF: ${resultadoPDF.error}`);
    }
    
    // Enviar por correo (un solo PDF)
    const resultadoCorreo = enviarCorreoConAmbosPDFs([resultadoPDF.pdf]);
    
    return {
      exito: true,
      reporte: resultadoPDF.reporte,
      tamañoPDF: resultadoPDF.tamañoPDF,
      correo: resultadoCorreo
    };
    
  } catch (error) {
    console.error(`Error procesando ${tipoReporte} para prueba:`, error);
    return {
      exito: false,
      reporte: tipoReporte,
      error: error.toString()
    };
  }
}

/**
 * Convierte una hoja de cálculo específica a PDF
 * @param {string} spreadsheetId - ID de la hoja de cálculo
 * @param {string} gid - GID de la hoja específica
 * @param {string} nombreArchivo - Nombre para el archivo PDF
 * @returns {Blob} PDF como Blob
 */
function convertirHojaToPDF(spreadsheetId, gid, nombreArchivo) {
  try {
    console.log(`Convirtiendo a PDF: ${nombreArchivo} (ID: ${spreadsheetId}, GID: ${gid})`);
    
    // Primero intentar con el método export mejorado
    let exportUrl = construirURLExportPDF(spreadsheetId, gid);
    console.log("Intentando con método export:", exportUrl);
    
    // Obtener token de acceso
    const token = ScriptApp.getOAuthToken();
    
    // Configurar opciones de fetch
    const options = {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      muteHttpExceptions: true
    };
    
    // Hacer la petición
    let response = UrlFetchApp.fetch(exportUrl, options);
    
    console.log(`Código de respuesta (método export): ${response.getResponseCode()}`);
    console.log(`Tipo de contenido: ${response.getHeaders()['Content-Type']}`);
    
    // Si el método export falla, intentar con el método print
    if (response.getResponseCode() !== 200) {
      console.log("Método export falló, intentando con método print...");
      exportUrl = construirURLPrintPDF(spreadsheetId, gid);
      console.log("Intentando con método print:", exportUrl);
      
      response = UrlFetchApp.fetch(exportUrl, options);
      console.log(`Código de respuesta (método print): ${response.getResponseCode()}`);
    }
    
    if (response.getResponseCode() !== 200) {
      console.error(`Error HTTP ${response.getResponseCode()}: ${response.getContentText()}`);
      throw new Error(`Error HTTP ${response.getResponseCode()}: ${response.getContentText()}`);
    }
    
    // Crear blob con nombre apropiado
    const pdfBlob = response.getBlob();
    const fechaActual = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
    const nombreCompleto = `${nombreArchivo}_${fechaActual}.pdf`;
    
    // Establecer nombre y tipo MIME
    pdfBlob.setName(nombreCompleto);
    pdfBlob.setContentType('application/pdf');
    
    // Usar getBytes().length en lugar de getSize() que no existe en Apps Script
    const tamañoBlob = pdfBlob.getBytes().length;
    console.log(`PDF creado exitosamente: ${nombreCompleto}, tamaño: ${tamañoBlob} bytes`);
    
    if (tamañoBlob === 0) {
      throw new Error(`El PDF generado está vacío (0 bytes)`);
    }
    
    return pdfBlob;
    
  } catch (error) {
    console.error(`Error en convertirHojaToPDF para ${nombreArchivo}:`, error);
    throw error;
  }
}

/**
 * Construye la URL para exportar una hoja específica como PDF
 * @param {string} spreadsheetId - ID de la hoja de cálculo
 * @param {string} gid - GID de la hoja específica
 * @returns {string} URL de exportación
 */
function construirURLExportPDF(spreadsheetId, gid) {
  // Usar método 'print' que a menudo captura mejor los íconos y gráficos
  const baseUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetId}/export`;
  
  // Construir parámetros manualmente con configuración mejorada para fit-to-page
  const params = [
    `format=${REPORTES_PDF_CONFIG.pdfConfig.format}`,
    `size=${REPORTES_PDF_CONFIG.pdfConfig.size}`,
    `portrait=${REPORTES_PDF_CONFIG.pdfConfig.portrait}`,
    `fitw=${REPORTES_PDF_CONFIG.pdfConfig.fitw}`,
    `fith=${REPORTES_PDF_CONFIG.pdfConfig.fith}`,
    `gridlines=${REPORTES_PDF_CONFIG.pdfConfig.gridlines}`,
    `printtitle=${REPORTES_PDF_CONFIG.pdfConfig.printtitle}`,
    `sheetnames=${REPORTES_PDF_CONFIG.pdfConfig.sheetnames}`,
    `fzr=${REPORTES_PDF_CONFIG.pdfConfig.fzr}`,
    `fzc=${REPORTES_PDF_CONFIG.pdfConfig.fzc}`,
    `gid=${gid}`,
    // Parámetros adicionales para mejorar calidad y ajuste
    `top_margin=${REPORTES_PDF_CONFIG.pdfConfig.top_margin}`,
    `bottom_margin=${REPORTES_PDF_CONFIG.pdfConfig.bottom_margin}`,
    `left_margin=${REPORTES_PDF_CONFIG.pdfConfig.left_margin}`,
    `right_margin=${REPORTES_PDF_CONFIG.pdfConfig.right_margin}`,
    `horizontal_alignment=${REPORTES_PDF_CONFIG.pdfConfig.horizontal_alignment}`,
    `vertical_alignment=${REPORTES_PDF_CONFIG.pdfConfig.vertical_alignment}`,
    `scale=${REPORTES_PDF_CONFIG.pdfConfig.scale}`,
    `fmtonly=${REPORTES_PDF_CONFIG.pdfConfig.fmtonly}`,
    `attachment=${REPORTES_PDF_CONFIG.pdfConfig.attachment}`,
    `repeat_headers=${REPORTES_PDF_CONFIG.pdfConfig.repeat_headers}`,
    `repeat_columns=${REPORTES_PDF_CONFIG.pdfConfig.repeat_columns}`,
    `page_order=${REPORTES_PDF_CONFIG.pdfConfig.page_order}`,
    // Parámetros adicionales para preservar formato
    `exportFormat=pdf`,
    `id=${spreadsheetId}`
  ];
  
  const urlCompleta = `${baseUrl}?${params.join('&')}`;
  console.log("URL construida con configuración fit-to-page:", urlCompleta);
  
  return urlCompleta;
}

/**
 * Construye URL alternativa usando el método 'print' para mejor captura de gráficos
 * @param {string} spreadsheetId - ID de la hoja de cálculo
 * @param {string} gid - GID de la hoja específica
 * @returns {string} URL de exportación usando método print
 */
function construirURLPrintPDF(spreadsheetId, gid) {
  // URL usando método print con configuración agresiva de fit-to-page
  const baseUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetId}/print`;
  
  const params = [
    `format=pdf`,
    `size=letter`,
    `portrait=true`,
    `scale=2`, // Fit to page width
    `fitw=true`,
    `fith=true`,
    `top_margin=0.5`,
    `bottom_margin=0.5`,
    `left_margin=0.5`,
    `right_margin=0.5`,
    `horizontal_alignment=CENTER`,
    `vertical_alignment=TOP`,
    `gridlines=false`,
    `printtitle=true`,
    `sheetnames=false`,
    `fzr=false`,
    `fzc=false`,
    `repeat_headers=false`,
    `repeat_columns=false`,
    `page_order=1`,
    `gid=${gid}`,
    `id=${spreadsheetId}`
  ];
  
  const urlCompleta = `${baseUrl}?${params.join('&')}`;
  console.log("URL alternativa construida (método print con fit-to-page):", urlCompleta);
  
  return urlCompleta;
}

/**
 * Envía un correo electrónico con ambos PDFs adjuntos
 * @param {Array} pdfBlobs - Array con los PDFs como Blobs
 * @returns {Object} Resultado del envío
 */
function enviarCorreoConAmbosPDFs(pdfBlobs) {
  try {
    const fechaActual = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy");
    
    // Personalizar asunto
    const asunto = REPORTES_PDF_CONFIG.correo.asunto.replace('{fecha}', fechaActual);
    
    const resultadosEnvio = [];
    
    // Verificar que tenemos PDFs para enviar
    if (!pdfBlobs || pdfBlobs.length === 0) {
      throw new Error("No hay PDFs para enviar");
    }
    
    console.log(`Preparando envío de ${pdfBlobs.length} PDFs`);
    
    // Enviar a cada destinatario individualmente con saludo personalizado
    REPORTES_PDF_CONFIG.destinatarios.forEach(emailDestinatario => {
      try {
        console.log(`Procesando destinatario: ${emailDestinatario}`);
        
        // Validar email
        if (!emailDestinatario || typeof emailDestinatario !== 'string' || !emailDestinatario.includes('@')) {
          throw new Error(`Email inválido: ${emailDestinatario}`);
        }
        
        // Determinar el saludo apropiado según el destinatario
        const saludo = obtenerSaludoPersonalizado(emailDestinatario);
        
        // Personalizar cuerpo del mensaje para este destinatario
        const cuerpo = REPORTES_PDF_CONFIG.correo.cuerpoMensaje
          .replace('{saludo}', saludo)
          .replace('{remitente}', REPORTES_PDF_CONFIG.correo.remitente)
          .replace('{cargo}', REPORTES_PDF_CONFIG.liderazgoRama.primerConsejero.cargo)
          .replace('{fecha}', fechaActual);
        
        console.log(`Enviando correo a ${emailDestinatario} con saludo: ${saludo}`);
        console.log(`Asunto: ${asunto}`);
        console.log(`Remitente configurado: ${REPORTES_PDF_CONFIG.correo.correoRemitente}`);
        console.log(`Nombre remitente: ${REPORTES_PDF_CONFIG.correo.remitente}`);
        console.log(`Número de adjuntos: ${pdfBlobs.length}`);
        
        // Verificar adjuntos
        pdfBlobs.forEach((blob, index) => {
          console.log(`Adjunto ${index + 1}: ${blob.getName()}, tamaño: ${blob.getBytes().length} bytes`);
        });
        
        // Enviar correo con ambos PDFs adjuntos usando GmailApp
        GmailApp.sendEmail(
          emailDestinatario,
          asunto,
          cuerpo,
          {
            attachments: pdfBlobs,
            name: REPORTES_PDF_CONFIG.correo.remitente
          }
        );
        
        resultadosEnvio.push({
          destinatario: emailDestinatario,
          saludo: saludo,
          adjuntos: pdfBlobs.length,
          exito: true
        });
        
        console.log(`Correo con ${pdfBlobs.length} PDFs enviado exitosamente a ${emailDestinatario}`);
        
      } catch (error) {
        console.error(`Error enviando correo a ${emailDestinatario}:`, error);
        resultadosEnvio.push({
          destinatario: emailDestinatario,
          exito: false,
          error: error.toString()
        });
      }
    });
    
    const enviosExitosos = resultadosEnvio.filter(r => r.exito).length;
    const enviosFallidos = resultadosEnvio.filter(r => !r.exito).length;
    
    console.log(`Envío completado - Exitosos: ${enviosExitosos}, Fallidos: ${enviosFallidos}`);
    console.log(`Total de PDFs por correo: ${pdfBlobs.length}`);
    
    return {
      exito: enviosFallidos === 0,
      destinatarios: REPORTES_PDF_CONFIG.destinatarios.length,
      enviosExitosos: enviosExitosos,
      enviosFallidos: enviosFallidos,
      totalPDFs: pdfBlobs.length,
      asunto: asunto,
      detalles: resultadosEnvio
    };
    
  } catch (error) {
    console.error(`Error general enviando correo con múltiples PDFs:`, error);
    return {
      exito: false,
      error: error.toString()
    };
  }
}

/**
 * Obtiene el saludo personalizado según el destinatario
 * @param {string} emailDestinatario - Email del destinatario
 * @returns {string} Saludo personalizado
 */
function obtenerSaludoPersonalizado(emailDestinatario) {
  // Buscar en la configuración de liderazgo
  const liderazgo = REPORTES_PDF_CONFIG.liderazgoRama;
  
  if (emailDestinatario === liderazgo.presidente.email) {
    return "Presidente Alvarez";
  }
  
  if (emailDestinatario === liderazgo.primerConsejero.email) {
    return "Presidente Marichal";
  }
  
  if (emailDestinatario === liderazgo.segundoConsejero.email) {
    return "Presidente Molina";
  }
  
  // Saludo genérico si no se encuentra en la configuración
  return "hermano";
}

/**
 * Envía un resumen del proceso de envío al administrador
 * @param {Array} resultados - Array con los resultados de cada envío
 */
function enviarResumenEnvio(resultados) {
  try {
    const fechaActual = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm");
    
    let resumen = `Resumen de envío de reportes misionales - ${fechaActual}\n\n`;
    
    resultados.forEach((resultado, index) => {
      resumen += `${index + 1}. ${resultado.reporte || 'Reporte'}: `;
      resumen += resultado.exito ? '✓ Exitoso' : '✗ Falló';
      if (resultado.error) {
        resumen += ` - Error: ${resultado.error}`;
      }
      resumen += '\n';
    });
    
    // Enviar solo al administrador
    GmailApp.sendEmail(
      CORREO_PERSONAL,
      `[CCM Scripts] Resumen envío reportes - ${fechaActual}`,
      resumen,
      {
        from: CORREO_MISIONAL,
        name: REMITENTE_NOMBRE
      }
    );
    
    console.log("Resumen enviado al administrador");
    
  } catch (error) {
    console.error("Error enviando resumen:", error);
  }
}

/**
 * Función de prueba específica para verificar el ajuste completo a la página (fit-to-page)
 */
function pruebaFitToPage() {
  console.log("=== PRUEBA DE FIT-TO-PAGE ===");
  
  try {
    // Probar ambos reportes para verificar el ajuste
    const reportes = ['branchInAGlance', 'reporteMisionalConcentrado'];
    const pdfBlobs = [];
    
    for (const tipoReporte of reportes) {
      console.log(`Generando PDF con fit-to-page para: ${tipoReporte}`);
      
      const spreadsheetId = REPORTES_PDF_CONFIG.spreadsheetIds[tipoReporte];
      const gid = REPORTES_PDF_CONFIG.gids[tipoReporte];
      const nombre = REPORTES_PDF_CONFIG.nombres[tipoReporte];
      
      console.log(`Configuración: ID=${spreadsheetId}, GID=${gid}, Nombre=${nombre}`);
      
      // Generar PDF con la nueva configuración de fit-to-page
      const pdfBlob = convertirHojaToPDF(spreadsheetId, gid, nombre);
      
      const tamañoPDF = pdfBlob.getBytes().length;
      console.log(`PDF ${nombre} generado: ${tamañoPDF} bytes`);
      
      pdfBlobs.push(pdfBlob);
    }
    
    // Enviar por correo para inspección
    const fechaActual = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm");
    const asunto = `[PRUEBA FIT-TO-PAGE] Reportes con ajuste completo - ${fechaActual}`;
    const cuerpo = `Estimado Presidente Marichal,

Estos son PDFs de prueba generados con configuración FIT-TO-PAGE mejorada:

✅ Ajuste al ancho (fitw=true)
✅ Ajuste a la altura (fith=true) 
✅ Escala automática (scale=2)
✅ Márgenes reducidos (0.5 pulgadas)
✅ Método de exportación con fallback

Cambios específicos para evitar truncamiento:
- fitw=true y fith=true (ajuste completo)
- scale=2 (fit to page automático)
- Márgenes reducidos a 0.5"
- Método print como alternativa

Por favor verifica que:
1. Todo el contenido se ve completo horizontalmente
2. No hay truncamiento en los bordes
3. Los íconos del Gantt se siguen viendo
4. El formato general se mantiene legible

Adjuntos: ${pdfBlobs.length} PDFs
Tamaños: ${pdfBlobs.map(p => Math.round(p.getBytes().length / 1024) + 'KB').join(', ')}

Saludos cordiales,
Sistema de Reportes CCM (Modo Fit-to-Page)`;

    GmailApp.sendEmail(
      "jpmarichal@train.missionary.org",
      asunto,
      cuerpo,
      {
        attachments: pdfBlobs,
        name: "Sistema de Reportes CCM"
      }
    );
    
    console.log("PDFs de prueba fit-to-page enviados exitosamente");
    
    return {
      exito: true,
      totalPDFs: pdfBlobs.length,
      tamaños: pdfBlobs.map(p => p.getBytes().length),
      configuracion: "fit-to-page mejorado",
      mensaje: "PDFs con ajuste completo generados y enviados para revisión"
    };
    
  } catch (error) {
    console.error("Error en prueba fit-to-page:", error);
    return {
      exito: false,
      error: error.toString()
    };
  }
}

/**
 * Función de prueba específica para verificar la captura de íconos y headers/footers
 */
function pruebaGeneracionPDFMejorado() {
  console.log("=== PRUEBA DE GENERACIÓN PDF MEJORADO ===");
  
  try {
    // Probar solo Branch in a Glance que tiene los íconos del Gantt
    console.log("Generando PDF de Branch in a Glance con configuración mejorada...");
    
    const tipoReporte = 'branchInAGlance';
    const spreadsheetId = REPORTES_PDF_CONFIG.spreadsheetIds[tipoReporte];
    const gid = REPORTES_PDF_CONFIG.gids[tipoReporte];
    const nombre = REPORTES_PDF_CONFIG.nombres[tipoReporte];
    
    console.log(`Configuración: ID=${spreadsheetId}, GID=${gid}, Nombre=${nombre}`);
    
    // Generar PDF con la nueva configuración
    const pdfBlob = convertirHojaToPDF(spreadsheetId, gid, nombre);
    
    const tamañoPDF = pdfBlob.getBytes().length;
    console.log(`PDF generado exitosamente: ${tamañoPDF} bytes`);
    
    // Enviar por correo para inspección
    const fechaActual = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm");
    const asunto = `[PRUEBA PDF MEJORADO] ${nombre} - ${fechaActual}`;
    const cuerpo = `Estimado Presidente Marichal,

Este es un PDF de prueba generado con la configuración mejorada para verificar:

✅ Íconos del Gantt en Branch in a Glance
✅ Headers y footers configurados
✅ Mejor calidad de imagen y formato

Configuración utilizada:
- Tamaño: Letter
- Título de hoja: Habilitado
- Márgenes mejorados
- Método de exportación con fallback

Tamaño del archivo: ${Math.round(tamañoPDF / 1024)} KB

Por favor revisa si ahora se ven correctamente:
1. Los íconos en las celdas del Gantt
2. Los headers y footers de la hoja
3. La calidad general del formato

Saludos cordiales,
Sistema de Reportes CCM`;

    GmailApp.sendEmail(
      "jpmarichal@train.missionary.org",
      asunto,
      cuerpo,
      {
        attachments: [pdfBlob],
        name: "Sistema de Reportes CCM"
      }
    );
    
    console.log("PDF de prueba enviado exitosamente");
    
    return {
      exito: true,
      tamañoPDF: tamañoPDF,
      nombreArchivo: pdfBlob.getName(),
      mensaje: "PDF mejorado generado y enviado para revisión"
    };
    
  } catch (error) {
    console.error("Error en prueba de PDF mejorado:", error);
    return {
      exito: false,
      error: error.toString()
    };
  }
}

/**
 * Función de prueba para verificar acceso a las hojas de cálculo
 */
function probarAccesoHojas() {
  console.log("=== PRUEBA DE ACCESO A HOJAS ===");
  
  Object.keys(REPORTES_PDF_CONFIG.spreadsheetIds).forEach(tipo => {
    try {
      const id = REPORTES_PDF_CONFIG.spreadsheetIds[tipo];
      console.log(`\nProbando acceso a ${tipo}:`);
      console.log(`ID: ${id}`);
      
      const spreadsheet = SpreadsheetApp.openById(id);
      console.log(`✓ Spreadsheet abierto: ${spreadsheet.getName()}`);
      
      const sheets = spreadsheet.getSheets();
      console.log(`✓ Número de hojas: ${sheets.length}`);
      
      sheets.forEach((sheet, index) => {
        console.log(`  Hoja ${index}: ${sheet.getName()}, GID: ${sheet.getSheetId()}`);
      });
      
    } catch (error) {
      console.error(`✗ Error accediendo a ${tipo}:`, error);
    }
  });
  
  return "Prueba completada - Ver logs para detalles";
}

/**
 * Función de prueba usando GmailApp en lugar de MailApp
 */
function pruebaCorreoConGmail() {
  console.log("=== PRUEBA CON GMAIL API ===");
  
  try {
    const destinatario = "jpmarichal@train.missionary.org";
    const asunto = "[PRUEBA GMAIL API] Verificación de entrega de correo";
    const cuerpo = `Esta es una prueba usando GmailApp para verificar la entrega de correo.

Destinatario configurado: ${destinatario}
Fecha y hora: ${new Date().toLocaleString()}
Método usado: GmailApp.sendEmail()

Este correo debería llegar al correo misional si GmailApp funciona diferente a MailApp.

Configuración actual:
- Destinatario: ${destinatario}
- Sistema: Google Apps Script con Gmail API
- Usuario activo: ${Session.getActiveUser().getEmail()}
- Zona horaria: ${Session.getScriptTimeZone()}`;

    console.log(`Enviando correo con Gmail API a: ${destinatario}`);
    console.log(`Usuario activo: ${Session.getActiveUser().getEmail()}`);
    
    // Usar GmailApp en lugar de MailApp
    GmailApp.sendEmail(destinatario, asunto, cuerpo);
    
    console.log("Correo con Gmail API enviado exitosamente");
    console.log("IMPORTANTE: Verifica si este correo llega a jpmarichal@train.missionary.org o a jpmarichal@gmail.com");
    
    return {
      exito: true,
      destinatario: destinatario,
      metodo: "GmailApp",
      usuario: Session.getActiveUser().getEmail()
    };
    
  } catch (error) {
    console.error("Error enviando correo con Gmail API:", error);
    return {
      exito: false,
      error: error.toString()
    };
  }
}

/**
 * Función de prueba simple para envío de correo sin PDFs
 */
function pruebaCorreoSimple() {
  console.log("=== PRUEBA SIMPLE DE ENVÍO DE CORREO ===");
  
  try {
    const destinatario = "jpmarichal@train.missionary.org";
    const asunto = "[PRUEBA] Verificación de entrega de correo";
    const cuerpo = `Esta es una prueba simple para verificar a qué dirección se entrega el correo.

Destinatario configurado: ${destinatario}
Fecha y hora: ${new Date().toLocaleString()}

Si recibes este correo en tu Gmail personal en lugar del correo misional, confirma que hay un problema de entrega.

Este es un correo de prueba del sistema de reportes misionales.

Configuración actual:
- Destinatario: ${destinatario}
- Sistema: Google Apps Script
- Zona horaria: ${Session.getScriptTimeZone()}`;

    console.log(`Enviando correo de prueba a: ${destinatario}`);
    console.log(`Zona horaria del script: ${Session.getScriptTimeZone()}`);
    
    // Envío simple sin opciones adicionales
    MailApp.sendEmail(destinatario, asunto, cuerpo);
    
    console.log("Correo de prueba enviado exitosamente");
    console.log("IMPORTANTE: Verifica si el correo llega a jpmarichal@train.missionary.org o a jpmarichal@gmail.com");
    
    return {
      exito: true,
      destinatario: destinatario,
      mensaje: "Revisa AMBOS correos (misional y personal) para verificar dónde llegó"
    };
    
  } catch (error) {
    console.error("Error enviando correo de prueba:", error);
    return {
      exito: false,
      error: error.toString()
    };
  }
}

/**
 * Función de prueba para verificar las cuentas y configuración de usuario
 */
function verificarConfiguracionUsuario() {
  console.log("=== VERIFICACIÓN DE CONFIGURACIÓN DE USUARIO ===");
  
  try {
    // Información básica que no requiere permisos especiales
    const zonaHoraria = Session.getScriptTimeZone();
    const locale = Session.getActiveUserLocale();
    
    console.log(`Zona horaria: ${zonaHoraria}`);
    console.log(`Locale: ${locale}`);
    
    // Intentar obtener información de usuario si los permisos lo permiten
    try {
      const usuarioActivo = Session.getActiveUser().getEmail();
      const usuarioEfectivo = Session.getEffectiveUser().getEmail();
      console.log(`Usuario activo: ${usuarioActivo}`);
      console.log(`Usuario efectivo: ${usuarioEfectivo}`);
    } catch (userError) {
      console.log("No se pudieron obtener datos de usuario (permisos insuficientes)");
      console.log("Esto es normal y no afecta el funcionamiento del sistema");
    }
    
    console.log("\nDestinatarios configurados:");
    REPORTES_PDF_CONFIG.destinatarios.forEach((email, index) => {
      console.log(`${index + 1}. ${email}`);
    });
    
    console.log(`\nCorreo misional configurado: ${CORREO_MISIONAL}`);
    console.log(`Correo personal configurado: ${CORREO_PERSONAL}`);
    console.log(`Remitente configurado: ${REPORTES_PDF_CONFIG.correo.correoRemitente}`);
    console.log(`Nombre remitente: ${REPORTES_PDF_CONFIG.correo.remitente}`);
    
    return {
      zonaHoraria: zonaHoraria,
      destinatarios: REPORTES_PDF_CONFIG.destinatarios,
      correoMisional: CORREO_MISIONAL,
      correoPersonal: CORREO_PERSONAL,
      configuracionCompleta: true
    };
    
  } catch (error) {
    console.error("Error verificando configuración:", error);
    return {
      error: error.toString()
    };
  }
}

/**
 * Función de verificación simplificada sin permisos sensibles
 */
function verificarConfiguracionSimple() {
  console.log("=== VERIFICACIÓN SIMPLE DE CONFIGURACIÓN ===");
  
  console.log("Destinatarios configurados:");
  REPORTES_PDF_CONFIG.destinatarios.forEach((email, index) => {
    console.log(`${index + 1}. ${email}`);
  });
  
  console.log(`\nCorreo misional configurado: ${CORREO_MISIONAL}`);
  console.log(`Correo personal configurado: ${CORREO_PERSONAL}`);
  console.log(`Remitente configurado: ${REPORTES_PDF_CONFIG.correo.correoRemitente}`);
  console.log(`Nombre remitente: ${REPORTES_PDF_CONFIG.correo.remitente}`);
  console.log(`Zona horaria: ${Session.getScriptTimeZone()}`);
  
  // Verificar que todas las configuraciones están presentes
  const configuracionCompleta = 
    REPORTES_PDF_CONFIG.destinatarios.length > 0 &&
    CORREO_MISIONAL &&
    REPORTES_PDF_CONFIG.correo.correoRemitente &&
    REPORTES_PDF_CONFIG.spreadsheetIds.branchInAGlance &&
    REPORTES_PDF_CONFIG.spreadsheetIds.reporteMisionalConcentrado;
  
  console.log(`\nConfiguración completa: ${configuracionCompleta ? 'SÍ' : 'NO'}`);
  
  return {
    destinatarios: REPORTES_PDF_CONFIG.destinatarios,
    correoMisional: CORREO_MISIONAL,
    correoPersonal: CORREO_PERSONAL,
    configuracionCompleta: configuracionCompleta
  };
}

/**
 * Función para actualizar configuración de destinatarios (uso administrativo)
 * @param {Object} nuevosDestinatarios - Objeto con la nueva configuración de liderazgo
 */
function actualizarDestinatarios(nuevosDestinatarios) {
  // Esta función permite actualizar los destinatarios dinámicamente
  // Los cambios son temporales, para cambios permanentes editar Config.js
  
  if (nuevosDestinatarios.presidente?.email) {
    REPORTES_PDF_CONFIG.liderazgoRama.presidente.email = nuevosDestinatarios.presidente.email;
    REPORTES_PDF_CONFIG.liderazgoRama.presidente.nombre = nuevosDestinatarios.presidente.nombre || REPORTES_PDF_CONFIG.liderazgoRama.presidente.nombre;
  }
  
  if (nuevosDestinatarios.primerConsejero?.email) {
    REPORTES_PDF_CONFIG.liderazgoRama.primerConsejero.email = nuevosDestinatarios.primerConsejero.email;
    REPORTES_PDF_CONFIG.liderazgoRama.primerConsejero.nombre = nuevosDestinatarios.primerConsejero.nombre || REPORTES_PDF_CONFIG.liderazgoRama.primerConsejero.nombre;
  }
  
  if (nuevosDestinatarios.segundoConsejero?.email) {
    REPORTES_PDF_CONFIG.liderazgoRama.segundoConsejero.email = nuevosDestinatarios.segundoConsejero.email;
    REPORTES_PDF_CONFIG.liderazgoRama.segundoConsejero.nombre = nuevosDestinatarios.segundoConsejero.nombre || REPORTES_PDF_CONFIG.liderazgoRama.segundoConsejero.nombre;
  }
  
  // Actualizar lista de destinatarios
  REPORTES_PDF_CONFIG.destinatarios = [
    REPORTES_PDF_CONFIG.liderazgoRama.presidente.email,
    REPORTES_PDF_CONFIG.liderazgoRama.primerConsejero.email,
    REPORTES_PDF_CONFIG.liderazgoRama.segundoConsejero.email
  ];
  
  console.log("Destinatarios actualizados:", REPORTES_PDF_CONFIG.destinatarios);
  return REPORTES_PDF_CONFIG.destinatarios;
}

/**
 * Cambia entre modo prueba (solo Presidente Marichal) y modo producción (todo el liderazgo)
 * @param {boolean} modoPrueba - true para modo prueba, false para producción
 */
function cambiarModoEnvio(modoPrueba = true) {
  if (modoPrueba) {
    // Modo prueba: solo Presidente Marichal
    REPORTES_PDF_CONFIG.destinatarios = ["jpmarichal@train.missionary.org"];
    console.log("MODO PRUEBA ACTIVADO - Solo Presidente Marichal recibirá correos");
  } else {
    // Modo producción: todo el liderazgo
    REPORTES_PDF_CONFIG.destinatarios = [
      REPORTES_PDF_CONFIG.liderazgoRama.presidente.email,      // Presidente Alvarez
      REPORTES_PDF_CONFIG.liderazgoRama.primerConsejero.email, // Presidente Marichal
      REPORTES_PDF_CONFIG.liderazgoRama.segundoConsejero.email // Presidente Molina
    ];
    console.log("MODO PRODUCCIÓN ACTIVADO - Todo el liderazgo recibirá correos");
  }
  
  console.log("Destinatarios actuales:", REPORTES_PDF_CONFIG.destinatarios);
  return {
    modo: modoPrueba ? "PRUEBA" : "PRODUCCIÓN",
    destinatarios: REPORTES_PDF_CONFIG.destinatarios.length,
    lista: REPORTES_PDF_CONFIG.destinatarios
  };
}

/**
 * Función de prueba que muestra el estado actual de destinatarios
 */
function verificarEstadoDestinatarios() {
  console.log("=== ESTADO ACTUAL DE DESTINATARIOS ===");
  console.log("Destinatarios configurados:", REPORTES_PDF_CONFIG.destinatarios);
  console.log("Total de destinatarios:", REPORTES_PDF_CONFIG.destinatarios.length);
  
  // Determinar si está en modo prueba
  const soloPrueba = REPORTES_PDF_CONFIG.destinatarios.length === 1 && 
                     REPORTES_PDF_CONFIG.destinatarios[0] === "jpmarichal@train.missionary.org";
  
  console.log("Modo actual:", soloPrueba ? "PRUEBA" : "PRODUCCIÓN");
  
  // Mostrar saludos que se generarían
  console.log("\n=== SALUDOS QUE SE GENERARÍAN ===");
  REPORTES_PDF_CONFIG.destinatarios.forEach(email => {
    const saludo = obtenerSaludoPersonalizado(email);
    console.log(`${email} → "Estimado ${saludo}"`);
  });
  
  return {
    modo: soloPrueba ? "PRUEBA" : "PRODUCCIÓN",
    destinatarios: REPORTES_PDF_CONFIG.destinatarios,
    totalDestinatarios: REPORTES_PDF_CONFIG.destinatarios.length
  };
}
