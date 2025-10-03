/**
 * SCRIPT DE EXTRACCIÓN Y SINCRONIZACIÓN DE DATOS MISIONALES
 * 
 * Este script automatiza la extracción de datos desde archivos Excel almacenados
 * en Google Drive y los sincroniza con la base de datos MySQL del CCM.
 * 
 * FUNCIÓN PRINCIPAL:
 * - Procesa archivos Excel de generaciones de misioneros desde Google Drive
 * - Extrae datos usando SheetJS para máxima compatibilidad
 * - Sincroniza datos con tabla ccm_generaciones en MySQL
 * - Manejo inteligente de actualizaciones e inserciones
 * 
 * CARACTERÍSTICAS:
 * - Sistema de reinicio automático para evitar timeouts
 * - Procesamiento por lotes para optimización
 * - Validación de datos y manejo de errores robusto
 * - Soporte para múltiples formatos de Excel
 * - Sistema de continuación automática para procesos largos
 * 
 * CONFIGURACIÓN:
 * - Base de datos: dbConfig (Config.js)
 * - Carpeta fuente: ID_CARPETA_GENERACIONES (Config.js)
 * 
 * FUNCIONES PRINCIPALES:
 * - sincronizarExcelAMySQL(): Función principal de sincronización
 * - procesarCarpetasConSheetJS(): Procesamiento de carpetas y archivos
 * - sincronizarDatosConMySQL(): Sincronización con base de datos
 * 
 * USO:
 * - Ejecutar sincronizarExcelAMySQL() para sincronización completa
 * - Configurar trigger para ejecución automática periódica
 * 
 * @author CCM Scripts
 * @version 3.0
 */

// --- CONFIGURACIÓN ---
// Las variables de configuración están centralizadas en Config.js
// ----------------

/**
 * Función principal que sincroniza datos desde Google Drive a MySQL
 * Adaptada para usar las convenciones de Laravel con la nueva tabla ccm_generaciones
 */
function sincronizarExcelAMySQL() {
  const scriptProperties = PropertiesService.getScriptProperties();
  const startTime = Date.now();
  let conn;

  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    // Configurar la conexión para evitar bloqueos
    conn.setAutoCommit(true); // Cambiar a true para commits automáticos
    
    // Configurar timeout para evitar bloqueos largos
    const stmt = conn.createStatement();
    stmt.execute("SET SESSION innodb_lock_wait_timeout = 30");
    stmt.execute("SET SESSION lock_wait_timeout = 30");
    stmt.close();
    
    Logger.log("✅ Conexión a MySQL exitosa.");
    
    const carpetaRaiz = DriveApp.getFolderById(ID_CARPETA_GENERACIONES);
    procesarCarpetasConSheetJS(conn, carpetaRaiz, scriptProperties, startTime);

  } catch (e) {
    Logger.log(`❌ ERROR CRÍTICO: ${e.toString()}\nStack: ${e.stack}`);
    if (conn) {
      try {
        conn.rollback();
      } catch (rollbackError) {
        Logger.log(`⚠️ Error en rollback: ${rollbackError.toString()}`);
      }
    }
  } finally {
    if (conn && !conn.isClosed()) {
      try {
        conn.close();
        Logger.log("🔌 Conexión cerrada correctamente.");
      } catch (closeError) {
        Logger.log(`⚠️ Error al cerrar conexión: ${closeError.toString()}`);
      }
    }
  }
}

