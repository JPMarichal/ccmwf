// TelegramNotifier.js
// Script para enviar notificaciones a Telegram usando la API del bot

/**
 * Envía un mensaje a un canal de Telegram
 * @param {string} mensaje - El mensaje a enviar
 * @param {Object} config - Configuración opcional del bot (si no se pasa, usa TELEGRAM_CONFIG por defecto)
 * @returns {Object} - Respuesta de la API de Telegram
 */
function enviarMensajeTelegram(mensaje, config = null) {
  try {
    // Usar configuración por defecto si no se proporciona una
    const telegramConfig = config || TELEGRAM_CONFIG;
    
    // Verificar si las notificaciones están habilitadas
    if (!telegramConfig.enabled) {
      console.log("Las notificaciones de Telegram están deshabilitadas");
      return { success: false, message: "Notificaciones deshabilitadas" };
    }
    
    // Verificar que tenemos los datos necesarios
    if (!telegramConfig.botToken || !telegramConfig.chatId) {
      throw new Error("Token del bot o Chat ID no configurados");
    }
    
    // Construir la URL de la API de Telegram
    const url = `https://api.telegram.org/bot${telegramConfig.botToken}/sendMessage`;
    
    // Preparar los datos del mensaje
    const payload = {
      chat_id: telegramConfig.chatId,
      text: mensaje,
      parse_mode: "HTML" // Permite usar formateo HTML básico
    };
    
    // Configurar las opciones de la petición HTTP
    const options = {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      payload: JSON.stringify(payload)
    };
    
    // Enviar la petición a la API de Telegram
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    // Procesar la respuesta
    if (responseCode === 200) {
      const result = JSON.parse(responseText);
      if (result.ok) {
        console.log("Mensaje enviado exitosamente a Telegram");
        return { 
          success: true, 
          messageId: result.result.message_id,
          response: result 
        };
      } else {
        throw new Error(`Error de la API de Telegram: ${result.description}`);
      }
    } else {
      throw new Error(`Error HTTP ${responseCode}: ${responseText}`);
    }
    
  } catch (error) {
    console.error("Error al enviar mensaje a Telegram:", error.toString());
    return { 
      success: false, 
      error: error.toString() 
    };
  }
}



/**
 * Envía un mensaje formateado con información del sistema CCM
 * @param {string} titulo - Título del mensaje
 * @param {string} contenido - Contenido principal del mensaje
 * @param {string} tipo - Tipo de mensaje ('info', 'warning', 'error', 'success')
 */
function enviarNotificacionCCM(titulo, contenido, tipo = 'info') {
  try {
    // Emojis según el tipo de mensaje
    const emojis = {
      'info': 'ℹ️',
      'warning': '⚠️',
      'error': '🚨',
      'success': '✅'
    };
    
    const emoji = emojis[tipo] || emojis['info'];
    
    const mensaje = `${emoji} <b>${titulo}</b>\n\n` +
                   `${contenido}\n\n` +
                   `🕐 ${new Date().toLocaleString('es-ES')}\n` +
                   `🏢 Rama ${RAMA} - CCM Sistema`;
    
    return enviarMensajeTelegram(mensaje);
    
  } catch (error) {
    console.error("Error al enviar notificación CCM:", error.toString());
    return { success: false, error: error.toString() };
  }
}



/**
 * Consulta los próximos misioneros que ingresarán al CCM para una rama específica
 * @param {Object} conn - Conexión a la base de datos MySQL
 * @param {number} rama - Número de rama (por defecto usa RAMA de Config.js)
 * @param {number} diasAdelante - Días hacia adelante para buscar (por defecto 60 días)
 * @returns {Array} - Array de objetos con información de próximos misioneros
 */
