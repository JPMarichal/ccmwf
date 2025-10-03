/**
 * SCRIPT DE NOTIFICACIONES CCM PARA MESSENGER
 * 
 * Sistema automatizado para envío de notificaciones del CCM a un chat grupal
 * de Facebook Messenger para comunicación con líderes de zona y hermanas capacitadoras.
 * 
 * CARACTERÍSTICAS:
 * - Notificaciones automáticas de próximos cumpleaños
 * - Notificaciones de próximos ingresos al CCM
 * - Formato optimizado para Messenger (texto plano)
 * - Dirigido a líderes de zona y hermanas capacitadoras
 * - Modo de prueba para testing seguro
 * - Manejo de errores y logging detallado
 * 
 * FUNCIONES PRINCIPALES:
 * - enviarNotificacionesCCMMessenger(): Proceso principal (ambas notificaciones)
 * - enviarSoloCumpleanosMessenger(): Solo cumpleaños
 * - enviarSoloIngresosMessenger(): Solo ingresos al CCM
 * - probarNotificacionesMessenger(): Función de prueba
 * - configurarTriggerMessenger(): Configura trigger automático
 * 
 * CONFIGURACIÓN:
 * - Base de datos: dbConfig (Config.js)
 * - Messenger: MESSENGER_CONFIG (Config.js)
 * - Scope: RAMAS_AUTORIZADAS (Config.js)
 * 
 * AUDIENCIA:
 * - Líderes de zona
 * - Hermanas capacitadoras
 * - Personal de supervisión CCM
 * 
 * @author CCM Scripts
 * @version 1.0
 */

// === CONFIGURACIÓN DE MODO PRUEBA ===
const MODO_PRUEBA_MESSENGER = false; // Cambiar a true para testing

/**
 * Función principal que envía todas las notificaciones CCM a Messenger
 * Incluye tanto cumpleaños como próximos ingresos
 */
