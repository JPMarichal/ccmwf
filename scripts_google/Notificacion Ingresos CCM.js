/**
 * SCRIPT DE NOTIFICACIONES DE PRÓXIMOS INGRESOS AL CCM
 * 
 * Sistema automatizado para envío de notificaciones de próximos ingresos de misioneros
 * al CCM en el formato específico de "CCM Notifications".
 * 
 * CARACTERÍSTICAS:
 * - Notificación automática de próximos ingresos al CCM
 * - Formato organizado por semana con fecha específica
 * - Información detallada por distrito (duración, entrada, salida)
 * - Timestamp y información del sistema
 * - Filtrado por rama y próximas semanas
 * - Modo de prueba para testing seguro
 * - Manejo de errores y logging detallado
 * 
 * FUNCIONES PRINCIPALES:
 * - enviarNotificacionIngresosCCM(): Proceso principal
 * - probarNotificacionIngresosCCM(): Función de prueba con datos simulados
 * - configurarTriggerIngresosCCM(): Configura trigger automático
 * 
 * CONFIGURACIÓN:
 * - Base de datos: dbConfig (Config.js)
 * - Telegram: TELEGRAM_CONFIG (Config.js)
 * - Scope: RAMAS_AUTORIZADAS (Config.js)
 * 
 * MODO PRUEBA:
 * - Cambiar MODO_PRUEBA_INGRESOS a true para testing
 * - Usar probarNotificacionIngresosCCM() para pruebas
 * 
 * USO:
 * - Ejecutar enviarNotificacionIngresosCCM() manualmente o con trigger
 * - Configurar trigger semanal usando configurarTriggerIngresosCCM()
 * 
 * @author CCM Scripts
 * @version 1.0
 */

// === CONFIGURACIÓN DE MODO PRUEBA ===
const MODO_PRUEBA_INGRESOS = false; // Cambiar a true para testing

/**
 * Función principal que envía la notificación de próximos ingresos al CCM
 * Se recomienda ejecutar semanalmente después de actualizar datos misionales
 */
function enviarNotificacionIngresosCCM() {
  console.log("📊 Iniciando proceso de notificación de próximos ingresos al CCM");
  
  if (MODO_PRUEBA_INGRESOS) {
    console.log("🧪 *** MODO PRUEBA ACTIVADO ***");
    return probarNotificacionIngresosCCM();
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
    
    // Enviar notificación de próximos ingresos usando las funciones del TelegramNotifier
    const resultado = notificarProximosIngresosCCM(conn, RAMA);
    
    if (resultado.success) {
      console.log("🎉 Notificación de próximos ingresos al CCM completada exitosamente");
    } else {
      console.error("❌ Error en notificación de ingresos:", resultado.error || resultado.message);
    }
    
    return resultado;
    
  } catch (error) {
    console.error("❌ Error en enviarNotificacionIngresosCCM:", error.toString());
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
function probarNotificacionIngresosCCM() {
  console.log("🧪 Ejecutando prueba de notificación de próximos ingresos...");
  
  try {
    // Verificar configuración de Telegram
    if (!TELEGRAM_CONFIG.enabled) {
      console.log("⚠️ Las notificaciones de Telegram están deshabilitadas");
      return { success: false, message: "Notificaciones deshabilitadas" };
    }
    
    // Crear datos simulados (basados en la imagen real)
    // Simulando el caso donde distrito D aparece duplicado en BD pero debe consolidarse
    const ingresosSimulados = [
      {
        distrito: "C",
        rDistrito: "14C",
        fechaLlegada: new Date(2025, 7, 20), // 20 de agosto (próxima semana)
        fechaSalida: new Date(2025, 8, 24), // 24 de septiembre  
        cantidad: 12,
        duracionSemanas: 6
      },
      {
        distrito: "D", 
        rDistrito: "14D",
        fechaLlegada: new Date(2025, 7, 21), // 21 de agosto
        fechaSalida: new Date(2025, 8, 23), // 23 de septiembre
        cantidad: 4, // Primera parte del distrito D
        duracionSemanas: 6
      },
      {
        distrito: "D", 
        rDistrito: "14D",
        fechaLlegada: new Date(2025, 7, 21), // 21 de agosto (misma fecha)
        fechaSalida: new Date(2025, 8, 24), // 24 de septiembre (puede ser diferente)
        cantidad: 7, // Segunda parte del distrito D - debe sumarse = 11 total
        duracionSemanas: 6
      },
      {
        distrito: "H",
        rDistrito: "14H",
        fechaLlegada: new Date(2025, 7, 21), // 21 de agosto
        fechaSalida: new Date(2025, 8, 24), // 24 de septiembre
        cantidad: 12,
        duracionSemanas: 6
      }
    ];
    
    // Generar mensaje usando la función del TelegramNotifier
    const mensajeReporte = generarReporteProximosIngresosCCM(ingresosSimulados, 14);
    
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
function configurarTriggerIngresosCCM() {
  try {
    console.log("⏰ Configurando trigger automático para notificaciones de ingresos al CCM...");
    
    // Eliminar triggers existentes
    const triggersExistentes = ScriptApp.getProjectTriggers();
    triggersExistentes.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'enviarNotificacionIngresosCCM') {
        ScriptApp.deleteTrigger(trigger);
        console.log("🗑️ Trigger existente eliminado");
      }
    });
    
    // Crear nuevo trigger semanal (cada miércoles a las 9:00 AM)
    // Se recomienda ejecutar después de actualizar datos misionales
    ScriptApp.newTrigger('enviarNotificacionIngresosCCM')
      .timeBased()
      .everyWeeks(1)
      .onWeekDay(ScriptApp.WeekDay.WEDNESDAY)
      .atHour(9)
      .create();
    
    console.log("✅ Trigger configurado: enviarNotificacionIngresosCCM cada miércoles a las 9:00 AM");
    console.log("📅 Próxima ejecución automática programada");
    
    return { 
      success: true, 
      message: "Trigger configurado exitosamente para notificaciones semanales de ingresos" 
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
function eliminarTriggerIngresosCCM() {
  try {
    console.log("🗑️ Eliminando triggers de notificaciones de ingresos al CCM...");
    
    const triggersExistentes = ScriptApp.getProjectTriggers();
    let triggersEliminados = 0;
    
    triggersExistentes.forEach(trigger => {
      if (trigger.getHandlerFunction() === 'enviarNotificacionIngresosCCM') {
        ScriptApp.deleteTrigger(trigger);
        triggersEliminados++;
        console.log("🗑️ Trigger eliminado");
      }
    });
    
    if (triggersEliminados > 0) {
      console.log(`✅ ${triggersEliminados} trigger(s) de ingresos eliminado(s)`);
    } else {
      console.log("ℹ️ No se encontraron triggers de ingresos para eliminar");
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
function estadoTriggersIngresosCCM() {
  try {
    console.log("📊 Verificando estado de triggers de ingresos al CCM...");
    
    const triggersExistentes = ScriptApp.getProjectTriggers();
    const triggersIngresos = triggersExistentes.filter(trigger => 
      trigger.getHandlerFunction() === 'enviarNotificacionIngresosCCM'
    );
    
    if (triggersIngresos.length === 0) {
      console.log("ℹ️ No hay triggers de ingresos configurados");
      console.log("💡 Usar configurarTriggerIngresosCCM() para crear uno");
    } else {
      console.log(`✅ Encontrados ${triggersIngresos.length} trigger(s) de ingresos:`);
      
      triggersIngresos.forEach((trigger, index) => {
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
      triggersCount: triggersIngresos.length,
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
