/**
 * SCRIPT DE CORREOS AUTOMÁTICOS DE CUMPLEAÑOS PARA MISIONEROS CCM
 * 
 * Sistema automatizado para envío de correos de cumpleaños personalizados
 * a misioneros según su estatus y rama asignada.
 * 
 * CARACTERÍSTICAS:
 * - Envío automático diario de correos de cumpleaños
 * - Personalización según género (Élder/Hermana)
 * - Filtrado por rama y estatus de misionero
 * - Modo de prueba para testing seguro
 * - Manejo de errores y logging detallado
 * - Soporte para múltiples ramas y estatus
 * 
 * FUNCIONES PRINCIPALES:
 * - enviarCorreosCumpleanos(): Proceso principal diario
 * - probarCorreosCumpleanos(): Función de prueba con datos simulados
 * - obtenerEstadisticasCumpleanos(): Estadísticas para análisis
 * 
 * CONFIGURACIÓN:
 * - Base de datos: dbConfig (Config.js)
 * - Remitente: REMITENTE_EMAIL, REMITENTE_NOMBRE (Config.js)
 * - Scope: RAMAS_AUTORIZADAS, CONFIG_ESTATUS_POR_RAMA (Config.js)
 * 
 * MODO PRUEBA:
 * - Cambiar MODO_PRUEBA a true para testing
 * - Configurar CORREO_PRUEBA y otros parámetros de prueba
 * 
 * USO:
 * - Ejecutar enviarCorreosCumpleanos() con trigger diario a las 6:00 AM
 * - Usar probarCorreosCumpleanos() para pruebas
 * 
 * @author CCM Scripts
 * @version 4.0
 */

// === CONFIGURACIÓN DE MODO PRUEBA ===
const MODO_PRUEBA = false; // Cambiar a false para producción
const SIMULAR_HERMANA = false; // true para hermana, false para élder
const CORREO_PRUEBA = "jpmarichal@gmail.com"; // Tu correo para recibir las pruebas
const NOMBRE_PRUEBA = "Juan Pablo Marichal"; // Tu nombre para la prueba

// === CONFIGURACIÓN DE SCOPE DE DESTINATARIOS ===
// Todas las variables de configuración están centralizadas en Config.js

/**
 * Función principal que se debe ejecutar diariamente
 * Se recomienda configurar un trigger diario a las 6:00 AM
 */
function enviarCorreosCumpleanos() {
  console.log("🎂 Iniciando proceso de correos de cumpleaños");
  
  if (MODO_PRUEBA) {
    console.log("🧪 *** MODO PRUEBA ACTIVADO ***");
    console.log(`📧 Los correos se enviarán a: ${CORREO_PRUEBA}`);
    console.log(`👤 Simulando: ${SIMULAR_HERMANA ? 'Hermana' : 'Élder'}`);
    
    // En modo prueba, usar datos simulados
    const misioneroSimulado = crearMisioneroSimulado();
    console.log(`📋 Datos simulados: ${misioneroSimulado.nombre} (Rama ${misioneroSimulado.rama}, ${misioneroSimulado.status})`);
    
    try {
      enviarCorreoIndividual(misioneroSimulado);
      console.log(`✅ Correo de prueba enviado exitosamente a ${CORREO_PRUEBA}`);
      console.log(`🎉 Proceso de prueba completado`);
    } catch (error) {
      console.error(`❌ Error enviando correo de prueba: ${error.message}`);
    }
    
    return;
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
    
    // Obtener misioneros que cumplen años hoy
    const cumpleaneros = obtenerCumpleanerosHoy(conn);
    console.log(`📋 Encontrados ${cumpleaneros.length} misioneros que cumplen años hoy`);
    
    // Validar si hay cumpleañeros
    if (cumpleaneros.length === 0) {
      console.log("ℹ️ No hay misioneros que cumplan años hoy en las ramas autorizadas");
      console.log(`🎯 Ramas monitoreadas: ${RAMAS_AUTORIZADAS.join(', ')}`);
      RAMAS_AUTORIZADAS.forEach(rama => {
        console.log(`   Rama ${rama}: ${obtenerEstatusValidosPorRama(rama).join(', ')}`);
      });
      console.log("✅ Proceso completado exitosamente - Sin cumpleañeros hoy");
      return; // Terminar elegantemente
    }
    
    // Enviar correos
    let enviadosExitosos = 0;
    for (const misionero of cumpleaneros) {
      try {
        enviarCorreoIndividual(misionero);
        enviadosExitosos++;
        console.log(`✅ Correo enviado a ${misionero.nombre} (Rama ${misionero.rama}, ${misionero.status})`);
      } catch (error) {
        // Pausa incluso si hay un error para no sobrecargar en caso de fallos repetidos
        Utilities.sleep(1000); 
        console.error(`❌ Error enviando correo a ${misionero.nombre}: ${error.message}`);
      }
    }
    
    console.log(`🎉 Proceso completado: ${enviadosExitosos}/${cumpleaneros.length} correos enviados exitosamente`);
    
  } catch (error) {
    console.error(`❌ Error crítico: ${error.message}`);
    throw error;
  } finally {
    if (conn && !conn.isClosed()) {
      conn.close();
    }
  }
}