function consultarProximosMisionerosCCM(conn, rama = null, diasAdelante = 60) {
  try {
    const ramaConsulta = rama || RAMA;
    const fechaActual = new Date();
    const fechaLimite = new Date();
    fechaLimite.setDate(fechaActual.getDate() + diasAdelante);
    
    // Formatear fechas para MySQL (YYYY-MM-DD)
    const fechaActualStr = fechaActual.toISOString().split('T')[0];
    const fechaLimiteStr = fechaLimite.toISOString().split('T')[0];
    
    // Query corregida usando la vista vwMisioneros con el campo tres_semanas
    const query = `
      SELECT 
        Distrito as distrito,
        RDistrito,
        DATE(CCM_llegada) as fecha_llegada,
        DATE(CCM_salida) as fecha_salida,
        COUNT(*) as cantidad_misioneros,
        CASE WHEN MAX(tres_semanas) = 1 THEN 3 ELSE 6 END as duracion_semanas
      FROM vwMisioneros 
      WHERE Rama = ? 
        AND CCM_llegada IS NOT NULL
        AND CCM_llegada > CURDATE()
        AND (BINARY Status = 'Futuro' OR BINARY Status = 'Virtual' OR BINARY Status = 'CCM')
      GROUP BY Distrito, RDistrito, DATE(CCM_llegada), DATE(CCM_salida)
      ORDER BY fecha_llegada ASC, distrito ASC
    `;
    
    const stmt = conn.prepareStatement(query);
    stmt.setInt(1, ramaConsulta);
    
    const resultSet = stmt.executeQuery();
    const proximosMisioneros = [];
    
    console.log("🔍 Procesando resultados de la consulta...");
    
    while (resultSet.next()) {
      const distrito = resultSet.getString('distrito');
      const rDistrito = resultSet.getString('RDistrito');
      const fechaLlegadaSQL = resultSet.getDate('fecha_llegada');
      const fechaSalidaSQL = resultSet.getDate('fecha_salida');
      const cantidad = resultSet.getInt('cantidad_misioneros');
      const duracionSemanas = resultSet.getInt('duracion_semanas');
      
      // Convertir las fechas JDBC a JavaScript Date estándar
      let fechaLlegada = null;
      let fechaSalida = null;
      
      if (fechaLlegadaSQL) {
        try {
          fechaLlegada = new Date(fechaLlegadaSQL.getTime());
        } catch (error) {
          console.log(`⚠️ Error al convertir fecha de llegada JDBC: ${error.toString()}`);
          fechaLlegada = null;
        }
      }
      
      if (fechaSalidaSQL) {
        try {
          fechaSalida = new Date(fechaSalidaSQL.getTime());
        } catch (error) {
          console.log(`⚠️ Error al convertir fecha de salida JDBC: ${error.toString()}`);
          fechaSalida = null;
        }
      }
      
      console.log(`📅 Registro encontrado - Distrito: ${distrito}, Entrada: ${fechaLlegada ? fechaLlegada.toISOString().split('T')[0] : 'null'}, Salida: ${fechaSalida ? fechaSalida.toISOString().split('T')[0] : 'null'}, Cantidad: ${cantidad}, Duración: ${duracionSemanas} semanas`);
      
      proximosMisioneros.push({
        distrito: distrito,
        rDistrito: rDistrito,
        fechaLlegada: fechaLlegada,
        fechaSalida: fechaSalida,
        cantidad: cantidad,
        duracionSemanas: duracionSemanas
      });
    }
    
    stmt.close();
    console.log(`📊 Encontrados ${proximosMisioneros.length} grupos de próximos misioneros para la rama ${ramaConsulta}`);
    
    return proximosMisioneros;
    
  } catch (error) {
    console.error("❌ Error al consultar próximos misioneros CCM:", error.toString());
    return [];
  }
}

/**
 * Genera un reporte formateado de próximos misioneros para Telegram
 * @param {Array} proximosMisioneros - Array de próximos misioneros desde consultarProximosMisionerosCCM
 * @param {number} rama - Número de rama
 * @returns {string} - Mensaje formateado para Telegram
 */