function procesarCarpetasConSheetJS(conn, carpetaRaiz, scriptProperties, startTime) {
    const continuationToken = scriptProperties.getProperty('continuationToken');
    let carpetasDeFecha = continuationToken ?
        DriveApp.continueFolderIterator(continuationToken) :
        carpetaRaiz.getFolders();

    while (carpetasDeFecha.hasNext()) {
        if ((Date.now() - startTime) / 1000 > 280) {
            scriptProperties.setProperty('continuationToken', carpetasDeFecha.getContinuationToken());
            crearDisparadorParaContinuar();
            Logger.log("⏳ Pausando por límite de tiempo. Se reanudará en 5 minutos.");
            return;
        }

        const carpetaFecha = carpetasDeFecha.next();
        const archivosExcel = carpetaFecha.getFilesByType(MimeType.MICROSOFT_EXCEL);
        
        while (archivosExcel.hasNext()) {
            const archivo = archivosExcel.next();
            const fileId = archivo.getId();
            
            try {
                const lastUpdated = archivo.getLastUpdated().toISOString();
                if (scriptProperties.getProperty(fileId) === lastUpdated) continue;

                Logger.log(`🔄 Procesando archivo: ${archivo.getName()}`);
                
                const signedBytes = archivo.getBlob().getBytes();
                const unsignedBytes = signedBytes.map(b => (b < 0) ? b + 256 : b);
                const workbook = XLSX.read(unsignedBytes, {type: "array", cellDates:true});

                const sheetName = workbook.SheetNames[0];
                const data = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], {header: 1});
                
                if (data.length < 2) continue;
                data.shift();
                
                const idsEnExcel = data.map(row => row[0]).filter(id => id);
                if (idsEnExcel.length === 0) continue;
                
                const idsExistentes = chequearIDsExistentes(conn, idsEnExcel);
                const filasNuevas = data.filter(row => row[0] && !idsExistentes.has(row[0]));

                if (filasNuevas.length > 0) {
                    insertarFilasEnLote(conn, filasNuevas);
                    Logger.log(`✔️ Se insertaron ${filasNuevas.length} registros desde ${archivo.getName()}.`);
                }
                scriptProperties.setProperty(fileId, lastUpdated);
            
            } catch(e) {
                Logger.log(`⚠️ Error al procesar el archivo ${archivo.getName()}: ${e.message}. Omitiendo y continuando con el siguiente.`);
            }
        }
    }

    Logger.log("🎉 Sincronización completa. Limpiando estado.");
    scriptProperties.deleteProperty('continuationToken');
    eliminarDisparadores();
}


/**
 * Inserta filas en lote usando las convenciones de Laravel
 * Mapea los campos originales a los nuevos nombres de columna
 * Procesa en lotes pequeños para evitar bloqueos
 */
