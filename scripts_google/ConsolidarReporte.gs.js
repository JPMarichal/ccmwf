/**
 * SCRIPT DE CONSOLIDACIÓN DE REPORTES MISIONALES
 * 
 * Este script consolida múltiples hojas de reporte misional en una sola hoja
 * para facilitar el análisis y reporte centralizado de datos misionales.
 * 
 * FUNCIÓN:
 * - Lee todas las hojas del libro de origen (configurado en Config.js)
 * - Combina los datos evitando duplicar encabezados
 * - Escribe el resultado en la hoja de destino especificada
 * 
 * CONFIGURACIÓN:
 * - Hoja origen: ID_HOJA_ORIGEN_REPORTE (Config.js)
 * - Hoja destino: NOMBRE_HOJA_DESTINO_REPORTE (Config.js)
 * 
 * USO:
 * - Ejecutar consolidarReporteMisional() manualmente o con trigger
 * - Asegurarse de que la hoja activa contiene la hoja de destino
 * 
 * @author CCM Scripts
 * @version 2.0
 */

/**
 * Verifica si una fila contiene datos válidos de un reporte misional
 * @param {Array} fila - Array con los valores de la fila
 * @returns {boolean} - true si la fila tiene datos válidos
 */
function esFilaValidaReporteMisional(fila) {
  if (!fila || fila.length === 0) return false;
  
  // Verificar que no sea una fila de encabezado duplicado
  const primeraColumna = String(fila[0] || "").trim().toLowerCase();
  const segundaColumna = String(fila[1] || "").trim().toLowerCase();
  
  // Filtrar encabezados duplicados
  if ((primeraColumna === "14" || primeraColumna === "") && 
      (segundaColumna === "distrito" || segundaColumna === "district")) {
    return false;
  }
  
  // Verificar si la fila tiene algún contenido real
  const tieneContenido = fila.some(celda => {
    if (celda === null || celda === undefined) return false;
    const valorStr = String(celda).trim();
    // Considerar válido si no está vacío y no es solo ceros
    return valorStr !== "" && valorStr !== "0" && valorStr !== "00";
  });
  
  return tieneContenido;
}

/**
 * Consolida múltiples hojas de reporte misional en una sola hoja de destino
 * Limpia la hoja destino antes de consolidar los nuevos datos
 * Filtrar filas vacías y sin datos válidos de reportes misionales
 */
function consolidarReporteMisional() {
  // Las variables de configuración están centralizadas en Config.js
  const hojaDestino = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(NOMBRE_HOJA_DESTINO_REPORTE);
  hojaDestino.clearContents(); // Limpia antes de copiar datos nuevos

  const libroOrigen = SpreadsheetApp.openById(ID_HOJA_ORIGEN_REPORTE);
  const hojasOrigen = libroOrigen.getSheets();

  let filaActual = 1;
  let encabezadoCopiado = false;

  hojasOrigen.forEach(hoja => {
    const datos = hoja.getDataRange().getValues();
    if (datos.length <= 1) return; // Omitir si solo tiene encabezado o está vacía

    // Filtrar filas que tienen datos válidos de reporte misional
    const datosConEncabezado = [datos[0]]; // Siempre incluir el encabezado
    
    // Revisar cada fila después del encabezado
    for (let i = 1; i < datos.length; i++) {
      const fila = datos[i];
      
      // Usar la función especializada para validar filas de reporte misional
      if (esFilaValidaReporteMisional(fila)) {
        datosConEncabezado.push(fila);
      }
    }
    
    // Solo procesar si hay filas con contenido real (más que solo el encabezado)
    if (datosConEncabezado.length <= 1) {
      console.log(`⚠️ Omitiendo hoja '${hoja.getName()}': solo contiene encabezado o filas vacías (${datos.length} filas originales, ${datosConEncabezado.length - 1} válidas)`);
      return;
    }

    console.log(`✅ Procesando hoja '${hoja.getName()}': ${datosConEncabezado.length - 1} filas con datos válidos de ${datos.length - 1} filas originales`);

    if (!encabezadoCopiado) {
      hojaDestino.getRange(filaActual, 1, datosConEncabezado.length, datosConEncabezado[0].length).setValues(datosConEncabezado);
      encabezadoCopiado = true;
    } else {
      // Solo copiar las filas de datos (sin encabezado)
      const soloFilasDatos = datosConEncabezado.slice(1);
      if (soloFilasDatos.length > 0) {
        hojaDestino.getRange(filaActual, 1, soloFilasDatos.length, soloFilasDatos[0].length).setValues(soloFilasDatos);
      }
    }

    filaActual += datosConEncabezado.length - (encabezadoCopiado ? 1 : 0);
  });

  aplicarBordesDistritos(); // Ejecuta formateo al finalizar
}

/**
 * FUNCIÓN DE EMERGENCIA: Consolidación SIN filtrado (comportamiento original)
 * Usar temporalmente si el filtrado está causando problemas
 */