function generarReporteProximosMisioneros(proximosMisioneros, rama = null) {
  try {
    const ramaReporte = rama || RAMA;
    
    if (!proximosMisioneros || proximosMisioneros.length === 0) {
      return `✅ No hay misioneros programados para ingresar al CCM en las próximas semanas.`;
    }
    
    // Filtrar y validar fechas antes de procesar
    const proximosValidos = proximosMisioneros.filter(grupo => {
      if (!grupo.fechaLlegada) {
        console.log("⚠️ Grupo sin fecha de llegada, omitiendo:", grupo.distrito);
        return false;
      }
      
      try {
        // Verificar si es un objeto Date válido
        if (!(grupo.fechaLlegada instanceof Date)) {
          console.log("⚠️ Fecha no es objeto Date, omitiendo:", grupo.distrito, typeof grupo.fechaLlegada);
          return false;
        }
        
        // Verificar si la fecha es válida
        if (isNaN(grupo.fechaLlegada.getTime())) {
          console.log("⚠️ Fecha inválida encontrada, omitiendo:", grupo.distrito, grupo.fechaLlegada);
          return false;
        }
        
        console.log(`✅ Fecha válida para distrito ${grupo.distrito}: ${grupo.fechaLlegada.toISOString().split('T')[0]}`);
        return true;
      } catch (error) {
        console.log("⚠️ Error al validar fecha, omitiendo:", grupo.distrito, error);
        return false;
      }
    });
    
    if (proximosValidos.length === 0) {
      return `⚠️ Se encontraron datos pero todas las fechas son inválidas.`;
    }
    
    // Calcular totales
    const totalMisioneros = proximosValidos.reduce((sum, grupo) => sum + grupo.cantidad, 0);
    
    // Agrupar por fecha y distrito
    const gruposPorFecha = {};
    proximosValidos.forEach(grupo => {
      try {
        // La fecha ya está validada como objeto Date en el filtro anterior
        const fecha = grupo.fechaLlegada;
        const fechaKey = fecha.toISOString().split('T')[0]; // YYYY-MM-DD
        
        if (!gruposPorFecha[fechaKey]) {
          gruposPorFecha[fechaKey] = [];
        }
        gruposPorFecha[fechaKey].push(grupo);
        
        console.log(`📅 Agrupando distrito ${grupo.distrito} en fecha ${fechaKey}`);
      } catch (error) {
        console.log("⚠️ Error al procesar fecha del grupo:", grupo.distrito, error);
      }
    });
    
    let mensaje = ``;
    
    // Procesar cada fecha
    const fechasOrdenadas = Object.keys(gruposPorFecha).sort();
    
    fechasOrdenadas.forEach(fechaKey => {
      const grupos = gruposPorFecha[fechaKey];
      const fecha = new Date(fechaKey);
      const totalDia = grupos.reduce((sum, grupo) => sum + grupo.cantidad, 0);
      
      // Calcular días desde hoy
      const hoy = new Date();
      const diffTime = fecha - hoy;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      let descripcionTiempo;
      if (diffDays <= 7) {
        descripcionTiempo = "La próxima semana";
      } else if (diffDays <= 14) {
        descripcionTiempo = "En 2 semanas";
      } else if (diffDays <= 21) {
        descripcionTiempo = "En 3 semanas";
      } else if (diffDays <= 30) {
        descripcionTiempo = "Este mes";
      } else {
        descripcionTiempo = `En ${diffDays} días`;
      }
      
      mensaje += `� <b>${descripcionTiempo}</b> (${fecha.toLocaleDateString('es-ES')})\n`;
      mensaje += `� Total: ${totalDia} misioneros\n\n`;
      
      // Mostrar cada distrito
      grupos.forEach(grupo => {
        try {
          mensaje += `   📍 <b>Distrito ${grupo.distrito}</b> (${grupo.rDistrito})\n`;
          mensaje += `   👥 ${grupo.cantidad} misionero${grupo.cantidad > 1 ? 's' : ''}\n`;
          
          // Mostrar duración (3 o 6 semanas)
          if (grupo.duracionSemanas) {
            mensaje += `   ⏱️ Duración: ${grupo.duracionSemanas} semanas\n`;
          }
          
          // Mostrar fechas de entrada y salida
          const fechaEntrada = grupo.fechaLlegada.toLocaleDateString('es-ES');
          mensaje += `   � Entrada: ${fechaEntrada}\n`;
          
          if (grupo.fechaSalida) {
            const fechaSalida = grupo.fechaSalida.toLocaleDateString('es-ES');
            mensaje += `   � Salida: ${fechaSalida}\n\n`;
          } else {
            mensaje += `   📤 Salida: Por definir\n\n`;
          }
          
        } catch (error) {
          console.log("⚠️ Error al procesar grupo individual:", grupo, error);
          mensaje += `   📍 <b>Distrito ${grupo.distrito || 'Desconocido'}</b>\n`;
          mensaje += `   ⚠️ Error al procesar datos\n\n`;
        }
      });
    });
    
    // Remover el último salto de línea extra
    mensaje = mensaje.trim();
    
    return mensaje;
    
  } catch (error) {
    console.error("❌ Error al generar reporte de próximos misioneros:", error.toString());
    return `❌ Error al generar reporte de próximos misioneros: ${error.toString()}`;
  }
}