function enviarNotificacionesCCMMessenger() {
  console.log("📱 Iniciando proceso de notificaciones CCM para Messenger");
  console.log(`👥 Destinatarios: ${MESSENGER_CONFIG.destinatarios}`);
  
  if (MODO_PRUEBA_MESSENGER) {
    console.log("🧪 *** MODO PRUEBA ACTIVADO ***");
    return probarNotificacionesMessenger();
  }
  
  // Modo producción - conectar a base de datos
  let conn;
  
  try {
    // Conectar a la base de datos
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    // Establecer collation para la sesión
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    console.log("✅ Conexión a MySQL exitosa con collation configurado");
    
    // Enviar todas las notificaciones usando las funciones del MessengerNotifier
    const resultado = enviarTodasLasNotificacionesMessenger(conn, RAMA);
    
    if (resultado.success) {
      console.log(`🎉 Notificaciones CCM enviadas a Messenger: ${resultado.exitosos} exitosas`);
      if (resultado.fallidos > 0) {
        console.log(`⚠️ ${resultado.fallidos} notificaciones fallaron`);
      }
    } else {
      console.error("❌ Error en notificaciones a Messenger:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en enviarNotificacionesCCMMessenger:", error.toString());
    return { success: false, error: error.toString() };
  } finally {
    if (conn) {
      try {
        conn.close();
        console.log("✅ Conexión a base de datos cerrada");
      } catch (error) {
        console.error("⚠️ Error al cerrar conexión:", error.toString());
      }
    }
  }
}

/**
 * Función para enviar solo notificaciones de cumpleaños a Messenger
 */
function enviarSoloCumpleanosMessenger() {
  console.log("🎂 Enviando solo notificaciones de cumpleaños a Messenger");
  
  let conn;
  
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    console.log("✅ Conexión a MySQL exitosa");
    
    const resultado = notificarProximosCumpleanosMessenger(conn, RAMA);
    
    if (resultado.success) {
      console.log("🎉 Notificación de cumpleaños enviada a Messenger exitosamente");
    } else {
      console.error("❌ Error en notificación de cumpleaños:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en enviarSoloCumpleanosMessenger:", error.toString());
    return { success: false, error: error.toString() };
  } finally {
    if (conn) {
      try {
        conn.close();
      } catch (error) {
        console.error("⚠️ Error al cerrar conexión:", error.toString());
      }
    }
  }
}

/**
 * Función para enviar solo notificaciones de próximos ingresos a Messenger
 */
function enviarSoloIngresosMessenger() {
  console.log("📊 Enviando solo notificaciones de próximos ingresos a Messenger");
  
  let conn;
  
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    console.log("✅ Conexión a MySQL exitosa");
    
    const resultado = notificarProximosIngresosCCMMessenger(conn, RAMA);
    
    if (resultado.success) {
      console.log("🎉 Notificación de próximos ingresos enviada a Messenger exitosamente");
    } else {
      console.error("❌ Error en notificación de ingresos:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en enviarSoloIngresosMessenger:", error.toString());
    return { success: false, error: error.toString() };
  } finally {
    if (conn) {
      try {
        conn.close();
      } catch (error) {
        console.error("⚠️ Error al cerrar conexión:", error.toString());
      }
    }
  }
}

/**
 * Función de prueba que envía notificaciones simuladas
 */
function probarNotificacionesMessenger() {
  console.log("🧪 Ejecutando prueba de notificaciones para Messenger...");
  
  try {
    // Verificar configuración de Messenger
    if (!MESSENGER_CONFIG.enabled) {
      console.log("⚠️ Las notificaciones de Messenger están deshabilitadas");
      return { success: false, message: "Notificaciones deshabilitadas" };
    }
    
    // Primero probar la conexión
    console.log("🔗 Probando conexión básica...");
    const pruebaConexion = probarConexionMessenger();
    
    if (!pruebaConexion.success) {
      console.error("❌ Fallo en prueba de conexión básica");
      return pruebaConexion;
    }
    
    console.log("✅ Conexión básica exitosa, enviando notificaciones de prueba...");
    
    // Esperar un poco entre mensajes
    Utilities.sleep(3000);
    
    // Crear datos simulados para cumpleaños
    const cumpleanosSimulados = [
      {
        id: 1, rama: 14, rDistrito: "Distrito Norte", tratamiento: "Elder Hatcher",
        nombreMisionero: "Elder Hatcher", nuevaEdad: 20, status: "CCM",
        correoMisional: "hatcher@train.missionary.org",
        fechaCumpleanos: new Date(2025, 7, 19) // 19 de agosto
      },
      {
        id: 2, rama: 14, rDistrito: "Distrito Sur", tratamiento: "Hermana Smedley",
        nombreMisionero: "Hermana Smedley", nuevaEdad: 20, status: "Virtual",
        correoMisional: "smedley@train.missionary.org",
        fechaCumpleanos: new Date(2025, 8, 26) // 26 de septiembre
      }
    ];
    
    // Enviar notificación de cumpleaños de prueba
    const mensajeCumpleanos = generarReporteProximosCumpleanosMessenger(cumpleanosSimulados, 14);
    const resultadoCumpleanos = enviarMensajeMessenger(mensajeCumpleanos);
    
    console.log("🎂 Resultado cumpleaños:", resultadoCumpleanos.success ? "✅ Exitoso" : "❌ Fallido");
    
    // Esperar entre mensajes
    Utilities.sleep(3000);
    
    // Crear datos simulados para ingresos
    const ingresosSimulados = [
      {
        distrito: "C", rDistrito: "14C",
        fechaLlegada: new Date(2025, 7, 20), fechaSalida: new Date(2025, 8, 24),
        cantidad: 12, duracionSemanas: 6
      },
      {
        distrito: "D", rDistrito: "14D",
        fechaLlegada: new Date(2025, 7, 21), fechaSalida: new Date(2025, 8, 24),
        cantidad: 11, duracionSemanas: 6
      }
    ];
    
    // Enviar notificación de ingresos de prueba
    const mensajeIngresos = generarReporteProximosIngresosCCMMessenger(ingresosSimulados, 14);
    const resultadoIngresos = enviarMensajeMessenger(mensajeIngresos);
    
    console.log("📊 Resultado ingresos:", resultadoIngresos.success ? "✅ Exitoso" : "❌ Fallido");
    
    // Evaluar resultados generales
    const exitosos = [resultadoCumpleanos.success, resultadoIngresos.success].filter(r => r).length;
    const total = 2;
    
    if (exitosos === total) {
      console.log("🎉 Todas las pruebas de Messenger completadas exitosamente");
    } else {
      console.log(`⚠️ Pruebas parcialmente exitosas: ${exitosos}/${total}`);
    }
    
    return {
      success: exitosos > 0,
      exitosos: exitosos,
      total: total,
      resultados: {
        cumpleanos: resultadoCumpleanos,
        ingresos: resultadoIngresos
      }
    };
    
  } catch (error) {
    console.error("❌ Error en prueba de notificaciones:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Función para configurar un trigger automático semanal
 */
function configurarTriggerMessenger() {
  try {
    console.log("⏰ Configurando trigger automático para notificaciones de Messenger...");
    
    // Eliminar triggers existentes
    const triggersExistentes = ScriptApp.getProjectTriggers();
    triggersExistentes.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'enviarNotificacionesCCMMessenger') {
        ScriptApp.deleteTrigger(trigger);
        console.log("🗑️ Trigger existente eliminado");
      }
    });
    
    // Crear nuevo trigger semanal (cada viernes a las 10:00 AM)
    // Diferente día que Telegram para distribuir las notificaciones
    ScriptApp.newTrigger('enviarNotificacionesCCMMessenger')
      .timeBased()
      .everyWeeks(1)
      .onWeekDay(ScriptApp.WeekDay.FRIDAY)
      .atHour(10)
      .create();
    
    console.log("✅ Trigger configurado: enviarNotificacionesCCMMessenger cada viernes a las 10:00 AM");
    console.log("📅 Próxima ejecución automática programada");
    console.log("👥 Destinatarios: Líderes de zona y hermanas capacitadoras");
    
    return { 
      success: true, 
      message: "Trigger configurado exitosamente para notificaciones semanales de Messenger" 
    };
    
  } catch (error) {
    console.error("❌ Error al configurar trigger:", error.toString());
    return { 
      success: false, 
      error: error.toString() 
    };
  }
}

/**
 * Función para eliminar los triggers automáticos de Messenger
 */
function eliminarTriggerMessenger() {
  try {
    console.log("🗑️ Eliminando triggers de notificaciones de Messenger...");
    
    const triggersExistentes = ScriptApp.getProjectTriggers();
    let triggersEliminados = 0;
    
    triggersExistentes.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'enviarNotificacionesCCMMessenger') {
        ScriptApp.deleteTrigger(trigger);
        triggersEliminados++;
        console.log("🗑️ Trigger eliminado");
      }
    });
    
    if (triggersEliminados > 0) {
      console.log(`✅ ${triggersEliminados} trigger(s) de Messenger eliminado(s)`);
    } else {
      console.log("ℹ️ No se encontraron triggers de Messenger para eliminar");
    }
    
    return { 
      success: true, 
      message: `${triggersEliminados} trigger(s) eliminado(s)` 
    };
    
  } catch (error) {
    console.error("❌ Error al eliminar triggers:", error.toString());
    return { 
      success: false, 
      error: error.toString() 
    };
  }
}