function insertarFilasEnLote(conn, filasNuevas) {
  const sql = `INSERT INTO ccm_generaciones (
    id, id_distrito, tipo, rama, distrito, pais, numero_lista, numero_companerismo,
    tratamiento, nombre_misionero, companero, mision_asignada, estaca, hospedaje,
    foto, fecha_llegada, fecha_salida, fecha_generacion, comentarios, investido,
    fecha_nacimiento, foto_tomada, pasaporte, folio_pasaporte, fm, ipad, closet,
    llegada_secundaria, pday, host, tres_semanas, device, correo_misional,
    correo_personal, fecha_presencial, activo, created_at, updated_at
  ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`;
  
  const BATCH_SIZE = 50; // Procesar en lotes de 50 registros
  const totalFilas = filasNuevas.length;
  let procesadas = 0;
  
  Logger.log(`📦 Procesando ${totalFilas} registros en lotes de ${BATCH_SIZE}...`);
  
  for (let i = 0; i < totalFilas; i += BATCH_SIZE) {
    const lote = filasNuevas.slice(i, i + BATCH_SIZE);
    const stmt = conn.prepareStatement(sql);
    
    try {
      const ahora = new Date();
      const timestamp = Jdbc.newTimestamp(ahora.getTime());

      for (const row of lote) {
        // Mapear campos según el índice del Excel original
        setIntegerOrNull(stmt, 1, row[0]);          // id (ID)
        stmt.setString(2, row[1] || null);          // id_distrito (iddistric)
        stmt.setString(3, row[2] || null);          // tipo (Tipo)
        setIntegerOrNull(stmt, 4, row[3]);          // rama (Rama)
        stmt.setString(5, row[4] || null);          // distrito (Distrito)
        stmt.setString(6, row[5] || null);          // pais (Pais)
        setIntegerOrNull(stmt, 7, row[6]);          // numero_lista (Numero_de_lista)
        setIntegerOrNull(stmt, 8, row[7]);          // numero_companerismo (Numero_de_companerismo)
        stmt.setString(9, null);                    // tratamiento (dejar en blanco)
        stmt.setString(10, row[8] || null);         // nombre_misionero (Nombre_del_misionero)
        stmt.setString(11, row[9] || null);         // companero (Companero)
        stmt.setString(12, row[10] || null);        // mision_asignada (Mision_asignada)
        stmt.setString(13, row[11] || null);        // estaca (Estaca)
        stmt.setString(14, row[12] || null);        // hospedaje (Hospedaje)
        stmt.setString(15, row[13] || null);        // foto (foto)
        setDateOrNull(stmt, 16, row[14]);           // fecha_llegada (llego)
        setDateOrNull(stmt, 17, row[15]);           // fecha_salida (salida)
        setDateOrNull(stmt, 18, row[16]);           // fecha_generacion (Generacion)
        stmt.setString(19, row[17] || null);        // comentarios (Comentarios)
        setBooleanWithDefault(stmt, 20, row[18], false); // investido (Investido)
        setDateOrNull(stmt, 21, row[19]);           // fecha_nacimiento (Cumpleanos)
        setBooleanWithDefault(stmt, 22, row[20], false); // foto_tomada (FotoN)
        setBooleanWithDefault(stmt, 23, row[21], false); // pasaporte (Pasaporte)
        stmt.setString(24, row[22] || null);        // folio_pasaporte (Folio_P)
        stmt.setString(25, row[23] || null);        // fm (FM)
        setBooleanWithDefault(stmt, 26, row[24], false); // ipad (iPad)
        stmt.setString(27, row[25] || null);        // closet (Closet)
        stmt.setString(28, row[26] || null);        // llegada_secundaria (llego2)
        stmt.setString(29, row[27] || null);        // pday (Pday)
        setBooleanWithDefault(stmt, 30, row[28], false); // host (Host)
        setBooleanWithDefault(stmt, 31, row[29], false); // tres_semanas (tres_semanas)
        setBooleanWithDefault(stmt, 32, row[30], false); // device (Device)
        stmt.setString(33, row[31] || null);        // correo_misional (Correo_Misional)
        stmt.setString(34, row[32] || null);        // correo_personal (Correo_Personal)
        setFechaPresencialOrNull(stmt, 35, row[33]); // fecha_presencial (Fecha_Presencial)
        stmt.setBoolean(36, true);                  // activo (siempre true para registros nuevos)
        stmt.setTimestamp(37, timestamp);           // created_at
        stmt.setTimestamp(38, timestamp);           // updated_at
        
        stmt.addBatch();
      }
      
      // Ejecutar el lote actual
      const resultado = stmt.executeBatch();
      procesadas += lote.length;
      
      Logger.log(`✅ Lote ${Math.floor(i/BATCH_SIZE) + 1}: ${lote.length} registros insertados (${procesadas}/${totalFilas})`);
      
    } catch (batchError) {
      Logger.log(`❌ Error en lote ${Math.floor(i/BATCH_SIZE) + 1}: ${batchError.toString()}`);
      throw batchError;
    } finally {
      stmt.close();
    }
  }
  
  Logger.log(`✅ ${procesadas} registros insertados exitosamente en total`);
}


// --- FUNCIONES AUXILIARES ---

function setIntegerOrNull(stmt, parameterIndex, value) {
  if (value === null || value === undefined || value === '') {
    stmt.setNull(parameterIndex, 4); // JDBC Type code for INTEGER
  } else {
    stmt.setInt(parameterIndex, value);
  }
}

/**
 * Establece un valor de fecha o null en un PreparedStatement
 */
function setDateOrNull(stmt, parameterIndex, value) {
  const fechaNormalizada = normalizarFecha(value);
  if (fechaNormalizada === null) {
    stmt.setNull(parameterIndex, Jdbc.Types.DATE);
  } else {
    stmt.setString(parameterIndex, fechaNormalizada);
  }
}

/**
 * Establece específicamente una fecha presencial (formato D/M/YYYY del Excel)
 */
function setFechaPresencialOrNull(stmt, parameterIndex, value) {
  const fechaNormalizada = normalizarFechaPresencial(value);
  if (fechaNormalizada === null) {
    stmt.setNull(parameterIndex, Jdbc.Types.DATE);
  } else {
    stmt.setString(parameterIndex, fechaNormalizada);
  }
}