/**
 * Crea un misionero simulado para pruebas
 */
function crearMisioneroSimulado() {
  const esTresSemanas = Math.random() < 0.3; // 30% probabilidad de ser de 3 semanas
  const rama = RAMAS_AUTORIZADAS[Math.floor(Math.random() * RAMAS_AUTORIZADAS.length)];
  const estatusValidos = obtenerEstatusValidosPorRama(rama);
  const status = estatusValidos[Math.floor(Math.random() * estatusValidos.length)];
  
  // Generar tratamiento correcto
  let tratamiento;
  if (SIMULAR_HERMANA) {
    const apellido = NOMBRE_PRUEBA.split(' ')[1] || NOMBRE_PRUEBA.split(' ')[0];
    tratamiento = `Hermana ${apellido}`;
  } else {
    const apellido = NOMBRE_PRUEBA.split(' ')[1] || NOMBRE_PRUEBA.split(' ')[0];
    tratamiento = `Élder ${apellido}`;
  }
  
  return {
    id: 999999,
    tipo: SIMULAR_HERMANA ? 'Sis' : 'Eld',
    tratamiento: tratamiento,
    nombre: NOMBRE_PRUEBA,
    nuevaEdad: 20 + Math.floor(Math.random() * 5), // Edad entre 20-24
    tresSemanas: esTresSemanas,
    correoMisional: CORREO_PRUEBA,
    correoPersonal: CORREO_PRUEBA,
    status: status,
    rama: rama
  };
}

/**
 * Obtiene los misioneros que cumplen años hoy (utilizando vwCumpleanerosDeHoy)
 */
function obtenerCumpleanerosHoy(conn) {
  // Construir condiciones dinámicas para cada rama autorizada
  const condicionesRama = RAMAS_AUTORIZADAS.map(rama => {
    const estatusValidos = obtenerEstatusValidosPorRama(rama);
    const estatusString = estatusValidos.map(s => `'${s}'`).join(',');
    return `(m.Rama = ${rama} AND m.Status IN (${estatusString}))`;
  }).join(' OR ');

  const sql = `
    SELECT 
      m.ID,
      m.Tipo,
      m.Tratamiento,
      m.Nombre_del_misionero,
      m.Nueva_Edad,
      m.tres_semanas,
      m.Correo_Misional,
      m.Correo_Personal,
      m.Status,
      m.Rama
    FROM vwCumpleanerosDeHoy m
    WHERE (${condicionesRama})
  `;
  
  console.log(`📋 Consulta SQL generada: ${sql}`);
  
  const stmt = conn.createStatement();
  const results = stmt.executeQuery(sql);
  const cumpleaneros = [];
  
  while (results.next()) {
    cumpleaneros.push({
      id: results.getInt('ID'),
      tipo: results.getString('Tipo'),
      tratamiento: results.getString('Tratamiento'),
      nombre: results.getString('Nombre_del_misionero'),
      nuevaEdad: results.getInt('Nueva_Edad'),
      tresSemanas: results.getBoolean('tres_semanas'),
      correoMisional: results.getString('Correo_Misional'),
      correoPersonal: results.getString('Correo_Personal'),
      status: results.getString('Status'),
      rama: results.getInt('Rama')
    });
  }
  
  results.close();
  stmt.close();
  return cumpleaneros;
}

/**
 * Envía el correo de cumpleaños personalizado a un misionero individual
 */