function consolidarReporteMisionalSinFiltrado() {
  console.log("🚨 USANDO CONSOLIDACIÓN SIN FILTRADO - VERSIÓN DE EMERGENCIA");
  
  const hojaDestino = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(NOMBRE_HOJA_DESTINO_REPORTE);
  hojaDestino.clearContents();

  const libroOrigen = SpreadsheetApp.openById(ID_HOJA_ORIGEN_REPORTE);
  const hojasOrigen = libroOrigen.getSheets();

  let filaActual = 1;
  let encabezadoCopiado = false;

  hojasOrigen.forEach(hoja => {
    const datos = hoja.getDataRange().getValues();
    console.log(`📋 Procesando hoja '${hoja.getName()}': ${datos.length} filas totales`);
    
    if (datos.length <= 1) {
      console.log(`   ⚠️ Omitida: solo tiene encabezado o está vacía`);
      return;
    }

    if (!encabezadoCopiado) {
      hojaDestino.getRange(filaActual, 1, datos.length, datos[0].length).setValues(datos);
      encabezadoCopiado = true;
      console.log(`   ✅ Primera hoja: copiadas ${datos.length} filas (con encabezado)`);
    } else {
      hojaDestino.getRange(filaActual, 1, datos.length - 1, datos[0].length).setValues(datos.slice(1));
      console.log(`   ✅ Hoja adicional: copiadas ${datos.length - 1} filas (sin encabezado)`);
    }

    filaActual += datos.length - (encabezadoCopiado ? 1 : 0);
  });

  aplicarBordesDistritos();
  console.log("🏁 Consolidación sin filtrado completada");
}

/**
 * Función de prueba para verificar qué hojas y datos se están procesando
 * Útil para debugging del filtrado de filas vacías
 */
function probarConsolidacionReporte() {
  console.log("🔍 INICIANDO PRUEBA DE CONSOLIDACIÓN DE REPORTE");
  
  const libroOrigen = SpreadsheetApp.openById(ID_HOJA_ORIGEN_REPORTE);
  const hojasOrigen = libroOrigen.getSheets();
  
  let totalHojasProcesadas = 0;
  let totalFilasValidas = 0;
  let totalHojasOmitidas = 0;

  console.log(`📊 Total de hojas encontradas: ${hojasOrigen.length}`);

  hojasOrigen.forEach((hoja, indice) => {
    const nombreHoja = hoja.getName();
    const datos = hoja.getDataRange().getValues();
    
    console.log(`\n📋 Hoja ${indice + 1}: "${nombreHoja}"`);
    console.log(`   Total de filas: ${datos.length}`);
    
    if (datos.length <= 1) {
      console.log(`   ⚠️ OMITIDA: Solo tiene encabezado o está vacía`);
      totalHojasOmitidas++;
      return;
    }

    // Contar filas válidas
    let filasValidas = 0;
    for (let i = 1; i < datos.length; i++) {
      if (esFilaValidaReporteMisional(datos[i])) {
        filasValidas++;
      }
    }
    
    if (filasValidas === 0) {
      console.log(`   ⚠️ OMITIDA: No tiene filas válidas de reporte misional`);
      totalHojasOmitidas++;
    } else {
      console.log(`   ✅ PROCESADA: ${filasValidas} filas válidas encontradas`);
      totalHojasProcesadas++;
      totalFilasValidas += filasValidas;
    }
  });

  console.log(`\n📈 RESUMEN:`);
  console.log(`   Hojas procesadas: ${totalHojasProcesadas}`);
  console.log(`   Hojas omitidas: ${totalHojasOmitidas}`);
  console.log(`   Total de filas válidas: ${totalFilasValidas}`);
  
  return {
    hojasProcesadas: totalHojasProcesadas,
    hojasOmitidas: totalHojasOmitidas,
    filasValidas: totalFilasValidas
  };
}

/**
 * Limpia filas vacías o inválidas de la hoja de reporte misional consolidado
 * Útil para limpiar reportes ya generados que tengan filas vacías
 */
function limpiarFilasVaciasReporteConsolidado() {
  console.log("🧹 INICIANDO LIMPIEZA DE FILAS VACÍAS");
  
  const hojaDestino = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(NOMBRE_HOJA_DESTINO_REPORTE);
  
  if (!hojaDestino) {
    console.log(`❌ No se encontró la hoja: ${NOMBRE_HOJA_DESTINO_REPORTE}`);
    return false;
  }
  
  const datos = hojaDestino.getDataRange().getValues();
  console.log(`📊 Total de filas en el reporte: ${datos.length}`);
  
  if (datos.length <= 1) {
    console.log("⚠️ El reporte solo tiene encabezado o está vacío");
    return false;
  }
  
  // Conservar el encabezado y filtrar filas válidas
  const datosLimpios = [datos[0]]; // Encabezado
  let filasEliminadas = 0;
  
  for (let i = 1; i < datos.length; i++) {
    if (esFilaValidaReporteMisional(datos[i])) {
      datosLimpios.push(datos[i]);
    } else {
      filasEliminadas++;
      console.log(`🗑️ Eliminando fila ${i + 1}: [${datos[i].slice(0, 3).join(', ')}...]`);
    }
  }
  
  if (filasEliminadas === 0) {
    console.log("✅ No se encontraron filas vacías para eliminar");
    return true;
  }
  
  // Limpiar la hoja y escribir solo los datos válidos
  hojaDestino.clearContents();
  hojaDestino.getRange(1, 1, datosLimpios.length, datosLimpios[0].length).setValues(datosLimpios);
  
  console.log(`✅ Limpieza completada:`);
  console.log(`   Filas eliminadas: ${filasEliminadas}`);
  console.log(`   Filas conservadas: ${datosLimpios.length - 1} (+ encabezado)`);
  
  // Aplicar formateo después de la limpieza
  aplicarBordesDistritos();
  
  return true;
}