/**
 * Función de estado que muestra información sobre los triggers configurados
 */
function estadoTriggersMessenger() {
  try {
    console.log("📊 Verificando estado de triggers de Messenger...");
    
    const triggersExistentes = ScriptApp.getProjectTriggers();
    const triggersMessenger = triggersExistentes.filter(trigger => 
      trigger.getHandlerFunction() === 'enviarNotificacionesCCMMessenger'
    );
    
    if (triggersMessenger.length === 0) {
      console.log("ℹ️ No hay triggers de Messenger configurados");
      console.log("💡 Usar configurarTriggerMessenger() para crear uno");
    } else {
      console.log(`✅ Encontrados ${triggersMessenger.length} trigger(s) de Messenger:`);
      
      triggersMessenger.forEach((trigger, index) => {
        const tipo = trigger.getEventType();
        console.log(`   ${index + 1}. Tipo: ${tipo}`);
        
        if (tipo === ScriptApp.EventType.CLOCK) {
          console.log(`      ⏰ Programación: ${trigger.getHandlerFunction()}`);
        }
      });
    }
    
    // Mostrar estado de configuración de Messenger
    console.log(`📱 Messenger habilitado: ${MESSENGER_CONFIG.enabled}`);
    console.log(`💬 Chat: ${MESSENGER_CONFIG.chatNombre}`);
    console.log(`👥 Destinatarios: ${MESSENGER_CONFIG.destinatarios}`);
    console.log(`🎯 Rama configurada: ${RAMA}`);
    
    return { 
      success: true, 
      triggersCount: triggersMessenger.length,
      messengerEnabled: MESSENGER_CONFIG.enabled
    };
    
  } catch (error) {
    console.error("❌ Error al verificar estado:", error.toString());
    return { 
      success: false, 
      error: error.toString() 
    };
  }
}