function enviarCorreoIndividual(misionero) {
  console.log("📨 Iniciando envío de correo...");
  
  const esHermana = misionero.tipo === 'Sis';
  const esTresSemanas = misionero.tresSemanas;
  
  console.log(`👤 Procesando: ${esHermana ? 'Hermana' : 'Élder'} (${misionero.tratamiento})`);
  
  // En modo prueba, usar correo de prueba
  const correoDestino = MODO_PRUEBA ? CORREO_PRUEBA : misionero.correoMisional;
  const correoPersonal = MODO_PRUEBA ? null : misionero.correoPersonal; // No usar BCC en pruebas
  
  console.log(`📧 Correo destino: ${correoDestino}`);
  
  if (!correoDestino) {
    throw new Error('No se encontró correo de destino');
  }
  
  // Generar contenido del mensaje
  console.log("📝 Generando contenido del mensaje...");
  const { asunto, cuerpoHtml } = generarMensajeCumpleanos(misionero, esHermana, esTresSemanas);
  console.log(`📋 Asunto generado: ${asunto}`);
  
  // Configurar opciones de envío
  const opciones = {
    htmlBody: cuerpoHtml,
    name: REMITENTE_NOMBRE,
    from: REMITENTE_EMAIL
  };
  
  // Agregar BCC al correo personal si existe y no estamos en modo prueba
  if (!MODO_PRUEBA && correoPersonal && correoPersonal !== correoDestino) {
    opciones.bcc = correoPersonal;
  }
  
  // Modificar asunto en modo prueba
  const asuntoFinal = MODO_PRUEBA ? `[PRUEBA] ${asunto}` : asunto;
  console.log(`📮 Asunto final: ${asuntoFinal}`);
  
  // Enviar correo usando Gmail directamente
  console.log("🚀 Enviando correo vía Gmail...");
  GmailApp.sendEmail(
    correoDestino,
    asuntoFinal,
    '', // texto plano (vacío porque usamos HTML)
    opciones
  );
  console.log("✅ Correo enviado exitosamente");
}

/**
 * Genera el mensaje personalizado de cumpleaños
 */
function generarMensajeCumpleanos(misionero, esHermana, esTresSemanas) {
  const tratamiento = misionero.tratamiento || (esHermana ? 'Hermana' : 'Élder');
  const edad = misionero.nuevaEdad;
  
  // Seleccionar pasaje bíblico aleatorio
  const pasaje = seleccionarPasajeBiblico();
  
  // Generar asunto (sin emojis para mejor compatibilidad)
  const asunto = `¡Feliz Cumpleaños ${tratamiento}!`;
  
  let cuerpoHtml;
  
  if (esTresSemanas) {
    // Misioneros de tres semanas: español primero, inglés segundo
    cuerpoHtml = generarMensajeEspanolIngles(tratamiento, edad, pasaje, esHermana);
  } else {
    // Misioneros regulares: inglés primero, español segundo
    cuerpoHtml = generarMensajeInglesEspanol(tratamiento, edad, pasaje, esHermana);
  }
  
  return { asunto, cuerpoHtml };
}

/**
 * Convierte emojis a códigos HTML para mejor compatibilidad
 */
function convertirEmojisAHTML(texto) {
  return texto
    .replace(/🎂/g, '&#127874;')
    .replace(/🎉/g, '&#127881;')
    .replace(/🎈/g, '&#127880;')
    .replace(/💫/g, '&#128171;')
    .replace(/🎊/g, '&#127882;')
    .replace(/💙/g, '&#128153;')
    .replace(/📧/g, '&#128231;')
    .replace(/🌟/g, '&#127775;');
}

/**
 * Genera mensaje con español primero (para misioneros de 3 semanas)
 */
