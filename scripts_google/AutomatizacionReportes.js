/**
 * SCRIPT DE AUTOMATIZACIÓN DE REPORTES MISIONALES
 * 
 * Este script proporciona funciones para programar el envío automático
 * de reportes misionales en PDF y gestionar los triggers correspondientes.
 * 
 * FUNCIONES PRINCIPALES:
 * - Configurar triggers para envío automático
 * - Gestionar programación semanal/mensual
 * - Funciones de utilidad para administración
 * 
 * CONFIGURACIÓN:
 * - Se basa en la configuración de Config.js
 * - Permite personalizar frecuencia y horarios
 * 
 * USO:
 * - Ejecutar configurarEnvioAutomatico() para configurar triggers
 * - Usar funciones de gestión para modificar programación
 * 
 * @author CCM Scripts
 * @version 1.0
 */

/**
 * Configura el envío automático de reportes misionales
 * @param {string} frecuencia - 'semanal', 'mensual' o 'personalizada'
 * @param {Object} opciones - Opciones adicionales de configuración
 */
function configurarEnvioAutomatico(frecuencia = 'semanal', opciones = {}) {
  console.log(`Configurando envío automático con frecuencia: ${frecuencia}`);
  
  try {
    // Eliminar triggers existentes para evitar duplicados
    eliminarTriggersReportes();
    
    let trigger;
    
    switch (frecuencia) {
      case 'semanal':
        // Envío cada domingo a las 18:00
        trigger = ScriptApp.newTrigger('enviarReportesPDFCompleto')
          .timeBased()
          .everyWeeks(1)
          .onWeekDay(ScriptApp.WeekDay.SUNDAY)
          .atHour(18)
          .create();
        console.log("Trigger semanal configurado: Domingos a las 18:00");
        break;
        
      case 'mensual':
        // Envío el primer domingo de cada mes a las 18:00
        trigger = ScriptApp.newTrigger('enviarReportesPDFCompleto')
          .timeBased()
          .onMonthlyWeekDay(ScriptApp.WeekDay.SUNDAY, 1)
          .atHour(18)
          .create();
        console.log("Trigger mensual configurado: Primer domingo del mes a las 18:00");
        break;
        
      case 'personalizada':
        // Usar opciones personalizadas
        if (opciones.diaSemana && opciones.hora) {
          trigger = ScriptApp.newTrigger('enviarReportesPDFCompleto')
            .timeBased()
            .everyWeeks(opciones.semanas || 1)
            .onWeekDay(opciones.diaSemana)
            .atHour(opciones.hora)
            .create();
          console.log(`Trigger personalizado configurado: ${opciones.diaSemana} a las ${opciones.hora}:00`);
        } else {
          throw new Error("Para frecuencia personalizada se requieren 'diaSemana' y 'hora' en opciones");
        }
        break;
        
      default:
        throw new Error(`Frecuencia no válida: ${frecuencia}`);
    }
    
    // Guardar configuración en PropertiesService para referencia
    const configuracion = {
      frecuencia: frecuencia,
      fechaConfiguracion: new Date().toISOString(),
      triggerId: trigger.getUniqueId(),
      opciones: opciones
    };
    
    PropertiesService.getScriptProperties().setProperty(
      'CONFIG_ENVIO_AUTOMATICO', 
      JSON.stringify(configuracion)
    );
    
    console.log("Configuración guardada exitosamente");
    
    return {
      exito: true,
      mensaje: `Envío automático configurado (${frecuencia})`,
      triggerId: trigger.getUniqueId(),
      configuracion: configuracion
    };
    
  } catch (error) {
    console.error("Error configurando envío automático:", error);
    return {
      exito: false,
      mensaje: "Error al configurar envío automático",
      error: error.toString()
    };
  }
}

/**
 * Elimina todos los triggers relacionados con reportes
 */
function eliminarTriggersReportes() {
  const triggers = ScriptApp.getProjectTriggers();
  
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'enviarReportesPDFCompleto') {
      ScriptApp.deleteTrigger(trigger);
      console.log(`Trigger eliminado: ${trigger.getUniqueId()}`);
    }
  });
  
  // Limpiar configuración guardada
  PropertiesService.getScriptProperties().deleteProperty('CONFIG_ENVIO_AUTOMATICO');
  
  console.log("Todos los triggers de reportes eliminados");
}

/**
 * Obtiene la configuración actual del envío automático
 */
function obtenerConfiguracionActual() {
  try {
    const configGuardada = PropertiesService.getScriptProperties().getProperty('CONFIG_ENVIO_AUTOMATICO');
    
    if (!configGuardada) {
      return {
        configurado: false,
        mensaje: "No hay configuración de envío automático"
      };
    }
    
    const config = JSON.parse(configGuardada);
    
    // Verificar si el trigger aún existe
    const triggers = ScriptApp.getProjectTriggers();
    const triggerExiste = triggers.some(t => t.getUniqueId() === config.triggerId);
    
    return {
      configurado: triggerExiste,
      configuracion: config,
      estadoTrigger: triggerExiste ? "Activo" : "Eliminado",
      totalTriggers: triggers.filter(t => t.getHandlerFunction() === 'enviarReportesPDFCompleto').length
    };
    
  } catch (error) {
    console.error("Error obteniendo configuración:", error);
    return {
      configurado: false,
      error: error.toString()
    };
  }
}

