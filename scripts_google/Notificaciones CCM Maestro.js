/**
 * SCRIPT MAESTRO DE NOTIFICACIONES CCM
 * 
 * Sistema unificado para envío de notificaciones del CCM a múltiples plataformas:
 * - Telegram: Canal "CCM Notifications" (público)
 * - Messenger: Chat grupal con líderes de zona y hermanas capacitadoras (privado)
 * 
 * CARACTERÍSTICAS:
 * - Envío coordinado a múltiples plataformas
 * - Diferentes audiencias y propósitos
 * - Manejo de errores independiente por plataforma
 * - Logging detallado de resultados
 * - Modo de prueba para testing seguro
 * 
 * FUNCIONES PRINCIPALES:
 * - enviarNotificacionesTodasPlataformas(): Envía a Telegram + Messenger
 * - enviarSoloCumpleanosTodasPlataformas(): Solo cumpleaños a ambos
 * - enviarSoloIngresosTodasPlataformas(): Solo ingresos a ambos
 * - estadoNotificacionesGlobal(): Estado de todas las plataformas
 * 
 * AUDIENCIAS:
 * - Telegram: Canal público para información general
 * - Messenger: Chat privado para coordinación de líderes
 * 
 * @author CCM Scripts
 * @version 1.0
 */

// === CONFIGURACIÓN GLOBAL ===
const MODO_PRUEBA_GLOBAL = false; // Cambiar a true para testing general

/**
 * Función principal que envía notificaciones CCM a todas las plataformas configuradas
 * Incluye Telegram (canal público) y Messenger (chat privado con líderes)
 */