function generarMensajeEspanolIngles(tratamiento, edad, pasaje, esHermana) {
  const pronombre = esHermana ? 'querida' : 'querido';
  const genero = esHermana ? 'a' : 'o';
  
  const contenido = `
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
      <div style="background: linear-gradient(135deg, #1f4e79, #2e5984); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="margin: 0; font-size: 28px;">🎂 ¡Feliz Cumpleaños! 🎉</h1>
      </div>
      
      <div style="padding: 30px; background: white; border-radius: 0 0 10px 10px;">
        <!-- MENSAJE EN ESPAÑOL -->
        <div style="margin-bottom: 40px;">
          <h2 style="color: #1f4e79; margin-bottom: 20px;">🌟 Mensaje en Español</h2>
          <p style="font-size: 16px; line-height: 1.6;">
            ${pronombre.charAt(0).toUpperCase() + pronombre.slice(1)} ${tratamiento},
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            ¡Hoy es un día muy especial! 🎈 En este ${edad}º cumpleaños, queremos que sepa lo mucho que valoramos su servicio al estar dedicad${genero} en la obra del Señor. 
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Su ejemplo de fe, obediencia y amor por los demás es una inspiración para todos nosotros en el Centro de Capacitación Misional. 💫
          </p>
          <div style="background: #e8f4f8; padding: 20px; border-left: 4px solid #1f4e79; margin: 20px 0;">
            <p style="font-style: italic; margin: 0; color: #2c3e50;">
              <strong>Escritura para reflexionar:</strong><br>
              "${pasaje.texto}"<br>
              <small>— ${pasaje.referencia}</small>
            </p>
          </div>
          <p style="font-size: 16px; line-height: 1.6;">
            Que el Señor continúe bendiciéndol${genero} en este nuevo año de vida y en su servicio misional. ¡Disfrute su día especial! 🎊
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Con cariño y mejores deseos,<br>
            <strong>Presidente Marichal</strong><br>
            <em>Primer Consejero de la Presidencia de Rama</em><br>
            <em>Rama 14 CCM</em><br>
            <small>📧 CCM: ${CORREO_MISIONAL}</small><br>
            <small>📧 Personal: ${CORREO_PERSONAL}</small> 💙
          </p>
        </div>
        
        <hr style="border: none; height: 2px; background: linear-gradient(to right, #1f4e79, #e0e0e0, #1f4e79); margin: 40px 0;">
        
        <!-- MENSAJE EN INGLÉS -->
        <div>
          <h2 style="color: #1f4e79; margin-bottom: 20px;">🌟 English Message</h2>
          <p style="font-size: 16px; line-height: 1.6;">
            Dear ${tratamiento},
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Today is a very special day! 🎈 On this ${edad}${getOrdinalSuffix(edad)} birthday, we want you to know how much we value your dedicated service in the Lord's work.
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Your example of faith, obedience, and love for others is an inspiration to all of us at the Missionary Training Center. 💫
          </p>
          <div style="background: #e8f4f8; padding: 20px; border-left: 4px solid #1f4e79; margin: 20px 0;">
            <p style="font-style: italic; margin: 0; color: #2c3e50;">
              <strong>Scripture to ponder:</strong><br>
              "${pasaje.textoIngles}"<br>
              <small>— ${pasaje.referencia}</small>
            </p>
          </div>
          <p style="font-size: 16px; line-height: 1.6;">
            May the Lord continue to bless you in this new year of life and in your missionary service. Enjoy your special day! 🎊
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            With love and best wishes,<br>
            <strong>President Marichal</strong><br>
            <em>First Counselor in the Branch Presidency</em><br>
            <em>Branch 14 MTC</em><br>
            <small>📧 MTC: ${CORREO_MISIONAL}</small><br>
            <small>📧 Personal: ${CORREO_PERSONAL}</small> 💙
          </p>
        </div>
      </div>
      
      <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
        Centro de Capacitación Misional
      </div>
    </div>
    </body>
    </html>
  `;
  
  return convertirEmojisAHTML(contenido);
}

/**
 * Genera mensaje con inglés primero (para misioneros regulares)
 */
function generarMensajeInglesEspanol(tratamiento, edad, pasaje, esHermana) {
  const pronombre = esHermana ? 'querida' : 'querido';
  const genero = esHermana ? 'a' : 'o';
  
  const contenido = `
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f8f9fa;">
      <div style="background: linear-gradient(135deg, #1f4e79, #2e5984); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="margin: 0; font-size: 28px;">🎂 Happy Birthday! 🎉</h1>
      </div>
      
      <div style="padding: 30px; background: white; border-radius: 0 0 10px 10px;">
        <!-- MENSAJE EN INGLÉS -->
        <div style="margin-bottom: 40px;">
          <h2 style="color: #1f4e79; margin-bottom: 20px;">🌟 English Message</h2>
          <p style="font-size: 16px; line-height: 1.6;">
            Dear ${tratamiento},
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Today is a very special day! 🎈 On this ${edad}${getOrdinalSuffix(edad)} birthday, we want you to know how much we value your dedicated service in the Lord's work.
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Your example of faith, obedience, and love for others is an inspiration to all of us at the Missionary Training Center. 💫
          </p>
          <div style="background: #e8f4f8; padding: 20px; border-left: 4px solid #1f4e79; margin: 20px 0;">
            <p style="font-style: italic; margin: 0; color: #2c3e50;">
              <strong>Scripture to ponder:</strong><br>
              "${pasaje.textoIngles}"<br>
              <small>— ${pasaje.referencia}</small>
            </p>
          </div>
          <p style="font-size: 16px; line-height: 1.6;">
            May the Lord continue to bless you in this new year of life and in your missionary service. Enjoy your special day! 🎊
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            With love and best wishes,<br>
            <strong>President Marichal</strong><br>
            <em>First Counselor in the Branch Presidency</em><br>
            <em>Branch 14 MTC</em><br>
            <small>📧 MTC: ${CORREO_MISIONAL}</small><br>
            <small>📧 Personal: ${CORREO_PERSONAL}</small> 💙
          </p>
        </div>
        
        <hr style="border: none; height: 2px; background: linear-gradient(to right, #1f4e79, #e0e0e0, #1f4e79); margin: 40px 0;">
        
        <!-- MENSAJE EN ESPAÑOL -->
        <div>
          <h2 style="color: #1f4e79; margin-bottom: 20px;">🌟 Mensaje en Español</h2>
          <p style="font-size: 16px; line-height: 1.6;">
            ${pronombre.charAt(0).toUpperCase() + pronombre.slice(1)} ${tratamiento},
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            ¡Hoy es un día muy especial! 🎈 En este ${edad}º cumpleaños, queremos que sepa lo mucho que valoramos su servicio dedicad${genero} en la obra del Señor.
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Su ejemplo de fe, obediencia y amor por los demás es una inspiración para todos nosotros en el Centro de Capacitación Misional. 💫
          </p>
          <div style="background: #e8f4f8; padding: 20px; border-left: 4px solid #1f4e79; margin: 20px 0;">
            <p style="font-style: italic; margin: 0; color: #2c3e50;">
              <strong>Escritura para reflexionar:</strong><br>
              "${pasaje.texto}"<br>
              <small>— ${pasaje.referencia}</small>
            </p>
          </div>
          <p style="font-size: 16px; line-height: 1.6;">
            Que el Señor continúe bendiciéndol${genero} en este nuevo año de vida y en su servicio misional. ¡Disfrute su día especial! 🎊
          </p>
          <p style="font-size: 16px; line-height: 1.6;">
            Con cariño y mejores deseos,<br>
            <strong>Presidente Marichal</strong><br>
            <em>Primer Consejero de la Presidencia de Rama</em><br>
            <em>Rama 14 CCM</em><br>
            <small>📧 CCM: ${CORREO_MISIONAL}</small><br>
            <small>📧 Personal: ${CORREO_PERSONAL}</small> 💙
          </p>
        </div>
      </div>
      
      <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
        Centro de Capacitación Misional
      </div>
    </div>
    </body>
    </html>
  `;
  
  return convertirEmojisAHTML(contenido);
}