/**
 * Establece un valor booleano o null en un PreparedStatement
 */
function setBooleanOrNull(stmt, parameterIndex, value) {
  if (value === null || value === undefined || value === '') {
    stmt.setNull(parameterIndex, Jdbc.Types.BOOLEAN);
  } else {
    // Convertir diferentes formatos a booleano
    const boolValue = normalizarBooleano(value);
    stmt.setBoolean(parameterIndex, boolValue);
  }
}

/**
 * Establece un valor booleano con valor por defecto (no permite NULL)
 */
function setBooleanWithDefault(stmt, parameterIndex, value, defaultValue) {
  let boolValue;
  
  if (value === null || value === undefined || value === '') {
    boolValue = defaultValue;
  } else {
    boolValue = normalizarBooleano(value);
  }
  
  stmt.setBoolean(parameterIndex, boolValue);
}

/**
 * Verifica qué IDs ya existen en la base de datos
 */
function chequearIDsExistentes(conn, ids) {
  const idsExistentes = new Set();
  if (ids.length === 0) return idsExistentes;
  
  const placeholders = ids.map(() => '?').join(',');
  const stmt = conn.prepareStatement(`SELECT id FROM ccm_generaciones WHERE id IN (${placeholders})`);
  
  ids.forEach((id, index) => stmt.setInt(index + 1, parseInt(id)));
  
  const results = stmt.executeQuery();
  while (results.next()) {
    idsExistentes.add(results.getInt(1));
  }
  
  results.close();
  stmt.close();
  return idsExistentes;
}

function normalizarFecha(valor) {
  if (!valor) return null;
  
  try {
    let fecha;
    
    if (valor instanceof Date) {
      fecha = new Date(valor);
    } else if (typeof valor === 'string') {
      fecha = new Date(valor);
    } else {
      return null;
    }
    
    // Verificar que la fecha sea válida
    if (isNaN(fecha.getTime())) {
      return null;
    }
    
    // Retornar en formato YYYY-MM-DD para MySQL
    return fecha.toISOString().slice(0, 10);
  } catch (e) { 
    Logger.log(`Error al normalizar fecha: ${e.toString()}`);
    return null; 
  }
}

function normalizarCumpleanos(valor) {
  if (!valor || valor === "") return null;
  if (valor instanceof Date) {
    valor.setMinutes(valor.getMinutes() - valor.getTimezoneOffset());
    return valor.toISOString().slice(0, 10);
  }
  const mesMap = {ene:0, feb:1, mar:2, abr:3, may:4, jun:5, jul:6, ago:7, sep:8, oct:9, nov:10, dic:11};
  try {
    const parts = valor.toString().toLowerCase().split('-');
    if (parts.length === 2 && mesMap[parts[1]] !== undefined) {
      const fecha = new Date(2000, mesMap[parts[1]], parseInt(parts[0]));
      fecha.setMinutes(fecha.getMinutes() - fecha.getTimezoneOffset());
      return fecha.toISOString().slice(0, 10);
    }
    return null;
  } catch (e) { return null; }
}

function normalizarGeneracion(valor) {
  if (!valor || valor === "") return null;
  if (valor instanceof Date) {
    valor.setMinutes(valor.getMinutes() - valor.getTimezoneOffset());
    return valor.toISOString().slice(0, 10);
  }
  const mesMap = {ene:0, feb:1, mar:2, abr:3, may:4, jun:5, jul:6, ago:7, sep:8, oct:9, nov:10, dic:11};
  try {
    const parts = valor.toString().toLowerCase().split('-');
    if (parts.length === 3 && mesMap[parts[1]] !== undefined) {
      const anio = parseInt(parts[2]) > 50 ? 1900 + parseInt(parts[2]) : 2000 + parseInt(parts[2]);
      const fecha = new Date(anio, mesMap[parts[1]], parseInt(parts[0]));
      fecha.setMinutes(fecha.getMinutes() - fecha.getTimezoneOffset());
      return fecha.toISOString().slice(0, 10);
    }
    return null;
  } catch (e) { return null; }
}