/**
 * Función principal para notificar próximos misioneros CCM después de extracción de datos
 * Esta función debe ser llamada desde el script "Extraer datos misionales"
 * @param {Object} conn - Conexión activa a la base de datos MySQL
 * @param {number} rama - Número de rama (opcional, usa RAMA por defecto)
 */
function notificarProximosMisionerosCCM(conn, rama = null) {
  try {
    console.log("📋 Generando reporte de próximos misioneros CCM...");
    
    // Consultar próximos misioneros
    const proximosMisioneros = consultarProximosMisionerosCCM(conn, rama);
    
    // Generar mensaje formateado
    const mensajeReporte = generarReporteProximosMisioneros(proximosMisioneros, rama);
    
    // Enviar notificación a Telegram
    const resultado = enviarNotificacionCCM(
      "Próximos Ingresos al CCM", 
      mensajeReporte, 
      'info'
    );
    
    if (resultado.success) {
      console.log("✅ Reporte de próximos misioneros enviado exitosamente a Telegram");
    } else {
      console.error("❌ Error al enviar reporte a Telegram:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en notificarProximosMisionerosCCM:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Consulta los próximos cumpleaños de misioneros para una rama específica
 * Solo incluye cumpleaños de hoy en adelante y estatus Virtual/CCM
 * @param {Object} conn - Conexión a la base de datos MySQL
 * @param {number} rama - Número de rama (por defecto usa RAMA de Config.js)
 * @returns {Array} - Array de objetos con información de próximos cumpleaños
 */
function consultarProximosCumpleanos(conn, rama = null) {
  try {
    const ramaConsulta = rama || RAMA;
    
    // Query usando la vista vwCumpleanosProximos
    // Solo cumpleaños próximos (de hoy en adelante) y estatus Virtual/CCM
    const query = `
      SELECT 
        ID,
        Rama,
        RDistrito,
        Tratamiento,
        Cumpleanios as nombre_misionero,
        Cumple as nueva_edad,
        Status,
        Correo_Misional,
        DATE(CONCAT(
          YEAR(CURDATE()),
          '-',
          LPAD(MONTH(
            (SELECT Fecha_nacimiento FROM vwMisioneros m2 WHERE m2.ID = vcp.ID)
          ), 2, '0'),
          '-',
          LPAD(DAY(
            (SELECT Fecha_nacimiento FROM vwMisioneros m2 WHERE m2.ID = vcp.ID)
          ), 2, '0')
        )) as fecha_cumpleanos_este_ano
      FROM vwCumpleanosProximos vcp
      WHERE Rama = ?
        AND Status IN ('Virtual', 'CCM')
        AND DATE(CONCAT(
          YEAR(CURDATE()),
          '-',
          LPAD(MONTH(
            (SELECT Fecha_nacimiento FROM vwMisioneros m2 WHERE m2.ID = vcp.ID)
          ), 2, '0'),
          '-',
          LPAD(DAY(
            (SELECT Fecha_nacimiento FROM vwMisioneros m2 WHERE m2.ID = vcp.ID)
          ), 2, '0')
        )) >= CURDATE()
      ORDER BY 
        MONTH((SELECT Fecha_nacimiento FROM vwMisioneros m2 WHERE m2.ID = vcp.ID)),
        DAY((SELECT Fecha_nacimiento FROM vwMisioneros m2 WHERE m2.ID = vcp.ID))
    `;
    
    const stmt = conn.prepareStatement(query);
    stmt.setInt(1, ramaConsulta);
    
    const resultSet = stmt.executeQuery();
    const proximosCumpleanos = [];
    
    console.log("🔍 Procesando resultados de próximos cumpleaños...");
    
    while (resultSet.next()) {
      const id = resultSet.getInt('ID');
      const ramaResult = resultSet.getInt('Rama');
      const rDistrito = resultSet.getString('RDistrito');
      const tratamiento = resultSet.getString('Tratamiento');
      const nombreMisionero = resultSet.getString('nombre_misionero');
      const nuevaEdad = resultSet.getInt('nueva_edad');
      const status = resultSet.getString('Status');
      const correoMisional = resultSet.getString('Correo_Misional');
      const fechaCumpleanosSQL = resultSet.getDate('fecha_cumpleanos_este_ano');
      
      // Convertir la fecha JDBC a JavaScript Date
      let fechaCumpleanos = null;
      if (fechaCumpleanosSQL) {
        try {
          fechaCumpleanos = new Date(fechaCumpleanosSQL.getTime());
        } catch (error) {
          console.log(`⚠️ Error al convertir fecha de cumpleaños JDBC: ${error.toString()}`);
          fechaCumpleanos = null;
        }
      }
      
      console.log(`🎂 Cumpleaños encontrado - ${tratamiento}: ${fechaCumpleanos ? fechaCumpleanos.toISOString().split('T')[0] : 'null'}, Edad: ${nuevaEdad}, Status: ${status}`);
      
      proximosCumpleanos.push({
        id: id,
        rama: ramaResult,
        rDistrito: rDistrito,
        tratamiento: tratamiento,
        nombreMisionero: nombreMisionero,
        nuevaEdad: nuevaEdad,
        status: status,
        correoMisional: correoMisional,
        fechaCumpleanos: fechaCumpleanos
      });
    }
    
    stmt.close();
    console.log(`📊 Encontrados ${proximosCumpleanos.length} próximos cumpleaños para la rama ${ramaConsulta}`);
    
    return proximosCumpleanos;
    
  } catch (error) {
    console.error("❌ Error al consultar próximos cumpleaños:", error.toString());
    return [];
  }
}

/**
 * Genera un reporte formateado de próximos cumpleaños para Telegram
 * @param {Array} proximosCumpleanos - Array de próximos cumpleaños desde consultarProximosCumpleanos
 * @param {number} rama - Número de rama
 * @returns {string} - Mensaje formateado para Telegram
 */
function generarReporteProximosCumpleanos(proximosCumpleanos, rama = null) {
  try {
    const ramaReporte = rama || RAMA;
    
    if (!proximosCumpleanos || proximosCumpleanos.length === 0) {
      return `✅ No hay cumpleaños próximos programados para los próximos meses.`;
    }
    
    // Filtrar y validar fechas antes de procesar
    const cumpleanosValidos = proximosCumpleanos.filter(cumpleanos => {
      if (!cumpleanos.fechaCumpleanos) {
        console.log("⚠️ Cumpleaños sin fecha, omitiendo:", cumpleanos.nombreMisionero);
        return false;
      }
      
      try {
        // Verificar si es un objeto Date válido
        if (!(cumpleanos.fechaCumpleanos instanceof Date)) {
          console.log("⚠️ Fecha no es objeto Date, omitiendo:", cumpleanos.nombreMisionero, typeof cumpleanos.fechaCumpleanos);
          return false;
        }
        
        // Verificar si la fecha es válida
        if (isNaN(cumpleanos.fechaCumpleanos.getTime())) {
          console.log("⚠️ Fecha inválida encontrada, omitiendo:", cumpleanos.nombreMisionero, cumpleanos.fechaCumpleanos);
          return false;
        }
        
        console.log(`✅ Fecha válida para ${cumpleanos.nombreMisionero}: ${cumpleanos.fechaCumpleanos.toISOString().split('T')[0]}`);
        return true;
      } catch (error) {
        console.log("⚠️ Error al validar fecha, omitiendo:", cumpleanos.nombreMisionero, error);
        return false;
      }
    });
    
    if (cumpleanosValidos.length === 0) {
      return `⚠️ Se encontraron datos pero todas las fechas son inválidas.`;
    }
    
    // Calcular totales
    const totalMisioneros = cumpleanosValidos.length;
    
    // Agrupar por mes
    const gruposPorMes = {};
    const nombresMeses = {
      1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL', 5: 'MAYO', 6: 'JUNIO',
      7: 'JULIO', 8: 'AGOSTO', 9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE'
    };
    
    cumpleanosValidos.forEach(cumpleanos => {
      try {
        const fecha = cumpleanos.fechaCumpleanos;
        const mes = fecha.getMonth() + 1; // getMonth() devuelve 0-11
        const dia = fecha.getDate();
        
        if (!gruposPorMes[mes]) {
          gruposPorMes[mes] = {};
        }
        
        if (!gruposPorMes[mes][dia]) {
          gruposPorMes[mes][dia] = [];
        }
        
        gruposPorMes[mes][dia].push(cumpleanos);
        
        console.log(`📅 Agrupando ${cumpleanos.nombreMisionero} en mes ${mes}, día ${dia}`);
      } catch (error) {
        console.log("⚠️ Error al procesar fecha del cumpleaños:", cumpleanos.nombreMisionero, error);
      }
    });
    
    // Construir el mensaje con formato similar a la imagen
    let mensaje = `🎊 <b>PRÓXIMOS CUMPLEAÑOS</b>\n`;
    mensaje += `📅 ${new Date().toLocaleDateString('es-ES')}\n`;
    mensaje += `🎯 Ramas: ${ramaReporte}\n\n`;
    
    // Procesar cada mes
    const mesesOrdenados = Object.keys(gruposPorMes).sort((a, b) => parseInt(a) - parseInt(b));
    
    mesesOrdenados.forEach(mes => {
      const nombreMes = nombresMeses[parseInt(mes)];
      const diasDelMes = gruposPorMes[mes];
      
      mensaje += `🗓️ <b>${nombreMes}:</b>\n`;
      
      // Procesar cada día del mes
      const diasOrdenados = Object.keys(diasDelMes).sort((a, b) => parseInt(a) - parseInt(b));
      
      diasOrdenados.forEach(dia => {
        const cumpleanosDelDia = diasDelMes[dia];
        
        // Mostrar cada cumpleaños del día
        cumpleanosDelDia.forEach(cumpleanos => {
          const diaFormateado = dia.toString().padStart(2, '0');
          mensaje += `📅 ${diaFormateado} - ${cumpleanos.tratamiento} (${cumpleanos.nuevaEdad}-CCM)\n`;
        });
      });
      
      mensaje += `\n`;
    });
    
    // Agregar totales al final
    mensaje += `🎯 Total: ${totalMisioneros} misioneros`;
    
    return mensaje;
    
  } catch (error) {
    console.error("❌ Error al generar reporte de próximos cumpleaños:", error.toString());
    return `❌ Error al generar reporte de próximos cumpleaños: ${error.toString()}`;
  }
}

/**
 * Función principal para notificar próximos cumpleaños después de extracción de datos
 * Esta función debe ser llamada desde el script principal o mediante trigger
 * @param {Object} conn - Conexión activa a la base de datos MySQL
 * @param {number} rama - Número de rama (opcional, usa RAMA por defecto)
 */
function notificarProximosCumpleanos(conn, rama = null) {
  try {
    console.log("🎂 Generando reporte de próximos cumpleaños...");
    
    // Consultar próximos cumpleaños
    const proximosCumpleanos = consultarProximosCumpleanos(conn, rama);
    
    // Generar mensaje formateado
    const mensajeReporte = generarReporteProximosCumpleanos(proximosCumpleanos, rama);
    
    // Enviar a Telegram usando el formato específico de CCM Notifications
    const resultado = enviarMensajeTelegram(mensajeReporte);
    
    if (resultado.success) {
      console.log("✅ Reporte de próximos cumpleaños enviado exitosamente a Telegram");
    } else {
      console.error("❌ Error al enviar reporte a Telegram:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en notificarProximosCumpleanos:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Genera un reporte formateado de próximos ingresos al CCM para Telegram
 * con el formato específico de "CCM Notifications"
 * @param {Array} proximosMisioneros - Array de próximos misioneros desde consultarProximosMisionerosCCM
 * @param {number} rama - Número de rama
 * @returns {string} - Mensaje formateado para Telegram
 */
function generarReporteProximosIngresosCCM(proximosMisioneros, rama = null) {
  try {
    const ramaReporte = rama || RAMA;
    
    if (!proximosMisioneros || proximosMisioneros.length === 0) {
      // Mensaje cuando no hay próximos ingresos
      const timestamp = new Date().toLocaleString('es-ES', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
      
      return `📊 <b>Próximos Ingresos al CCM</b>\n\n` +
             `✅ No hay misioneros programados para ingresar al CCM en las próximas semanas.\n\n` +
             `🕐 ${timestamp}\n` +
             `🏢 Rama ${ramaReporte} - CCM Sistema`;
    }
    
    // Filtrar y validar fechas antes de procesar
    const proximosValidos = proximosMisioneros.filter(grupo => {
      if (!grupo.fechaLlegada) {
        console.log("⚠️ Grupo sin fecha de llegada, omitiendo:", grupo.distrito);
        return false;
      }
      
      try {
        if (!(grupo.fechaLlegada instanceof Date)) {
          console.log("⚠️ Fecha no es objeto Date, omitiendo:", grupo.distrito, typeof grupo.fechaLlegada);
          return false;
        }
        
        if (isNaN(grupo.fechaLlegada.getTime())) {
          console.log("⚠️ Fecha inválida encontrada, omitiendo:", grupo.distrito, grupo.fechaLlegada);
          return false;
        }
        
        return true;
      } catch (error) {
        console.log("⚠️ Error al validar fecha, omitiendo:", grupo.distrito, error);
        return false;
      }
    });
    
    if (proximosValidos.length === 0) {
      return `⚠️ Se encontraron datos pero todas las fechas son inválidas.`;
    }
    
    // Calcular totales
    const totalMisioneros = proximosValidos.reduce((sum, grupo) => sum + grupo.cantidad, 0);
    
    // Agrupar por fecha y luego por distrito
    const gruposPorFecha = {};
    proximosValidos.forEach(grupo => {
      try {
        const fecha = grupo.fechaLlegada;
        const fechaKey = fecha.toISOString().split('T')[0]; // YYYY-MM-DD
        
        if (!gruposPorFecha[fechaKey]) {
          gruposPorFecha[fechaKey] = {};
        }
        
        // Agrupar por distrito dentro de cada fecha
        const distritoKey = grupo.distrito;
        if (!gruposPorFecha[fechaKey][distritoKey]) {
          gruposPorFecha[fechaKey][distritoKey] = {
            distrito: grupo.distrito,
            rDistrito: grupo.rDistrito,
            fechaLlegada: grupo.fechaLlegada,
            fechaSalida: grupo.fechaSalida,
            cantidad: 0,
            duracionSemanas: grupo.duracionSemanas
          };
        }
        
        // Sumar misioneros del mismo distrito
        gruposPorFecha[fechaKey][distritoKey].cantidad += grupo.cantidad;
        
        // Tomar la fecha de salida más tardía si hay múltiples registros
        if (grupo.fechaSalida && gruposPorFecha[fechaKey][distritoKey].fechaSalida) {
          if (grupo.fechaSalida > gruposPorFecha[fechaKey][distritoKey].fechaSalida) {
            gruposPorFecha[fechaKey][distritoKey].fechaSalida = grupo.fechaSalida;
          }
        } else if (grupo.fechaSalida) {
          gruposPorFecha[fechaKey][distritoKey].fechaSalida = grupo.fechaSalida;
        }
        
        console.log(`📅 Agrupando distrito ${grupo.distrito} en fecha ${fechaKey}, cantidad: ${grupo.cantidad}, total acumulado: ${gruposPorFecha[fechaKey][distritoKey].cantidad}`);
      } catch (error) {
        console.log("⚠️ Error al procesar fecha del grupo:", grupo.distrito, error);
      }
    });
    
    // Construir el mensaje con formato específico de CCM Notifications
    let mensaje = `📊 <b>Próximos Ingresos al CCM</b>\n\n`;
    
    // Procesar cada fecha
    const fechasOrdenadas = Object.keys(gruposPorFecha).sort();
    
    fechasOrdenadas.forEach(fechaKey => {
      const distritos = gruposPorFecha[fechaKey];
      const fecha = new Date(fechaKey);
      
      // Calcular total de misioneros para esta fecha
      const totalDia = Object.values(distritos).reduce((sum, distrito) => sum + distrito.cantidad, 0);
      
      // Calcular días desde hoy
      const hoy = new Date();
      const diffTime = fecha - hoy;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      let descripcionTiempo;
      if (diffDays <= 7) {
        descripcionTiempo = "La próxima semana";
      } else if (diffDays <= 14) {
        descripcionTiempo = "En 2 semanas";
      } else if (diffDays <= 21) {
        descripcionTiempo = "En 3 semanas";
      } else if (diffDays <= 30) {
        descripcionTiempo = "Este mes";
      } else {
        descripcionTiempo = `En ${diffDays} días`;
      }
      
      // Formato: ◆ La próxima semana (13/8/2025)
      mensaje += `◆ <b>${descripcionTiempo}</b> (${fecha.toLocaleDateString('es-ES')})\n`;
      mensaje += `◆ Total: ${totalDia} misioneros\n\n`;
      
      // Mostrar cada distrito (ahora ya consolidado)
      Object.values(distritos).forEach(distrito => {
        try {
          // Formato: 📍 Distrito A (14A)
          mensaje += `📍 <b>Distrito ${distrito.distrito}</b> (${distrito.rDistrito})\n`;
          mensaje += `👥 ${distrito.cantidad} misionero${distrito.cantidad > 1 ? 's' : ''}\n`;
          
          // Mostrar duración
          if (distrito.duracionSemanas) {
            mensaje += `⏱️ Duración: ${distrito.duracionSemanas} semanas\n`;
          }
          
          // Mostrar fechas de entrada y salida
          const fechaEntrada = distrito.fechaLlegada.toLocaleDateString('es-ES');
          mensaje += `◆ Entrada: ${fechaEntrada}\n`;
          
          if (distrito.fechaSalida) {
            const fechaSalida = distrito.fechaSalida.toLocaleDateString('es-ES');
            mensaje += `◆ Salida: ${fechaSalida}\n\n`;
          } else {
            mensaje += `◆ Salida: Por definir\n\n`;
          }
          
        } catch (error) {
          console.log("⚠️ Error al procesar distrito individual:", distrito, error);
          mensaje += `📍 <b>Distrito ${distrito.distrito || 'Desconocido'}</b>\n`;
          mensaje += `⚠️ Error al procesar datos\n\n`;
        }
      });
    });
    
    // Agregar timestamp y información del sistema al final
    const timestamp = new Date().toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
    
    mensaje += `🕐 ${timestamp}\n`;
    mensaje += `🏢 Rama ${ramaReporte} - CCM Sistema`;
    
    return mensaje;
    
  } catch (error) {
    console.error("❌ Error al generar reporte de próximos ingresos CCM:", error.toString());
    return `❌ Error al generar reporte de próximos ingresos CCM: ${error.toString()}`;
  }
}

/**
 * Función principal para notificar próximos ingresos al CCM con formato CCM Notifications
 * Esta función debe ser llamada desde el script "Extraer datos misionales"
 * @param {Object} conn - Conexión activa a la base de datos MySQL
 * @param {number} rama - Número de rama (opcional, usa RAMA por defecto)
 */
function notificarProximosIngresosCCM(conn, rama = null) {
  try {
    console.log("📋 Generando reporte de próximos ingresos al CCM...");
    
    // Consultar próximos misioneros
    const proximosMisioneros = consultarProximosMisionerosCCM(conn, rama);
    
    // Generar mensaje formateado con el estilo específico de CCM Notifications
    const mensajeReporte = generarReporteProximosIngresosCCM(proximosMisioneros, rama);
    
    // Enviar a Telegram usando el formato específico
    const resultado = enviarMensajeTelegram(mensajeReporte);
    
    if (resultado.success) {
      console.log("✅ Reporte de próximos ingresos al CCM enviado exitosamente a Telegram");
    } else {
      console.error("❌ Error al enviar reporte a Telegram:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en notificarProximosIngresosCCM:", error.toString());
    return { success: false, error: error.toString() };
  }
}