/**
 * Selecciona un pasaje bíblico inspirador aleatorio
 */
function seleccionarPasajeBiblico() {
  const pasajes = [
    {
      referencia: "D. y C. 4:2",
      texto: "Por tanto, oh vosotros que os embarcáis en el servicio de Dios, mirad que le sirváis con todo vuestro corazón, alma, mente y fuerza, para que aparezcáis sin culpa ante Dios en el último día.",
      textoIngles: "Therefore, O ye that embark in the service of God, see that ye serve him with all your heart, might, mind and strength, that ye may stand blameless before God at the last day."
    },
    {
      referencia: "Alma 26:12",
      texto: "Sí, sé que nada soy; en cuanto a mi fuerza, soy débil; por tanto, no me gloriaré en mí mismo, sino que me gloriaré en mi Dios, porque con su fuerza puedo hacer todas las cosas.",
      textoIngles: "Yea, I know that I am nothing; as to my strength I am weak; therefore I will not boast of myself, but I will boast of my God, for in his strength I can do all things."
    },
    {
      referencia: "D. y C. 84:88",
      texto: "Y quien os reciba, allí estaré yo también, porque iré delante de vosotros. Estaré a vuestra derecha y a vuestra izquierda, y mi Espíritu estará en vuestros corazones, y mis ángeles os rodearán para sosteneros.",
      textoIngles: "And whoso receiveth you, there I will be also, for I will go before your face. I will be on your right hand and on your left, and my Spirit shall be in your hearts, and mine angels round about you, to bear you up."
    },
    {
      referencia: "1 Nefi 3:7",
      texto: "Y aconteció que yo, Nefi, dije a mi padre: Iré y haré lo que el Señor ha mandado, porque sé que él nunca da mandamientos a los hijos de los hombres sin antes prepararles la vía para que cumplan lo que les ha mandado.",
      textoIngles: "And it came to pass that I, Nephi, said unto my father: I will go and do the things which the Lord hath commanded, for I know that the Lord giveth no commandments unto the children of men, save he shall prepare a way for them that they may accomplish the thing which he commandeth them."
    },
    {
      referencia: "D. y C. 68:6",
      texto: "Por tanto, tened buen ánimo, y no temáis, porque yo, el Señor, estoy con vosotros y os sostendré; y daréis testimonio de mí, sí, Jesucristo, de que yo soy el Hijo del Dios viviente, que fui y que soy y que he de venir.",
      textoIngles: "Wherefore, be of good cheer, and do not fear, for I the Lord am with you, and will stand by you; and ye shall bear record of me, even Jesus Christ, that I am the Son of the living God, that I was, that I am, and that I am to come."
    },
    {
      referencia: "Isaías 6:8",
      texto: "Después oí la voz del Señor, que decía: ¿A quién enviaré, y quién irá por nosotros? Entonces respondí yo: Heme aquí, envíame a mí.",
      textoIngles: "Also I heard the voice of the Lord, saying, Whom shall I send, and who will go for us? Then said I, Here am I; send me."
    },
    {
      referencia: "Mateo 28:19-20",
      texto: "Por tanto, id, y haced discípulos a todas las naciones, bautizándolos en el nombre del Padre, y del Hijo, y del Espíritu Santo; enseñándoles que guarden todas las cosas que os he mandado; y he aquí yo estoy con vosotros todos los días, hasta el fin del mundo.",
      textoIngles: "Go ye therefore, and teach all nations, baptizing them in the name of the Father, and of the Son, and of the Holy Ghost: Teaching them to observe all things whatsoever I have commanded you: and, lo, I am with you always, even unto the end of the world."
    },
    {
      referencia: "D. y C. 100:7",
      texto: "Por tanto, no os preocupéis por el mañana, porque no sabéis lo que un día puede traer. Por tanto, no os angustiéis por el mañana. Dios os dará, en la hora misma, sí, en el momento preciso, lo que debéis decir.",
      textoIngles: "Therefore, take no thought for the morrow, for what ye shall eat, or what ye shall drink, or wherewithal ye shall be clothed. For, consider the lilies of the field, how they grow, they toil not, neither do they spin; and the kingdoms of the world, in all their glory, are not arrayed like one of these."
    }
  ];
  
  const indiceAleatorio = Math.floor(Math.random() * pasajes.length);
  return pasajes[indiceAleatorio];
}