function enviarNotificacionesTodasPlataformas() {
  console.log("🌐 Iniciando proceso de notificaciones CCM para todas las plataformas");
  console.log("📱 Plataformas: Telegram (público) + Messenger (líderes)");
  
  if (MODO_PRUEBA_GLOBAL) {
    console.log("🧪 *** MODO PRUEBA GLOBAL ACTIVADO ***");
    return probarTodasLasPlataformas();
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
    
    const resultados = [];
    
    // === ENVÍO A TELEGRAM ===
    if (TELEGRAM_CONFIG.enabled) {
      console.log("📢 Enviando notificaciones a Telegram...");
      
      try {
        // Cumpleaños
        const resultadoCumpleanosT = notificarProximosCumpleanos(conn, RAMA);
        resultados.push({ 
          plataforma: 'Telegram', 
          tipo: 'cumpleanos', 
          resultado: resultadoCumpleanosT 
        });
        
        // Pausa entre mensajes
        Utilities.sleep(3000);
        
        // Ingresos al CCM
        const resultadoIngresosT = notificarProximosIngresosCCM(conn, RAMA);
        resultados.push({ 
          plataforma: 'Telegram', 
          tipo: 'ingresos', 
          resultado: resultadoIngresosT 
        });
        
        console.log("📢 Notificaciones de Telegram completadas");
        
      } catch (error) {
        console.error("❌ Error en notificaciones de Telegram:", error.toString());
        resultados.push({ 
          plataforma: 'Telegram', 
          tipo: 'error', 
          resultado: { success: false, error: error.toString() } 
        });
      }
    } else {
      console.log("⚠️ Telegram deshabilitado, omitiendo...");
      resultados.push({ 
        plataforma: 'Telegram', 
        tipo: 'omitido', 
        resultado: { success: false, message: "Deshabilitado" } 
      });
    }
    
    // Pausa entre plataformas
    Utilities.sleep(5000);
    
    // === ENVÍO A MESSENGER ===
    if (MESSENGER_CONFIG.enabled) {
      console.log("💬 Enviando notificaciones a Messenger...");
      
      try {
        const resultadoMessenger = enviarTodasLasNotificacionesMessenger(conn, RAMA);
        resultados.push({ 
          plataforma: 'Messenger', 
          tipo: 'todas', 
          resultado: resultadoMessenger 
        });
        
        console.log("💬 Notificaciones de Messenger completadas");
        
      } catch (error) {
        console.error("❌ Error en notificaciones de Messenger:", error.toString());
        resultados.push({ 
          plataforma: 'Messenger', 
          tipo: 'error', 
          resultado: { success: false, error: error.toString() } 
        });
      }
    } else {
      console.log("⚠️ Messenger deshabilitado, omitiendo...");
      resultados.push({ 
        plataforma: 'Messenger', 
        tipo: 'omitido', 
        resultado: { success: false, message: "Deshabilitado" } 
      });
    }
    
    // === EVALUAR RESULTADOS GENERALES ===
    const exitosos = resultados.filter(r => r.resultado.success).length;
    const fallidos = resultados.length - exitosos;
    const plataformasExitosas = [...new Set(resultados.filter(r => r.resultado.success).map(r => r.plataforma))];
    
    console.log(`\n📊 === RESUMEN GENERAL ===`);
    console.log(`✅ Notificaciones exitosas: ${exitosos}`);
    console.log(`❌ Notificaciones fallidas: ${fallidos}`);
    console.log(`📱 Plataformas exitosas: ${plataformasExitosas.join(', ')}`);
    
    // Detalles por plataforma
    resultados.forEach(r => {
      const estado = r.resultado.success ? "✅" : "❌";
      console.log(`   ${estado} ${r.plataforma} (${r.tipo}): ${r.resultado.success ? 'Exitoso' : r.resultado.error || r.resultado.message}`);
    });
    
    if (exitosos > 0) {
      console.log("🎉 Proceso de notificaciones completado con éxito");
    } else {
      console.log("⚠️ Proceso completado pero sin notificaciones exitosas");
    }
    
    return {
      success: exitosos > 0,
      exitosos: exitosos,
      fallidos: fallidos,
      plataformasExitosas: plataformasExitosas,
      resultados: resultados
    };
    
  } catch (error) {
    console.error("❌ Error global en enviarNotificacionesTodasPlataformas:", error.toString());
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
 * Función para enviar solo notificaciones de cumpleaños a todas las plataformas
 */
function enviarSoloCumpleanosTodasPlataformas() {
  console.log("🎂 Enviando solo notificaciones de cumpleaños a todas las plataformas");
  
  let conn;
  
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    const resultados = [];
    
    // Telegram
    if (TELEGRAM_CONFIG.enabled) {
      const resultado = notificarProximosCumpleanos(conn, RAMA);
      resultados.push({ plataforma: 'Telegram', resultado: resultado });
    }
    
    // Pausa entre plataformas
    Utilities.sleep(3000);
    
    // Messenger
    if (MESSENGER_CONFIG.enabled) {
      const resultado = notificarProximosCumpleanosMessenger(conn, RAMA);
      resultados.push({ plataforma: 'Messenger', resultado: resultado });
    }
    
    const exitosos = resultados.filter(r => r.resultado.success).length;
    console.log(`🎂 Cumpleaños enviados a ${exitosos} plataforma(s)`);
    
    return { success: exitosos > 0, resultados: resultados };
    
  } catch (error) {
    console.error("❌ Error en enviarSoloCumpleanosTodasPlataformas:", error.toString());
    return { success: false, error: error.toString() };
  } finally {
    if (conn) {
      try { conn.close(); } catch (e) {}
    }
  }
}

/**
 * Función para enviar solo notificaciones de próximos ingresos a todas las plataformas
 */
function enviarSoloIngresosTodasPlataformas() {
  console.log("📊 Enviando solo notificaciones de próximos ingresos a todas las plataformas");
  
  let conn;
  
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    const resultados = [];
    
    // Telegram
    if (TELEGRAM_CONFIG.enabled) {
      const resultado = notificarProximosIngresosCCM(conn, RAMA);
      resultados.push({ plataforma: 'Telegram', resultado: resultado });
    }
    
    // Pausa entre plataformas
    Utilities.sleep(3000);
    
    // Messenger
    if (MESSENGER_CONFIG.enabled) {
      const resultado = notificarProximosIngresosCCMMessenger(conn, RAMA);
      resultados.push({ plataforma: 'Messenger', resultado: resultado });
    }
    
    const exitosos = resultados.filter(r => r.resultado.success).length;
    console.log(`📊 Ingresos enviados a ${exitosos} plataforma(s)`);
    
    return { success: exitosos > 0, resultados: resultados };
    
  } catch (error) {
    console.error("❌ Error en enviarSoloIngresosTodasPlataformas:", error.toString());
    return { success: false, error: error.toString() };
  } finally {
    if (conn) {
      try { conn.close(); } catch (e) {}
    }
  }
}

/**
 * Función de prueba para todas las plataformas
 */
