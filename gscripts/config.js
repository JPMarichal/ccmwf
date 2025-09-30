// config.js
// Configuración centralizada para scripts de Google Apps Script CCM

// --- Configuración de base de datos principal ---
const dbConfig = {
    host: "212.227.243.210",
    port: "3306",
    user: "jpmarichal",
    password: "pcia_ccm",
    dbName: "ccm"
  };
  
  // --- Configuración de ramas y hojas ---
  const RAMA = 14;
  const ID_CARPETA_GENERACIONES = "1ned3xG0oC-SgCUeLXSBADD8PQWV5drVs";
  const ID_CARPETA_BACKUP = "1Kjof0VZAjr0_OO6Y32S0NkioPo43D9t0";
  const ID_HOJA_ORIGEN_REPORTE = "12bZMLrrRcBbOYIo6px9B6IIfeNrPkttlx7dY7YI9GcI";
  const NOMBRE_HOJA_DESTINO_REPORTE = "Reporte misional concentrado";
  
  // Consolidación de IDs de hojas de cálculo (mantener compatibilidad)
  const SPREADSHEET_ID_BRANCH_IN_A_GLANCE = "1He4ctI9apqrIdhNkHT34zxDD_tcw4PU_pthFrSKO2Nk";
  const SPREADSHEET_ID_REPORTE_MISIONAL = "19N5tl77QLcxYkuR-KfIikrdwLd8OmEYkOzQoLVvHA_Y";
  
  // --- Configuración de notificaciones Telegram ---
  const TELEGRAM_CONFIG = {
    botToken: "8261928878:AAF7xe1yyXQ7Tt9mm6K3p7eXjdrWuVReBkU", // Token del bot obtenido de @BotFather
    chatId: "-1002527727204", // Chat ID del canal "CCM Notifications"
    enabled: true, // Habilitar/deshabilitar notificaciones
    canalNombre: "CCM Notifications", // Nombre del canal para referencia
    urlCanal: "https://t.me/+wnIpBMJJeG8xZTZh" // Enlace de invitación del canal
  };
  
  // Flag global adicional para compatibilidad con otros scripts
  const TELEGRAM_NOTIFICATIONS_ENABLED = TELEGRAM_CONFIG.enabled;
  
  // --- Configuración de notificaciones Messenger ---
  const MESSENGER_CONFIG = {
    pageAccessToken: "TU_PAGE_ACCESS_TOKEN", // Token de acceso de tu página de Facebook
    verifyToken: "CCM_VERIFY_TOKEN_2025", // Token de verificación para webhook (opcional)
    appSecret: "TU_APP_SECRET", // App Secret de tu aplicación de Facebook (opcional)
    pageId: "TU_PAGE_ID", // ID de tu página de Facebook
    groupThreadId: "TU_GROUP_THREAD_ID", // ID del grupo "Branch 14 leadership" existente
    enabled: false, // Cambiar a true cuando esté configurado correctamente
    grupoNombre: "Branch 14 leadership", // Nombre del grupo existente
    destinatarios: "Líderes de zona y hermanas capacitadoras", // Descripción de audiencia
    metodo: "pagina_en_grupo_existente" // Método: página agregada al grupo existente
  };
  
  // Flag global adicional para compatibilidad con otros scripts
  const MESSENGER_NOTIFICATIONS_ENABLED = MESSENGER_CONFIG.enabled;
  
  // --- Configuración de correos ---
  const REMITENTE_EMAIL = "jpmarichal@gmail.com";
  const REMITENTE_NOMBRE = "Presidente Marichal";
  const CORREO_PERSONAL = "jpmarichal@gmail.com";
  const CORREO_MISIONAL = "jpmarichal@train.missionary.org";
  
  // --- Configuración de reportes PDF ---
  const REPORTES_PDF_CONFIG = {
    // URLs de las hojas de cálculo
    urls: {
      branchInAGlance: "https://docs.google.com/spreadsheets/d/1He4ctI9apqrIdhNkHT34zxDD_tcw4PU_pthFrSKO2Nk/edit?gid=4393459#gid=4393459",
      reporteMisionalConcentrado: "https://docs.google.com/spreadsheets/d/19N5tl77QLcxYkuR-KfIikrdwLd8OmEYkOzQoLVvHA_Y/edit?gid=0#gid=0"
    },
    
    // IDs de las hojas de cálculo (extraídos de las URLs)
    spreadsheetIds: {
      branchInAGlance: SPREADSHEET_ID_BRANCH_IN_A_GLANCE,
      reporteMisionalConcentrado: SPREADSHEET_ID_REPORTE_MISIONAL
    },
    
    // GIDs específicos de las hojas
    gids: {
      branchInAGlance: "4393459",
      reporteMisionalConcentrado: "0"
    },
    
    // Nombres de las hojas para el PDF
    nombres: {
      branchInAGlance: "Branch in a Glance",
      reporteMisionalConcentrado: "Reporte Misional Concentrado"
    },
    
    // Configuración de liderazgo de rama
    liderazgoRama: {
      presidente: {
        nombre: "Presidente Alvarez",
        email: "arturoalvarezz@train.missionary.org",
        cargo: "Presidente"
      },
      primerConsejero: {
        nombre: "Presidente Marichal",
        email: "jpmarichal@train.missionary.org", 
        cargo: "Primer Consejero"
      },
      segundoConsejero: {
        nombre: "Presidente Molina", 
        email: "Molinajo@train.missionary.org", 
        cargo: "Segundo Consejero"
      }
    },
    
    // Lista de destinatarios (se puede personalizar)
    destinatarios: [
      "jpmarichal@train.missionary.org"      // Solo Presidente Marichal para pruebas
      // Descomentar las siguientes líneas cuando esté listo para producción:
      // "arturoalvarezz@train.missionary.org",  // Presidente Alvarez
      // "Molinajo@train.missionary.org"         // Segundo Consejero Molina
    ],
    
    // Configuración de envío de correo
    correo: {
      asunto: "Reportes Misionales - {fecha}",
      cuerpoMensaje: `
  Estimado {saludo},
  
  Se adjuntan los reportes misionales actualizados:
  
  1. Branch in a Glance - Resumen general de la rama
  2. Reporte Misional Concentrado - Datos detallados consolidados
  
  Estos reportes se generan automáticamente y contienen la información más reciente disponible.
  
  Saludos cordiales,
  {remitente}
  {cargo}
      `.trim(),
      remitente: REMITENTE_NOMBRE,
      correoRemitente: CORREO_MISIONAL
    },
    
    // Configuración de PDF
    pdfConfig: {
      format: "pdf",
      size: "LETTER", // Cambiado de A4 a Letter
      portrait: true,
      fitw: true, // Ajustar al ancho
      fith: true, // Ajustar a la altura también
      gridlines: false,
      printtitle: true, // Cambiado a true para incluir el título de la hoja
      sheetnames: false,
      fzr: false, // No congelar filas
      fzc: false, // No congelar columnas
      // Configuraciones adicionales para mejorar la calidad del PDF
      top_margin: "0.5",
      bottom_margin: "0.5", 
      left_margin: "0.5",
      right_margin: "0.5",
      horizontal_alignment: "CENTER",
      vertical_alignment: "TOP",
      // Incluir encabezados y pies de página
      headers: true,
      footers: true,
      // Configuraciones para preservar formato y gráficos
      scale: "2", // Fit to page (escala automática)
      fmtonly: false, // No solo formato, incluir todos los elementos
      attachment: false, // No como adjunto, como vista completa
      // Configuraciones específicas para ajuste de página
      repeat_headers: false,
      repeat_columns: false,
      page_order: "1" // Orden de páginas: 1 = hacia abajo, luego hacia la derecha
    }
  };
  
  // --- Configuración de destinatarios y ramas autorizadas ---
  const RAMAS_AUTORIZADAS = [14];
  const CONFIG_ESTATUS_POR_RAMA = {
    12: ['Campo'],
    14: ['Virtual', 'CCM', 'Campo'],
    9: ['Virtual'],
    6: ['CCM'],
    16: ['CCM']
  };
  
  // --- Configuración de etiquetas y búsqueda de correos ---
  const DESTINATION_EMAIL_REENVIO = "jpmarichal@train.missionary.org";
  const SEARCH_QUERY_REENVIO = 'subject:"Ajustes "';
  const PROCESSED_LABEL_REENVIO = "Reenviado_Automaticamente";
  
  // --- Configuración para extracción de attachments de correos de misioneros ---
  const SEARCH_QUERY_MISIONEROS = 'subject:"Misioneros que llegan " is:unread';
  const PROCESSED_LABEL_MISIONEROS = "Attachments_Extraidos";
  const ID_CARPETA_ATTACHMENTS = ID_CARPETA_GENERACIONES; // Usa la misma carpeta base
  
  // --- Configuración específica de notificaciones Telegram ---
  const TELEGRAM_NOTIFICATION_CONFIG = {
    // Días hacia adelante para buscar distritos próximos
    diasProximosLlegadas: 30,
    
    // Plantillas de mensajes
    emojisPorTipo: {
      procesamiento: "🚀",
      estadisticas: "📊", 
      distritos: "🎯",
      fecha: "📅",
      rama: "🌿",
      misioneros: "👥",
      pais: "🌍",
      bot: "🤖"
    },
    
    // Configuración de formato
    formatoFecha: "dd/MM/yyyy HH:mm",
    formatoFechaCorta: "dd/MM/yyyy",
    
    // Límites de mensaje
    maxDistritosPorMensaje: 20,
    cortarMensajeLargo: true
  };
  
  // --- Configuración de hoja Branch in a Glance ---
  const sheetConfigBranchInAGlance = {
    spreadsheetId: SPREADSHEET_ID_BRANCH_IN_A_GLANCE,
    sheetName: "Branch in a Glance",
    distritos: {
      "A": 7, "B": 8, "C": 9, "D": 10, "E": 11, "F": 12, "G": 13, "H": 14, "I": 15, "J": 16, "K": 17
    },
    campos: {
      "Generacion": "C",
      "CCM_llegada": "D",
      "CCM_salida": "E"
    },
    columnaTotal: "Q"
  };
  
  // --- Funciones auxiliares centralizadas ---
  // Función para obtener los estatus válidos para una rama específica
  function obtenerEstatusValidosPorRama(rama) {
    return CONFIG_ESTATUS_POR_RAMA[rama] || [];
  }
  
  // Exportar para uso global (Apps Script: basta con estar en el mismo proyecto)
  // No es necesario exportar explícitamente en Apps Script clásico.
  