/**
 * Obtiene el sufijo ordinal en inglés (st, nd, rd, th)
 */
function getOrdinalSuffix(num) {
  const j = num % 10;
  const k = num % 100;
  if (j == 1 && k != 11) return "st";
  if (j == 2 && k != 12) return "nd";
  if (j == 3 && k != 13) return "rd";
  return "th";
}

/**
 * Función para configurar el trigger automático diario
 * Ejecutar esta función UNA SOLA VEZ para configurar la automatización
 */
function configurarTriggerDiario() {
  // Eliminar triggers existentes para evitar duplicados
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'enviarCorreosCumpleanos') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // Crear nuevo trigger diario a las 6:00 AM
  ScriptApp.newTrigger('enviarCorreosCumpleanos')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();
  
  console.log('✅ Trigger diario configurado para las 6:00 AM');
}

/**
 * Función específica para ejecutar pruebas del sistema
 * Ejecuta esta función para probar el sistema sin afectar la base de datos
 */
function ejecutarPrueba() {
  try {
    console.log("🧪 ===== INICIANDO PRUEBA DEL SISTEMA =====");
    
    // Verificar configuración
    console.log(`📧 Correo de prueba: ${CORREO_PRUEBA}`);
    console.log(`👤 Tipo de misionero: ${SIMULAR_HERMANA ? 'Hermana' : 'Élder'}`);
    console.log(`🏢 Ramas autorizadas: ${RAMAS_AUTORIZADAS.join(', ')}`);
    
    // Crear misionero simulado
    console.log("📋 Creando misionero simulado...");
    const misioneroSimulado = crearMisioneroSimulado();
    console.log("📋 Datos del misionero simulado:");
    console.log(`   Nombre: ${misioneroSimulado.nombre}`);
    console.log(`   Tipo: ${misioneroSimulado.tipo} (${misioneroSimulado.tratamiento})`);
    console.log(`   Edad: ${misioneroSimulado.nuevaEdad} años`);
    console.log(`   Tres semanas: ${misioneroSimulado.tresSemanas ? 'Sí' : 'No'}`);
    console.log(`   Rama: ${misioneroSimulado.rama}`);
    console.log(`   Status: ${misioneroSimulado.status}`);
    console.log(`   Orden del mensaje: ${misioneroSimulado.tresSemanas ? 'Español → Inglés' : 'Inglés → Español'}`);
    
    // Enviar correo de prueba
    console.log("📤 Enviando correo de prueba...");
    enviarCorreoIndividual(misioneroSimulado);
    console.log("✅ ¡Correo de prueba enviado exitosamente!");
    console.log(`📬 Revisa tu bandeja de entrada en: ${CORREO_PRUEBA}`);
    console.log("🎉 Prueba completada exitosamente");
    
  } catch (error) {
    console.error(`❌ Error en la prueba: ${error.message}`);
    console.error(`❌ Stack trace: ${error.stack}`);
    console.error("🔧 Verifica las configuraciones y permisos de Gmail");
    throw error; // Re-lanzar el error para que se vea en los logs
  }
  
  console.log("🧪 ===== FIN DE LA PRUEBA =====");
}

/**
 * Función para probar el envío de correos (solo para testing)
 * Busca misioneros que cumplieron años en los últimos 7 días
 */