function probarTodasLasPlataformas() {
  console.log("🧪 Ejecutando pruebas en todas las plataformas...");
  
  try {
    const resultados = [];
    
    // Probar Telegram
    if (TELEGRAM_CONFIG.enabled) {
      console.log("📢 Probando Telegram...");
      // Usar función de prueba existente o enviar mensaje de prueba
      const resultado = enviarMensajeTelegram("🧪 Prueba de notificaciones CCM - Telegram\n\n✅ Sistema funcionando correctamente");
      resultados.push({ plataforma: 'Telegram', resultado: resultado });
    }
    
    // Pausa entre pruebas
    Utilities.sleep(3000);
    
    // Probar Messenger
    if (MESSENGER_CONFIG.enabled) {
      console.log("💬 Probando Messenger...");
      const resultado = probarConexionMessenger();
      resultados.push({ plataforma: 'Messenger', resultado: resultado });
    }
    
    // Evaluar resultados
    const exitosos = resultados.filter(r => r.resultado.success).length;
    const total = resultados.length;
    
    console.log(`\n🧪 === RESULTADOS DE PRUEBA ===`);
    console.log(`✅ Plataformas funcionando: ${exitosos}/${total}`);
    
    resultados.forEach(r => {
      const estado = r.resultado.success ? "✅" : "❌";
      console.log(`   ${estado} ${r.plataforma}: ${r.resultado.success ? 'Funcionando' : r.resultado.error || r.resultado.message}`);
    });
    
    if (exitosos === total) {
      console.log("🎉 Todas las plataformas funcionando correctamente");
    } else if (exitosos > 0) {
      console.log("⚠️ Algunas plataformas funcionando");
    } else {
      console.log("❌ Ninguna plataforma funcionando");
    }
    
    return {
      success: exitosos > 0,
      exitosos: exitosos,
      total: total,
      resultados: resultados
    };
    
  } catch (error) {
    console.error("❌ Error en pruebas globales:", error.toString());
    return { success: false, error: error.toString() };
  }
}

/**
 * Función de estado que muestra información sobre todas las plataformas
 */
function estadoNotificacionesGlobal() {
  try {
    console.log("📊 === ESTADO GLOBAL DE NOTIFICACIONES CCM ===");
    
    // Estado de Telegram
    console.log("\n📢 TELEGRAM:");
    console.log(`   Habilitado: ${TELEGRAM_CONFIG.enabled}`);
    console.log(`   Canal: ${TELEGRAM_CONFIG.canalNombre}`);
    console.log(`   Chat ID: ${TELEGRAM_CONFIG.chatId}`);
    console.log(`   Audiencia: Canal público`);
    
    // Estado de Messenger
    console.log("\n💬 MESSENGER:");
    console.log(`   Habilitado: ${MESSENGER_CONFIG.enabled}`);
    console.log(`   Chat: ${MESSENGER_CONFIG.chatNombre}`);
    console.log(`   Chat ID: ${MESSENGER_CONFIG.chatId}`);
    console.log(`   Audiencia: ${MESSENGER_CONFIG.destinatarios}`);
    
    // Estado general
    console.log("\n🎯 CONFIGURACIÓN GENERAL:");
    console.log(`   Rama: ${RAMA}`);
    console.log(`   Ramas autorizadas: ${RAMAS_AUTORIZADAS.join(', ')}`);
    
    // Contar triggers
    const triggersExistentes = ScriptApp.getProjectTriggers();
    const triggersTelegram = triggersExistentes.filter(t => 
      t.getHandlerFunction().includes('Telegram') || 
      t.getHandlerFunction().includes('cumpleanos') ||
      t.getHandlerFunction().includes('ingresos')
    ).length;
    const triggersMessenger = triggersExistentes.filter(t => 
      t.getHandlerFunction().includes('Messenger')
    ).length;
    
    console.log("\n⏰ TRIGGERS CONFIGURADOS:");
    console.log(`   Telegram: ${triggersTelegram}`);
    console.log(`   Messenger: ${triggersMessenger}`);
    
    // Evaluación general
    const plataformasHabilitadas = [];
    if (TELEGRAM_CONFIG.enabled) plataformasHabilitadas.push('Telegram');
    if (MESSENGER_CONFIG.enabled) plataformasHabilitadas.push('Messenger');
    
    console.log("\n📱 RESUMEN:");
    console.log(`   Plataformas habilitadas: ${plataformasHabilitadas.join(', ')}`);
    console.log(`   Total triggers: ${triggersTelegram + triggersMessenger}`);
    
    if (plataformasHabilitadas.length === 0) {
      console.log("⚠️ ADVERTENCIA: Ninguna plataforma habilitada");
    } else {
      console.log(`✅ Sistema funcionando en ${plataformasHabilitadas.length} plataforma(s)`);
    }
    
    return {
      success: true,
      plataformasHabilitadas: plataformasHabilitadas,
      telegramEnabled: TELEGRAM_CONFIG.enabled,
      messengerEnabled: MESSENGER_CONFIG.enabled,
      triggersTotal: triggersTelegram + triggersMessenger
    };
    
  } catch (error) {
    console.error("❌ Error al verificar estado global:", error.toString());
    return { success: false, error: error.toString() };
  }
}
