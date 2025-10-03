// MessengerNotifier.js
// Script para enviar notificaciones a Facebook Messenger usando la Graph API

/**
 * Envía un mensaje a un chat grupal de Facebook Messenger
 * @param {string} mensaje - El mensaje a enviar
 * @param {Object} config - Configuración opcional del messenger (si no se pasa, usa MESSENGER_CONFIG por defecto)
 * @returns {Object} - Respuesta de la API de Facebook
 */
function enviarMensajeMessenger(mensaje, config = null) {
  try {
    // Usar configuración por defecto si no se proporciona una
    const messengerConfig = config || MESSENGER_CONFIG;
    
    // Verificar si las notificaciones están habilitadas
    if (!messengerConfig.enabled) {
      console.log("Las notificaciones de Messenger están deshabilitadas");
      return { success: false, message: "Notificaciones deshabilitadas" };
    }
    
    // Verificar que tenemos los datos necesarios
    if (!messengerConfig.pageAccessToken || !messengerConfig.groupThreadId) {
      throw new Error("Token de página o Group Thread ID no configurados");
    }
    
    // Construir la URL de la Graph API de Facebook
    const url = `https://graph.facebook.com/v18.0/me/messages`;
    
    // Preparar los datos del mensaje
    const payload = {
      recipient: {
        thread_key: messengerConfig.groupThreadId // ID del grupo existente
      },
      message: {
        text: mensaje
      },
      messaging_type: "UPDATE" // Tipo de mensaje para actualizaciones
    };
    
    // Configurar las opciones de la petición HTTP
    const options = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${messengerConfig.pageAccessToken}`
      },
      payload: JSON.stringify(payload)
    };
    
    // Enviar la petición a la Graph API de Facebook
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    // Procesar la respuesta
    if (responseCode === 200) {
      const result = JSON.parse(responseText);
      if (result.message_id) {
        console.log("Mensaje enviado exitosamente a Messenger");
        return { 
          success: true, 
          messageId: result.message_id,
          response: result 
        };
      } else {
        throw new Error(`Error de la API de Facebook: ${result.error ? result.error.message : 'Error desconocido'}`);
      }
    } else {
      throw new Error(`Error HTTP ${responseCode}: ${responseText}`);
    }
    
  } catch (error) {
    console.error("Error al enviar mensaje a Messenger:", error.toString());
    return { 
      success: false, 
      error: error.toString() 
    };
  }
}

/**
 * Envía un mensaje formateado con información del sistema CCM a Messenger
 * @param {string} titulo - Título del mensaje
 * @param {string} contenido - Contenido principal del mensaje
 * @param {string} tipo - Tipo de mensaje ('info', 'warning', 'error', 'success')
 */
function enviarNotificacionCCMMessenger(titulo, contenido, tipo = 'info') {
  try {
    // Emojis según el tipo de mensaje
    const emojis = {
      'info': 'ℹ️',
      'warning': '⚠️',
      'error': '🚨',
      'success': '✅'
    };
    
    const emoji = emojis[tipo] || emojis['info'];
    
    // Formato para Messenger (texto plano, sin HTML)
    const mensaje = `${emoji} ${titulo}\n\n` +
                   `${contenido}\n\n` +
                   `🕐 ${new Date().toLocaleString('es-ES')}\n` +
                   `🏢 Rama ${RAMA} - CCM Sistema`;
    
    return enviarMensajeMessenger(mensaje);
    
  } catch (error) {
    console.error("Error al enviar notificación CCM a Messenger:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Genera un reporte formateado de próximos cumpleaños para Messenger
 * @param {Array} proximosCumpleanos - Array de próximos cumpleaños
 * @param {number} rama - Número de rama
 * @returns {string} - Mensaje formateado para Messenger
 */
function generarReporteProximosCumpleanosMessenger(proximosCumpleanos, rama = null) {
  try {
    const ramaReporte = rama || RAMA;
    
    if (!proximosCumpleanos || proximosCumpleanos.length === 0) {
      return `✅ No hay cumpleaños próximos programados para los próximos meses.`;
    }
    
    // Filtrar y validar fechas
    const cumpleanosValidos = proximosCumpleanos.filter(cumpleanos => {
      return cumpleanos.fechaCumpleanos && 
             cumpleanos.fechaCumpleanos instanceof Date && 
             !isNaN(cumpleanos.fechaCumpleanos.getTime());
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
      const fecha = cumpleanos.fechaCumpleanos;
      const mes = fecha.getMonth() + 1;
      const dia = fecha.getDate();
      
      if (!gruposPorMes[mes]) {
        gruposPorMes[mes] = {};
      }
      
      if (!gruposPorMes[mes][dia]) {
        gruposPorMes[mes][dia] = [];
      }
      
      gruposPorMes[mes][dia].push(cumpleanos);
    });
    
    // Construir el mensaje para Messenger (texto plano)
    let mensaje = `🎊 PRÓXIMOS CUMPLEAÑOS\n`;
    mensaje += `📅 ${new Date().toLocaleDateString('es-ES')}\n`;
    mensaje += `🎯 Ramas: ${ramaReporte}\n\n`;
    
    // Procesar cada mes
    const mesesOrdenados = Object.keys(gruposPorMes).sort((a, b) => parseInt(a) - parseInt(b));
    
    mesesOrdenados.forEach(mes => {
      const nombreMes = nombresMeses[parseInt(mes)];
      const diasDelMes = gruposPorMes[mes];
      
      mensaje += `🗓️ ${nombreMes}:\n`;
      
      const diasOrdenados = Object.keys(diasDelMes).sort((a, b) => parseInt(a) - parseInt(b));
      
      diasOrdenados.forEach(dia => {
        const cumpleanosDelDia = diasDelMes[dia];
        
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
    console.error("Error al generar reporte de próximos cumpleaños para Messenger:", error.toString());
    return `❌ Error al generar reporte de próximos cumpleaños: ${error.toString()}`;
  }
}

/**
 * Genera un reporte formateado de próximos ingresos al CCM para Messenger
 * @param {Array} proximosMisioneros - Array de próximos misioneros
 * @param {number} rama - Número de rama
 * @returns {string} - Mensaje formateado para Messenger
 */
function generarReporteProximosIngresosCCMMessenger(proximosMisioneros, rama = null) {
  try {
    const ramaReporte = rama || RAMA;
    
    if (!proximosMisioneros || proximosMisioneros.length === 0) {
      const timestamp = new Date().toLocaleString('es-ES');
      return `📊 Próximos Ingresos al CCM\n\n` +
             `✅ No hay misioneros programados para ingresar al CCM en las próximas semanas.\n\n` +
             `🕐 ${timestamp}\n` +
             `🏢 Rama ${ramaReporte} - CCM Sistema`;
    }
    
    // Filtrar y validar fechas
    const proximosValidos = proximosMisioneros.filter(grupo => {
      return grupo.fechaLlegada && 
             grupo.fechaLlegada instanceof Date && 
             !isNaN(grupo.fechaLlegada.getTime());
    });
    
    if (proximosValidos.length === 0) {
      return `⚠️ Se encontraron datos pero todas las fechas son inválidas.`;
    }
    
    // Agrupar por fecha y luego por distrito (misma lógica que Telegram pero formato texto)
    const gruposPorFecha = {};
    proximosValidos.forEach(grupo => {
      const fecha = grupo.fechaLlegada;
      const fechaKey = fecha.toISOString().split('T')[0];
      
      if (!gruposPorFecha[fechaKey]) {
        gruposPorFecha[fechaKey] = {};
      }
      
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
      
      // Tomar la fecha de salida más tardía
      if (grupo.fechaSalida && gruposPorFecha[fechaKey][distritoKey].fechaSalida) {
        if (grupo.fechaSalida > gruposPorFecha[fechaKey][distritoKey].fechaSalida) {
          gruposPorFecha[fechaKey][distritoKey].fechaSalida = grupo.fechaSalida;
        }
      } else if (grupo.fechaSalida) {
        gruposPorFecha[fechaKey][distritoKey].fechaSalida = grupo.fechaSalida;
      }
    });
    
    // Construir el mensaje para Messenger (texto plano)
    let mensaje = `📊 Próximos Ingresos al CCM\n\n`;
    
    const fechasOrdenadas = Object.keys(gruposPorFecha).sort();
    
    fechasOrdenadas.forEach(fechaKey => {
      const distritos = gruposPorFecha[fechaKey];
      const fecha = new Date(fechaKey);
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
      
      mensaje += `◆ ${descripcionTiempo} (${fecha.toLocaleDateString('es-ES')})\n`;
      mensaje += `◆ Total: ${totalDia} misioneros\n\n`;
      
      // Mostrar cada distrito
      Object.values(distritos).forEach(distrito => {
        mensaje += `📍 Distrito ${distrito.distrito} (${distrito.rDistrito})\n`;
        mensaje += `👥 ${distrito.cantidad} misionero${distrito.cantidad > 1 ? 's' : ''}\n`;
        
        if (distrito.duracionSemanas) {
          mensaje += `⏱️ Duración: ${distrito.duracionSemanas} semanas\n`;
        }
        
        const fechaEntrada = distrito.fechaLlegada.toLocaleDateString('es-ES');
        mensaje += `◆ Entrada: ${fechaEntrada}\n`;
        
        if (distrito.fechaSalida) {
          const fechaSalida = distrito.fechaSalida.toLocaleDateString('es-ES');
          mensaje += `◆ Salida: ${fechaSalida}\n\n`;
        } else {
          mensaje += `◆ Salida: Por definir\n\n`;
        }
      });
    });
    
    // Agregar timestamp y información del sistema
    const timestamp = new Date().toLocaleString('es-ES');
    mensaje += `🕐 ${timestamp}\n`;
    mensaje += `🏢 Rama ${ramaReporte} - CCM Sistema`;
    
    return mensaje;
    
  } catch (error) {
    console.error("Error al generar reporte de próximos ingresos CCM para Messenger:", error.toString());
    return `❌ Error al generar reporte de próximos ingresos CCM: ${error.toString()}`;
  }
}

/**
 * Función principal para notificar próximos cumpleaños a Messenger
 * @param {Object} conn - Conexión activa a la base de datos MySQL
 * @param {number} rama - Número de rama (opcional, usa RAMA por defecto)
 */
function notificarProximosCumpleanosMessenger(conn, rama = null) {
  try {
    console.log("🎂 Generando reporte de próximos cumpleaños para Messenger...");
    
    // Reutilizar la función de consulta existente
    const proximosCumpleanos = consultarProximosCumpleanos(conn, rama);
    
    // Generar mensaje formateado para Messenger
    const mensajeReporte = generarReporteProximosCumpleanosMessenger(proximosCumpleanos, rama);
    
    // Enviar a Messenger
    const resultado = enviarMensajeMessenger(mensajeReporte);
    
    if (resultado.success) {
      console.log("✅ Reporte de próximos cumpleaños enviado exitosamente a Messenger");
    } else {
      console.error("❌ Error al enviar reporte a Messenger:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en notificarProximosCumpleanosMessenger:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Función principal para notificar próximos ingresos al CCM a Messenger
 * @param {Object} conn - Conexión activa a la base de datos MySQL
 * @param {number} rama - Número de rama (opcional, usa RAMA por defecto)
 */
function notificarProximosIngresosCCMMessenger(conn, rama = null) {
  try {
    console.log("📋 Generando reporte de próximos ingresos al CCM para Messenger...");
    
    // Reutilizar la función de consulta existente
    const proximosMisioneros = consultarProximosMisionerosCCM(conn, rama);
    
    // Generar mensaje formateado para Messenger
    const mensajeReporte = generarReporteProximosIngresosCCMMessenger(proximosMisioneros, rama);
    
    // Enviar a Messenger
    const resultado = enviarMensajeMessenger(mensajeReporte);
    
    if (resultado.success) {
      console.log("✅ Reporte de próximos ingresos al CCM enviado exitosamente a Messenger");
    } else {
      console.error("❌ Error al enviar reporte a Messenger:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en notificarProximosIngresosCCMMessenger:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Función para enviar ambas notificaciones (cumpleaños e ingresos) a Messenger
 * @param {Object} conn - Conexión activa a la base de datos MySQL
 * @param {number} rama - Número de rama (opcional, usa RAMA por defecto)
 */
function enviarTodasLasNotificacionesMessenger(conn, rama = null) {
  try {
    console.log("📱 Enviando todas las notificaciones a Messenger...");
    
    const resultados = [];
    
    // Enviar notificación de cumpleaños
    const resultadoCumpleanos = notificarProximosCumpleanosMessenger(conn, rama);
    resultados.push({ tipo: 'cumpleanos', resultado: resultadoCumpleanos });
    
    // Esperar un poco entre mensajes para evitar rate limiting
    Utilities.sleep(2000);
    
    // Enviar notificación de ingresos
    const resultadoIngresos = notificarProximosIngresosCCMMessenger(conn, rama);
    resultados.push({ tipo: 'ingresos', resultado: resultadoIngresos });
    
    // Evaluar resultados
    const exitosos = resultados.filter(r => r.resultado.success).length;
    const fallidos = resultados.length - exitosos;
    
    console.log(`📊 Resumen de envío a Messenger: ${exitosos} exitosos, ${fallidos} fallidos`);
    
    return {
      success: exitosos > 0,
      exitosos: exitosos,
      fallidos: fallidos,
      resultados: resultados
    };
    
  } catch (error) {
    console.error("❌ Error en enviarTodasLasNotificacionesMessenger:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Función de prueba para verificar conectividad con Messenger
 */
function probarConexionMessenger() {
  try {
    console.log("🧪 Probando conexión con Messenger...");
    
    if (!MESSENGER_CONFIG.enabled) {
      console.log("⚠️ Las notificaciones de Messenger están deshabilitadas");
      return { success: false, message: "Notificaciones deshabilitadas" };
    }
    
    const mensajePrueba = `🧪 Prueba de conexión\n\n` +
                         `✅ Sistema CCM conectado exitosamente a Messenger\n\n` +
                         `🕐 ${new Date().toLocaleString('es-ES')}\n` +
                         `🏢 Rama ${RAMA} - CCM Sistema`;
    
    const resultado = enviarMensajeMessenger(mensajePrueba);
    
    if (resultado.success) {
      console.log("✅ Prueba de conexión a Messenger exitosa");
      console.log(`📱 Message ID: ${resultado.messageId}`);
    } else {
      console.error("❌ Prueba de conexión fallida:", resultado.error);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en prueba de conexión:", error.toString());
    return { success: false, error: error.toString() };
  }
}