function probarEnvioCorreos() {
  console.log("🧪 Función de prueba - buscando cumpleañeros recientes");
  let conn;
  
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    // Establecer collation para la sesión
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    // Construir condiciones dinámicas para cada rama autorizada
    const condicionesRama = RAMAS_AUTORIZADAS.map(rama => {
      const estatusValidos = obtenerEstatusValidosPorRama(rama);
      const estatusString = estatusValidos.map(s => `'${s}'`).join(',');
      return `(m.Rama = ${rama} AND m.Status IN (${estatusString}))`;
    }).join(' OR ');
    
    // Buscar misioneros que cumplieron años en los últimos 7 días
    // Nota: Esta función usa vwMisioneros directamente porque busca cumpleaños pasados, 
    // no del día siguiente como la función principal
    const sql = `
      SELECT 
        m.ID,
        m.Tipo,
        m.Tratamiento,
        m.Nombre_del_misionero,
        m.Edad + 1 as Nueva_Edad,
        m.tres_semanas,
        m.Correo_Misional,
        m.Correo_Personal,
        m.Status,
        m.Rama,
        m.Fecha_nacimiento
      FROM vwMisioneros m
      WHERE (${condicionesRama})
      AND m.Correo_Misional IS NOT NULL
      AND (
        (DAYOFYEAR(m.Fecha_nacimiento) BETWEEN DAYOFYEAR(CURDATE() - INTERVAL 7 DAY) AND DAYOFYEAR(CURDATE()))
        OR 
        (MONTH(m.Fecha_nacimiento) = MONTH(CURDATE()) AND DAY(m.Fecha_nacimiento) <= DAY(CURDATE()))
      )
      LIMIT 1
    `;
    
    console.log(`🔍 Consulta de prueba: ${sql}`);
    
    const stmt = conn.createStatement();
    const results = stmt.executeQuery(sql);
    
    if (results.next()) {
      const misionero = {
        id: results.getInt('ID'),
        tipo: results.getString('Tipo'),
        tratamiento: results.getString('Tratamiento'),
        nombre: results.getString('Nombre_del_misionero'),
        nuevaEdad: results.getInt('Nueva_Edad'),
        tresSemanas: results.getBoolean('tres_semanas'),
        correoMisional: results.getString('Correo_Misional'),
        correoPersonal: results.getString('Correo_Personal'),
        status: results.getString('Status'),
        rama: results.getInt('Rama')
      };
      
      console.log(`🎯 Enviando correo de prueba a: ${misionero.nombre} (Rama ${misionero.rama}, ${misionero.status})`);
      enviarCorreoIndividual(misionero);
      console.log("✅ Correo de prueba enviado exitosamente");
    } else {
      console.log("⚠️ No se encontraron misioneros para la prueba en las ramas autorizadas");
      console.log(`📋 Ramas autorizadas: ${RAMAS_AUTORIZADAS.join(', ')}`);
      RAMAS_AUTORIZADAS.forEach(rama => {
        console.log(`   Rama ${rama}: ${obtenerEstatusValidosPorRama(rama).join(', ')}`);
      });
    }
    
    results.close();
    stmt.close();
    
  } catch (error) {
    console.error(`❌ Error en prueba: ${error.message}`);
  } finally {
    if (conn && !conn.isClosed()) {
      conn.close();
    }
  }
}

/**
 * Función para cambiar entre modo prueba y producción
 * No modifica el archivo, solo para verificar configuración actual
 */
function verificarConfiguracion() {
  console.log("⚙️ ===== CONFIGURACIÓN ACTUAL =====");
  console.log(`🔧 Modo prueba: ${MODO_PRUEBA ? 'ACTIVADO' : 'DESACTIVADO'}`);
  console.log(`👤 Simulación: ${SIMULAR_HERMANA ? 'Hermana' : 'Élder'}`);
  console.log(`📧 Correo de prueba: ${CORREO_PRUEBA}`);
  console.log(`👤 Nombre de prueba: ${NOMBRE_PRUEBA}`);
  console.log(`🏢 Ramas autorizadas: ${RAMAS_AUTORIZADAS.join(', ')}`);
  
  console.log("\n📋 Estatus por rama:");
  RAMAS_AUTORIZADAS.forEach(rama => {
    console.log(`   Rama ${rama}: ${obtenerEstatusValidosPorRama(rama).join(', ')}`);
  });
  
  console.log(`\n📤 Remitente: ${REMITENTE_NOMBRE} <${REMITENTE_EMAIL}>`);
  console.log(`📧 Correo personal: ${CORREO_PERSONAL}`);
  
  if (MODO_PRUEBA) {
    console.log("\n⚠️ RECORDATORIO: Para usar en producción, cambia MODO_PRUEBA a false");
    console.log("📝 Para cambiar el tipo de misionero simulado, modifica SIMULAR_HERMANA");
  } else {
    console.log("\n✅ Configurado para producción");
    console.log("🗓️ Se ejecutará automáticamente con el trigger diario a las 6:00 AM");
  }
  
  console.log("⚙️ ===== FIN CONFIGURACIÓN =====");
}