/**
 * Normaliza específicamente las fechas presenciales que vienen en formato D/M/YYYY del Excel
 * Ejemplo: "3/7/2025" debería ser 3 de julio de 2025, no 7 de marzo
 */
function normalizarFechaPresencial(valor) {
  if (!valor) return null;
  
  try {
    let fecha;
    
    if (valor instanceof Date) {
      fecha = new Date(valor);
    } else if (typeof valor === 'string') {
      const valorStr = valor.toString().trim();
      
      // Verificar si es formato D/M/YYYY o DD/MM/YYYY
      if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(valorStr)) {
        const parts = valorStr.split('/');
        const dia = parseInt(parts[0], 10);
        const mes = parseInt(parts[1], 10) - 1; // Los meses en JavaScript van de 0-11
        const anio = parseInt(parts[2], 10);
        
        // Crear fecha explícitamente como DD/MM/YYYY
        fecha = new Date(anio, mes, dia);
        Logger.log(`🔄 Fecha presencial convertida: "${valorStr}" → Día=${dia}, Mes=${mes+1}, Año=${anio} → ${fecha.toISOString().slice(0, 10)}`);
      } else {
        // Usar parsing normal para otros formatos
        fecha = new Date(valorStr);
      }
    } else {
      return null;
    }
    
    // Verificar que la fecha sea válida
    if (isNaN(fecha.getTime())) {
      Logger.log(`⚠️ Fecha presencial inválida: ${valor}`);
      return null;
    }
    
    // Retornar en formato YYYY-MM-DD para MySQL
    return fecha.toISOString().slice(0, 10);
  } catch (e) { 
    Logger.log(`❌ Error al normalizar fecha presencial: ${e.toString()}`);
    return null; 
  }
}

/**
 * ✅ NUEVA FUNCIÓN: Convierte valores como "VERDADERO", "FALSO", true, false, etc., a boolean.
 */
function normalizarBooleano(valor) {
  if (!valor) return false; // Cubre null, undefined, "", false, 0
  if (typeof valor === 'boolean') return valor;
  
  const lowerVal = valor.toString().toLowerCase().trim();
  const valoresVerdaderos = ['verdadero', 'true', 'si', '1', 'x'];
  
  return valoresVerdaderos.includes(lowerVal);
}

function crearDisparadorParaContinuar() {
  try {
    eliminarDisparadores();
    ScriptApp.newTrigger('sincronizarExcelAMySQL')
        .timeBased()
        .after(5 * 60 * 1000)
        .create();
    Logger.log("✅ Disparador creado para continuar en 5 minutos.");
  } catch (error) {
    Logger.log(`⚠️ No se pudo crear el disparador debido a permisos insuficientes: ${error.message}`);
    Logger.log("💡 Por favor, ejecuta manualmente la función sincronizarExcelAMySQL() más tarde para continuar.");
  }
}

function eliminarDisparadores() {
  try {
    const triggers = ScriptApp.getProjectTriggers();
    for (const trigger of triggers) {
      if (trigger.getHandlerFunction() === 'sincronizarExcelAMySQL') {
        ScriptApp.deleteTrigger(trigger);
      }
    }
    Logger.log("🧹 Disparadores existentes eliminados.");
  } catch (error) {
    Logger.log(`⚠️ No se pudieron eliminar los disparadores debido a permisos insuficientes: ${error.message}`);
    // Continúa sin error, ya que esto no es crítico para la funcionalidad principal
  }
}

/**
 * Ejecuta esta función UNA SOLA VEZ para borrar el historial de archivos procesados
 * y forzar una sincronización completa desde cero.
 */
function reiniciarPropiedadesDelScript() {
  const scriptProperties = PropertiesService.getScriptProperties();
  scriptProperties.deleteAllProperties();
  Logger.log('✅ Propiedades del script eliminadas. El próximo ciclo de sincronización comenzará desde cero.');
}

/**
 * Función de prueba para verificar la conexión con la nueva tabla
 */
