/**
 * SCRIPT DE NOTIFICACIONES DE CUMPLEAÑOS A TELEGRAM
 * 
 * Sistema automatizado para envío de notificaciones de próximos cumpleaños
 * a Telegram en el formato de "CCM Notifications".
 * 
 * CARACTERÍSTICAS:
 * - Notificación automática de próximos cumpleaños
 * - Formato organizado por mes (AGOSTO, SEPTIEMBRE, etc.)
 * - Agrupación por fecha y tratamiento
 * - Filtrado por rama y estatus de misionero
 * - Modo de prueba para testing seguro
 * - Manejo de errores y logging detallado
 * 
 * FUNCIONES PRINCIPALES:
 * - enviarNotificacionCumpleanos(): Proceso principal
 * - probarNotificacionCumpleanos(): Función de prueba con datos simulados
 * - configurarTriggerCumpleanos(): Configura trigger automático
 * 
 * CONFIGURACIÓN:
 * - Base de datos: dbConfig (Config.js)
 * - Telegram: TELEGRAM_CONFIG (Config.js)
 * - Scope: RAMAS_AUTORIZADAS, CONFIG_ESTATUS_POR_RAMA (Config.js)
 * 
 * MODO PRUEBA:
 * - Cambiar MODO_PRUEBA a true para testing
 * - Usar probarNotificacionCumpleanos() para pruebas
 * 
 * USO:
 * - Ejecutar enviarNotificacionCumpleanos() manualmente o con trigger
 * - Configurar trigger semanal usando configurarTriggerCumpleanos()
 * 
 * @author CCM Scripts
 * @version 1.0
 */

// === CONFIGURACIÓN DE MODO PRUEBA ===
const MODO_PRUEBA_CUMPLEANOS = false; // Cambiar a true para testing

/**
 * Función principal que envía la notificación de próximos cumpleaños a Telegram
 * Se recomienda ejecutar semanalmente
 */