/**
 * Función para obtener estadísticas de cumpleaños próximos
 */
function obtenerEstadisticasCumpleanos() {
  let conn;
  
  try {
    const url = `jdbc:mysql://${dbConfig.host}:${dbConfig.port}/${dbConfig.dbName}?useUnicode=true&characterEncoding=utf8`;
    conn = Jdbc.getConnection(url, dbConfig.user, dbConfig.password);
    
    // Establecer collation para la sesión
    const collationStmt = conn.createStatement();
    collationStmt.execute("SET collation_connection = utf8mb4_unicode_ci");
    collationStmt.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci");
    collationStmt.close();
    
    // Construir condiciones dinámicas para cada rama autorizada
    const condicionesRama = RAMAS_AUTORIZADAS.map(rama => {
      const estatusValidos = obtenerEstatusValidosPorRama(rama);
      const estatusString = estatusValidos.map(s => `'${s}'`).join(',');
      return `(e.Rama = ${rama} AND e.Status IN (${estatusString}))`;
    }).join(' OR ');
    
    const sql = `
      SELECT 
        e.Fecha_Cumple,
        e.Rama,
        e.Cantidad,
        e.Misioneros
      FROM vwEstadisticasCumpleanos e
      WHERE (${condicionesRama})
      ORDER BY 
        CASE 
          WHEN e.Mes = MONTH(CURDATE()) THEN 1
          WHEN e.Mes = MONTH(DATE_ADD(CURDATE(), INTERVAL 1 MONTH)) THEN 2
          ELSE 3
        END,
        e.Dia,
        e.Rama
    `;
    
    const stmt = conn.createStatement();
    const results = stmt.executeQuery(sql);
    
    console.log("📊 Próximos cumpleaños (filtrado por ramas autorizadas):");
    console.log("========================================================");
    console.log(`🎯 Ramas incluidas: ${RAMAS_AUTORIZADAS.join(', ')}`);
    RAMAS_AUTORIZADAS.forEach(rama => {
      console.log(`   Rama ${rama}: ${obtenerEstatusValidosPorRama(rama).join(', ')}`);
    });
    console.log("========================================================");
    
    while (results.next()) {
      const fecha = results.getString('Fecha_Cumple');
      const rama = results.getInt('Rama');
      const cantidad = results.getInt('Cantidad');
      const misioneros = results.getString('Misioneros');
      
      console.log(`${fecha} - Rama ${rama}: ${cantidad} misionero(s)`);
      console.log(`   ${misioneros}`);
      console.log("");
    }
    
    results.close();
    stmt.close();
    
  } catch (error) {
    console.error(`❌ Error obteniendo estadísticas: ${error.message}`);
  } finally {
    if (conn && !conn.isClosed()) {
      conn.close();
    }
  }
}

// ===============================================
// INSTRUCCIONES PARA USAR EL MODO PRUEBA
// ===============================================
/*

CONFIGURACIÓN DE PRUEBA:
1. MODO_PRUEBA = true (activar modo prueba)
2. SIMULAR_HERMANA = true/false (tipo de misionero a simular)
3. CORREO_PRUEBA = "tuCorreo@gmail.com" (tu correo para recibir pruebas)
4. NOMBRE_PRUEBA = "Tu Nombre" (nombre para la simulación)

FUNCIONES DISPONIBLES:

1. ejecutarPrueba()
   - Ejecuta una prueba completa del sistema
   - Crea un misionero simulado y envía correo a tu correo personal
   - No requiere conexión a base de datos

2. verificarConfiguracion()
   - Muestra la configuración actual del sistema
   - Útil para verificar settings antes de ejecutar

3. enviarCorreosCumpleanos()
   - Función principal que respeta el modo MODO_PRUEBA
   - En modo prueba: envía correo simulado
   - En modo producción: consulta base de datos real

4. obtenerEstadisticasCumpleanos()
   - Siempre consulta la base de datos real
   - Muestra cumpleaños próximos filtrados por ramas autorizadas

PASOS PARA PROBAR:
1. Asegúrate de que MODO_PRUEBA = true
2. Configura tu correo en CORREO_PRUEBA
3. Ejecuta: ejecutarPrueba()
4. Revisa tu bandeja de entrada
5. Para producción, cambia MODO_PRUEBA = false

NOTAS:
- En modo prueba, el asunto incluye [PRUEBA]
- No se usa BCC en modo prueba
- Los datos del misionero son completamente simulados
- Se respetan las configuraciones de ramas y estatus

*/
