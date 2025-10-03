/**
 * SCRIPT DE ACTUALIZACIÓN DE "BRANCH IN A GLANCE"
 * 
 * Este script actualiza automáticamente la hoja "Branch in a Glance" con
 * información resumida de fechas CCM por distrito misional.
 * 
 * FUNCIÓN:
 * - Extrae datos de fechas CCM desde la base de datos MySQL
 * - Actualiza la hoja Branch in a Glance con información por distrito
 * - Calcula totales de misioneros por distrito
 * - Usa vista optimizada para consultas eficientes
 * 
 * DATOS ACTUALIZADOS:
 * - Primera generación por distrito
 * - Fecha de primera llegada al CCM
 * - Fecha de última salida del CCM
 * - Total de misioneros por distrito
 * 
 * CONFIGURACIÓN:
 * - Base de datos: dbConfig (Config.js)
 * - Hoja destino: sheetConfigBranchInAGlance (Config.js)
 * - Rama: RAMA (Config.js)
 * 
 * USO:
 * - Ejecutar actualizarFechasCCM() manualmente o con trigger programado
 * 
 * @author CCM Scripts
 * @version 2.0
 */

// Las variables de configuración están centralizadas en Config.js

/**
 * Actualiza la hoja Branch in a Glance con datos de fechas CCM por distrito
 * Conecta a la base de datos y actualiza información resumida
 */
function actualizarFechasCCM() {
  let conn = null;
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    Logger.log("✅ Conexión a la base de datos exitosa.");

    const spreadsheet = SpreadsheetApp.openById(sheetConfigBranchInAGlance.spreadsheetId);
    const sheet = spreadsheet.getSheetByName(sheetConfigBranchInAGlance.sheetName);
    if (!sheet) throw new Error(`No se encontró la hoja "${sheetConfigBranchInAGlance.sheetName}".`);

    // Obtener todos los datos de una sola vez usando la vista optimizada
    const sql = `
      SELECT 
        Distrito,
        Primera_Generacion as Generacion,
        Primera_CCM_llegada as CCM_llegada,
        Ultima_CCM_salida as CCM_salida,
        Total_Misioneros
      FROM vwFechasCCMPorDistrito
      WHERE Rama = ${RAMA}
      ORDER BY Distrito
    `;

    Logger.log("📋 Obteniendo datos de todos los distritos con una sola consulta...");
    const stmt = conn.createStatement();
    const results = stmt.executeQuery(sql);
    
    // Crear mapa de datos por distrito
    const datosPorDistrito = {};
    while (results.next()) {
      const distrito = results.getString('Distrito');
      datosPorDistrito[distrito] = {
        Generacion: results.getDate('Generacion'),        // Usar getDate en lugar de getTimestamp
        CCM_llegada: results.getDate('CCM_llegada'),      // Usar getDate en lugar de getTimestamp  
        CCM_salida: results.getDate('CCM_salida'),        // Usar getDate en lugar de getTimestamp
        total: results.getInt('Total_Misioneros')
      };
      Logger.log(`📋 Distrito ${distrito}: Gen=${results.getDate('Generacion')}, Llegada=${results.getDate('CCM_llegada')}, Salida=${results.getDate('CCM_salida')}, Total=${results.getInt('Total_Misioneros')}`);
    }
    results.close();
    stmt.close();

    Logger.log(`📊 Datos obtenidos para ${Object.keys(datosPorDistrito).length} distritos`);
    Logger.log(`📊 Distritos encontrados: ${Object.keys(datosPorDistrito).join(', ')}`);

    // Llenar las celdas usando los datos obtenidos
    for (const distrito in sheetConfigBranchInAGlance.distritos) {
      const fila = sheetConfigBranchInAGlance.distritos[distrito];
      const datosDistrito = datosPorDistrito[distrito];

      Logger.log(`🔍 Procesando distrito ${distrito} (fila ${fila})`);
      Logger.log(`🔍 Datos encontrados: ${datosDistrito ? 'SÍ' : 'NO'}`);

      if (datosDistrito) {
        // Llenar fechas
        for (const campo in sheetConfigBranchInAGlance.campos) {
          const columna = sheetConfigBranchInAGlance.campos[campo];
          const celda = `${columna}${fila}`;
          const targetRange = sheet.getRange(celda);

          // Convertir fecha SQL a JavaScript
          const fechaSql = datosDistrito[campo];
          if (fechaSql) {
            // Si fechaSql es una fecha válida
            let fechaJs;
            if (fechaSql instanceof Date) {
              fechaJs = fechaSql;
            } else {
              // Convertir de timestamp SQL a Date de JavaScript
              fechaJs = new Date(fechaSql.getTime());
            }
            
            targetRange.setValue(fechaJs);
            targetRange.setNumberFormat("dd-mmm-yyyy");
            Logger.log(`📌 ${campo} para distrito ${distrito} → ${celda}: ${fechaJs.toDateString()}`);
          } else {
            targetRange.setValue("");
            Logger.log(`⚠️ No se encontró ${campo} para distrito ${distrito} (valor null/undefined).`);
          }
        }

        // Llenar total de misioneros
        const celdaTotal = `${sheetConfigBranchInAGlance.columnaTotal}${fila}`;
        const targetRangeTotal = sheet.getRange(celdaTotal);
        
        // Verificar si hay total de misioneros
        if (datosDistrito.total > 0) {
          targetRangeTotal.setValue(datosDistrito.total);
          Logger.log(`📊 Total misioneros distrito ${distrito} → ${celdaTotal}: ${datosDistrito.total}`);
        } else {
          targetRangeTotal.setValue("");
          Logger.log(`📊 Total misioneros distrito ${distrito} → ${celdaTotal}: vacío (0 misioneros)`);
        }
      } else {
        // No hay datos para este distrito - limpiar celdas
        Logger.log(`⚠️ No se encontraron datos para distrito ${distrito}`);
        
        // Limpiar fechas
        for (const campo in sheetConfigBranchInAGlance.campos) {
          const columna = sheetConfigBranchInAGlance.campos[campo];
          const celda = `${columna}${fila}`;
          sheet.getRange(celda).setValue("");
        }
        
        // Limpiar total
        const celdaTotal = `${sheetConfigBranchInAGlance.columnaTotal}${fila}`;
        sheet.getRange(celdaTotal).setValue("");
      }
    }

  } catch (e) {
    Logger.log(`❌ Error: ${e.message}`);
  } finally {
    if (conn) {
      conn.close();
      Logger.log("🔌 Conexión cerrada.");
    }
  }
}