function enviarNotificacionCumpleanos() {
  console.log("🎂 Iniciando proceso de notificación de próximos cumpleaños");
  
  if (MODO_PRUEBA_CUMPLEANOS) {
    console.log("🧪 *** MODO PRUEBA ACTIVADO ***");
    return probarNotificacionCumpleanos();
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
    
    // Enviar notificación de próximos cumpleaños usando las funciones del TelegramNotifier
    const resultado = notificarProximosCumpleanos(conn, RAMA);
    
    if (resultado.success) {
      console.log("🎉 Notificación de próximos cumpleaños completada exitosamente");
    } else {
      console.error("❌ Error en notificación de cumpleaños:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en enviarNotificacionCumpleanos:", error.toString());
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
 * Función de prueba que envía una notificación simulada
 * Útil para verificar el formato y funcionamiento sin datos reales
 */
function probarNotificacionCumpleanos() {
  console.log("🧪 Ejecutando prueba de notificación de cumpleaños...");
  
  try {
    // Verificar configuración de Telegram
    if (!TELEGRAM_CONFIG.enabled) {
      console.log("⚠️ Las notificaciones de Telegram están deshabilitadas");
      return { success: false, message: "Notificaciones deshabilitadas" };
    }
    
    // Crear datos simulados (solo Virtual y CCM, fechas futuras desde hoy)
    const cumpleanosSimulados = [
      {
        id: 1,
        rama: 14,
        rDistrito: "Distrito Norte",
        tratamiento: "Elder Hatcher",
        nombreMisionero: "Elder Hatcher",
        nuevaEdad: 20,
        status: "CCM",
        correoMisional: "hatcher@train.missionary.org",
        fechaCumpleanos: new Date(2025, 7, 14) // 14 de agosto
      },
      {
        id: 2,
        rama: 14,
        rDistrito: "Distrito Sur",
        tratamiento: "Elder Wirthlin",
        nombreMisionero: "Elder Wirthlin",
        nuevaEdad: 19,
        status: "CCM",
        correoMisional: "wirthlin@train.missionary.org",
        fechaCumpleanos: new Date(2025, 7, 15) // 15 de agosto
      },
      {
        id: 3,
        rama: 14,
        rDistrito: "Distrito Este",
        tratamiento: "Elder Parry",
        nombreMisionero: "Elder Parry",
        nuevaEdad: 20,
        status: "CCM",
        correoMisional: "parry@train.missionary.org",
        fechaCumpleanos: new Date(2025, 7, 19) // 19 de agosto
      },
      {
        id: 4,
        rama: 14,
        rDistrito: "Distrito Oeste",
        tratamiento: "Elder Esplin",
        nombreMisionero: "Elder Esplin",
        nuevaEdad: 19,
        status: "Virtual",
        correoMisional: "esplin@train.missionary.org",
        fechaCumpleanos: new Date(2025, 8, 2) // 2 de septiembre
      },
      {
        id: 5,
        rama: 14,
        rDistrito: "Distrito Central",
        tratamiento: "Hermana Smedley",
        nombreMisionero: "Hermana Smedley",
        nuevaEdad: 20,
        status: "CCM",
        correoMisional: "smedley@train.missionary.org",
        fechaCumpleanos: new Date(2025, 8, 26) // 26 de septiembre
      }
    ];
    
    // Generar mensaje usando la función del TelegramNotifier
    const mensajeReporte = generarReporteProximosCumpleanos(cumpleanosSimulados, 14);
    
    console.log("📋 Mensaje generado para prueba:");
    console.log(mensajeReporte);
    
    // Enviar a Telegram
    const resultado = enviarMensajeTelegram(mensajeReporte);
    
    if (resultado.success) {
      console.log("✅ Notificación de prueba enviada exitosamente a Telegram");
      console.log(`📱 Message ID: ${resultado.messageId}`);
    } else {
      console.error("❌ Error al enviar notificación de prueba:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en prueba de notificación:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Función para configurar un trigger automático semanal
 * Configura la notificación para ejecutarse automáticamente cada semana
 */
function configurarTriggerCumpleanos() {
  try {
    console.log("⏰ Configurando trigger automático para notificaciones de cumpleaños...");
    
    // Eliminar triggers existentes
    const triggersExistentes = ScriptApp.getProjectTriggers();
    triggersExistentes.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'enviarNotificacionCumpleanos') {
        ScriptApp.deleteTrigger(trigger);
        console.log("🗑️ Trigger existente eliminado");
      }
    });
    
    // Crear nuevo trigger semanal (cada lunes a las 8:00 AM)
    ScriptApp.newTrigger('enviarNotificacionCumpleanos')
      .timeBased()
      .everyWeeks(1)
      .onWeekDay(ScriptApp.WeekDay.MONDAY)
      .atHour(8)
      .create();
    
    console.log("✅ Trigger configurado: enviarNotificacionCumpleanos cada lunes a las 8:00 AM");
    console.log("📅 Próxima ejecución automática programada");
    
    return { 
      success: true, 
      message: "Trigger configurado exitosamente para notificaciones semanales" 
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
 * Función para eliminar los triggers automáticos
 * Útil si necesitas deshabilitar las notificaciones automáticas
 */
function eliminarTriggerCumpleanos() {
  try {
    console.log("🗑️ Eliminando triggers de notificaciones de cumpleaños...");
    
    const triggersExistentes = ScriptApp.getProjectTriggers();
    let triggersEliminados = 0;
    
    triggersExistentes.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'enviarNotificacionCumpleanos') {
        ScriptApp.deleteTrigger(trigger);
        triggersEliminados++;
        console.log("🗑️ Trigger eliminado");
      }
    });
    
    if (triggersEliminados > 0) {
      console.log(`✅ ${triggersEliminados} trigger(s) de cumpleaños eliminado(s)`);
    } else {
      console.log("ℹ️ No se encontraron triggers de cumpleaños para eliminar");
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
function estadoTriggersCumpleanos() {
  try {
    console.log("📊 Verificando estado de triggers de cumpleaños...");
    
    const triggersExistentes = ScriptApp.getProjectTriggers();
    const triggersCumpleanos = triggersExistentes.filter(trigger => 
      trigger.getHandlerFunction() === 'enviarNotificacionCumpleanos'
    );
    
    if (triggersCumpleanos.length === 0) {
      console.log("ℹ️ No hay triggers de cumpleaños configurados");
      console.log("💡 Usar configurarTriggerCumpleanos() para crear uno");
    } else {
      console.log(`✅ Encontrados ${triggersCumpleanos.length} trigger(s) de cumpleaños:`);
      
      triggersCumpleanos.forEach((trigger, index) => {
        const tipo = trigger.getEventType();
        console.log(`   ${index + 1}. Tipo: ${tipo}`);
        
        if (tipo === ScriptApp.EventType.CLOCK) {
          console.log(`      ⏰ Programación: ${trigger.getHandlerFunction()}`);
        }
      });
    }
    
    // Mostrar estado de configuración de Telegram
    console.log(`📱 Telegram habilitado: ${TELEGRAM_CONFIG.enabled}`);
    console.log(`📢 Canal: ${TELEGRAM_CONFIG.canalNombre}`);
    console.log(`🎯 Rama configurada: ${RAMA}`);
    
    return { 
      success: true, 
      triggersCount: triggersCumpleanos.length,
      telegramEnabled: TELEGRAM_CONFIG.enabled
    };
    
  } catch (error) {
    console.error("❌ Error al verificar estado:", error.toString());
    return { 
      success: false, 
      error: error.toString() 
    };
  }
}