function probarConexionLaravel() {
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}`;
    const conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const stmt = conn.createStatement();
    const results = stmt.executeQuery("SELECT COUNT(*) as total FROM ccm_generaciones WHERE activo = 1");
    
    if (results.next()) {
      const total = results.getInt('total');
      Logger.log(`✅ Conexión exitosa con tabla Laravel. Total de registros activos: ${total}`);
    }
    
    results.close();
    stmt.close();
    conn.close();
    
  } catch (e) {
    Logger.log(`❌ Error de conexión: ${e.toString()}`);
  }
}

/**
 * Función para verificar bloqueos activos en la tabla
 */
function verificarBloqueos() {
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}`;
    const conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const stmt = conn.createStatement();
    
    // Verificar procesos bloqueados
    Logger.log("🔍 Verificando bloqueos activos...");
    const processResults = stmt.executeQuery("SHOW PROCESSLIST");
    
    let bloqueos = 0;
    while (processResults.next()) {
      const estado = processResults.getString('State');
      const info = processResults.getString('Info');
      if (estado && (estado.includes('Waiting') || estado.includes('Locked'))) {
        bloqueos++;
        Logger.log(`⚠️ Proceso bloqueado: ${estado} - ${info}`);
      }
    }
    
    if (bloqueos === 0) {
      Logger.log("✅ No se encontraron bloqueos activos.");
    } else {
      Logger.log(`⚠️ Se encontraron ${bloqueos} procesos con posibles bloqueos.`);
    }
    
    processResults.close();
    stmt.close();
    conn.close();
    
  } catch (e) {
    Logger.log(`❌ Error al verificar bloqueos: ${e.toString()}`);
  }
}

/**
 * Función para limpiar conexiones colgadas (úsala con cuidado)
 */
function limpiarConexionesColgadas() {
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}`;
    const conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const stmt = conn.createStatement();
    
    Logger.log("🧹 Buscando conexiones inactivas...");
    const results = stmt.executeQuery(`
      SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO 
      FROM INFORMATION_SCHEMA.PROCESSLIST 
      WHERE USER = '${dbConfig.user}' 
      AND COMMAND = 'Sleep' 
      AND TIME > 300
    `);
    
    const conexionesAMatar = [];
    while (results.next()) {
      const id = results.getInt('ID');
      const tiempo = results.getInt('TIME');
      conexionesAMatar.push({id, tiempo});
    }
    
    if (conexionesAMatar.length > 0) {
      Logger.log(`🔫 Matando ${conexionesAMatar.length} conexiones inactivas...`);
      for (const conexion of conexionesAMatar) {
        try {
          stmt.execute(`KILL ${conexion.id}`);
          Logger.log(`✅ Conexión ${conexion.id} terminada (${conexion.tiempo}s inactiva)`);
        } catch (killError) {
          Logger.log(`⚠️ No se pudo terminar conexión ${conexion.id}: ${killError.message}`);
        }
      }
    } else {
      Logger.log("✅ No se encontraron conexiones inactivas para limpiar.");
    }
    
    results.close();
    stmt.close();
    conn.close();
    
  } catch (e) {
    Logger.log(`❌ Error al limpiar conexiones: ${e.toString()}`);
  }
}

/**
 * Función de prueba para verificar que la normalización de fechas presenciales funciona correctamente
 */
function probarNormalizacionFechaPresencial() {
  Logger.log("🧪 Probando normalización de fechas presenciales...");
  
  const casos = [
    "3/7/2025",    // Debería ser 2025-07-03 (3 de julio)
    "18/3/2025",   // Debería ser 2025-03-18 (18 de marzo)
    "7/7/2025",    // Debería ser 2025-07-07 (7 de julio)
    "15/12/2025",  // Debería ser 2025-12-15 (15 de diciembre)
    new Date(2025, 6, 3), // Ya es fecha de JavaScript (3 de julio)
    "",            // Debería ser null
    null,          // Debería ser null
    "fecha_invalida" // Debería ser null
  ];
  
  casos.forEach((caso, i) => {
    const resultado = normalizarFechaPresencial(caso);
    Logger.log(`📋 Caso ${i + 1}: "${caso}" → ${resultado}`);
  });
  
  Logger.log("✅ Prueba de normalización completada. Revisa los logs para verificar los resultados.");
}