/**
 * Lista todos los triggers activos del proyecto
 */
function listarTriggersActivos() {
  const triggers = ScriptApp.getProjectTriggers();
  
  const triggersInfo = triggers.map(trigger => {
    return {
      id: trigger.getUniqueId(),
      funcion: trigger.getHandlerFunction(),
      tipo: trigger.getTriggerSource().toString(),
      evento: trigger.getEventType().toString()
    };
  });
  
  console.log("Triggers activos:", triggersInfo);
  return triggersInfo;
}

/**
 * Ejecuta una prueba de envío sin programar triggers
 */
function pruebaEnvioManual() {
  console.log("=== INICIANDO PRUEBA DE ENVÍO MANUAL ===");
  
  try {
    // Verificar configuración
    console.log("1. Verificando configuración...");
    const pruebaConfig = probarConfiguracionReportes();
    console.log("Resultado prueba configuración:", pruebaConfig);
    
    // Enviar solo un reporte de prueba
    console.log("2. Enviando Branch in a Glance como prueba...");
    const resultado = enviarReporteIndividual('branchInAGlance');
    
    console.log("3. Resultado del envío de prueba:", resultado);
    
    if (resultado.exito) {
      console.log("✓ Prueba exitosa - El sistema está funcionando correctamente");
      return {
        exito: true,
        mensaje: "Prueba de envío completada exitosamente",
        detalle: resultado
      };
    } else {
      console.log("✗ Prueba falló - Revisar configuración");
      return {
        exito: false,
        mensaje: "Prueba de envío falló",
        error: resultado.error
      };
    }
    
  } catch (error) {
    console.error("Error en prueba de envío:", error);
    return {
      exito: false,
      mensaje: "Error en prueba de envío",
      error: error.toString()
    };
  }
}

/**
 * Funciones de utilidad para días de la semana
 */
const DIAS_SEMANA = {
  DOMINGO: ScriptApp.WeekDay.SUNDAY,
  LUNES: ScriptApp.WeekDay.MONDAY,
  MARTES: ScriptApp.WeekDay.TUESDAY,
  MIERCOLES: ScriptApp.WeekDay.WEDNESDAY,
  JUEVES: ScriptApp.WeekDay.THURSDAY,
  VIERNES: ScriptApp.WeekDay.FRIDAY,
  SABADO: ScriptApp.WeekDay.SATURDAY
};

/**
 * Configura envío personalizado con parámetros específicos
 * @param {string} dia - Día de la semana (usar DIAS_SEMANA)
 * @param {number} hora - Hora del día (0-23)
 * @param {number} semanas - Intervalo en semanas (1 = semanal, 2 = quincenal, etc.)
 */
function configurarEnvioPersonalizado(dia, hora, semanas = 1) {
  if (!DIAS_SEMANA[dia.toUpperCase()]) {
    throw new Error(`Día no válido: ${dia}. Usar: ${Object.keys(DIAS_SEMANA).join(', ')}`);
  }
  
  if (hora < 0 || hora > 23) {
    throw new Error("Hora debe estar entre 0 y 23");
  }
  
  return configurarEnvioAutomatico('personalizada', {
    diaSemana: DIAS_SEMANA[dia.toUpperCase()],
    hora: hora,
    semanas: semanas
  });
}

/**
 * Función de emergencia para detener todos los envíos automáticos
 */
function detenerTodosLosEnvios() {
  console.log("DETENCIÓN DE EMERGENCIA - Eliminando todos los triggers");
  
  eliminarTriggersReportes();
  
  // Enviar notificación al administrador
  try {
    GmailApp.sendEmail(
      CORREO_PERSONAL,
      "[CCM Scripts] ALERTA: Envíos automáticos detenidos",
      `Los envíos automáticos de reportes misionales han sido detenidos manualmente.
      
Fecha: ${new Date().toLocaleString()}
Acción: Detención de emergencia
      
Para reactivar, ejecutar configurarEnvioAutomatico() nuevamente.`,
      {
        from: CORREO_MISIONAL,
        name: REMITENTE_NOMBRE
      }
    );
  } catch (error) {
    console.error("Error enviando notificación de detención:", error);
  }
  
  return "Todos los envíos automáticos han sido detenidos";
}

/**
 * Función para programar envío inmediato (para pruebas)
 */
function programarEnvioInmediato() {
  console.log("Programando envío inmediato en 2 minutos...");
  
  try {
    const trigger = ScriptApp.newTrigger('enviarReportesPDFCompleto')
      .timeBased()
      .after(2 * 60 * 1000) // 2 minutos en milisegundos
      .create();
    
    console.log(`Trigger inmediato creado: ${trigger.getUniqueId()}`);
    
    return {
      exito: true,
      mensaje: "Envío programado para 2 minutos",
      triggerId: trigger.getUniqueId()
    };
    
  } catch (error) {
    console.error("Error programando envío inmediato:", error);
    return {
      exito: false,
      error: error.toString()
    };
  }
}
