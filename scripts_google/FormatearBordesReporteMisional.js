/**
 * SCRIPT DE FORMATEO DE BORDES PARA REPORTE MISIONAL
 * 
 * Este script aplica formateo automático de bordes a los reportes misionales
 * para mejorar la legibilidad y presentación de los datos.
 * 
 * FUNCIÓN:
 * - Aplica bordes finos tipo grid a toda la tabla
 * - Agrega bordes gruesos para separar secciones importantes
 * - Separa visualmente los diferentes distritos con bordes gruesos
 * - Formatea automáticamente el encabezado
 * 
 * CARACTERÍSTICAS:
 * - Detecta automáticamente cambios de distrito
 * - Limpia formateo anterior antes de aplicar nuevo
 * - Trabaja con la hoja activa actual
 * 
 * USO:
 * - Ejecutar aplicarBordesDistritos() en la hoja que necesita formateo
 * - Ideal para usar después de consolidar reportes
 * 
 * @author CCM Scripts
 * @version 2.0
 */

/**
 * Aplica formateo de bordes automático a la hoja activa
 * Separa visualmente los distritos y mejora la presentación de datos
 */
function aplicarBordesDistritos() {
  const hoja = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  const lastRow = hoja.getLastRow();
  if (lastRow < 2) return;

  const rangoCompleto = hoja.getRange("A1:K" + lastRow);
  const rangoEncabezado = hoja.getRange("A1:K1");
  const datosDistritos = hoja.getRange("B2:B" + lastRow).getValues(); // Columna de distrito desde fila 2

  // LIMPIAR todos los bordes anteriores
  rangoCompleto.setBorder(false, false, false, false, false, false);

  // APLICAR bordes finos (tipo grid) a toda la tabla
  rangoCompleto.setBorder(true, true, true, true, true, true, "black", SpreadsheetApp.BorderStyle.SOLID);

  // APLICAR borde grueso EXTERIOR a toda la tabla
  rangoCompleto.setBorder(true, true, true, true, null, null, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // APLICAR borde grueso INFERIOR al encabezado
  rangoEncabezado.setBorder(null, null, true, null, null, null, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // APLICAR borde grueso INFERIOR entre bloques de distrito
  for (let i = 1; i < datosDistritos.length; i++) {
    if (datosDistritos[i][0] !== datosDistritos[i - 1][0]) {
      hoja.getRange("A" + (i + 1) + ":K" + (i + 1))
        .setBorder(null, null, true, null, null, null, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
    }
  }

  // REFUERZO del borde inferior para el último distrito
  if (lastRow > 1 && datosDistritos.length > 0) {
    hoja.getRange("A" + lastRow + ":K" + lastRow)
      .setBorder(null, null, true, null, null, null, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  }
}