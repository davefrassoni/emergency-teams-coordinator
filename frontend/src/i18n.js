import { nextTick, ref, watch } from 'vue'
import { literalTranslations } from './literalTranslations.generated'

export const languages = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
  { code: 'fr', label: 'Français' },
  { code: 'it', label: 'Italiano' },
  { code: 'zh', label: '中文' },
  { code: 'ru', label: 'Русский' },
  { code: 'he', label: 'עברית' },
]

const messages = {
  en: {
    map: 'Map', overview: 'Overview', incidents: 'Emergencies', supplies: 'Supplies',
    teams: 'Teams', activity: 'Activity', signIn: 'Sign in', openOperation: 'Open an operation',
    liveResponse: 'Built for live response', headline: 'Every team. One clear picture.',
    hero: 'Coordinate emergencies, triage needs, and deploy available responders from a shared, low-friction workspace.',
    start: 'Start coordinating', noAccount: 'No account required', privateLinks: 'Private access links',
    operationName: 'Operation name', codename: 'Short codename', primaryArea: 'Primary area',
    context: 'Brief context', yourName: 'Your name', adminEmail: 'Administrator email',
    create: 'Open response operation', recent: 'Your recent operations',
    emergency: 'Emergency', missingPerson: 'Missing person', requestSupplies: 'Request supplies',
    supplyNeeds: 'Supply needs', needsResponse: 'Needs & response', publicMap: 'Public help map',
    feature: 'Request a feature', featureTitle: 'Request a new feature',
    featureHelp: 'Tell us what would make field coordination easier.',
    email: 'Contact email', details: 'Feature details', send: 'Send request',
    sent: 'Your request was sent. Thank you.', cancel: 'Cancel',
    builtBy: 'Built by', donate: 'Please donate to improve the site and server performance',
    returnOperation: 'Return to an operation',
    passwordless: 'Passwordless access', emailLink: 'Email me a sign-in link',
    language: 'Language', whatHappened: 'What can you see?', exactLocation: 'Address or nearby landmark',
    peopleAffected: 'People affected', peopleTrapped: 'People trapped', hazards: 'Visible hazards',
    usefulDetails: 'Other useful details', sendReport: 'Send unverified report',
    reportMissing: 'Report a missing person', personName: "Person's name", age: 'Approximate age',
    lastSeenLocation: 'Last-seen address or landmark', lastSeenTime: 'When were they last seen?',
    physicalDescription: 'Physical description', clothing: 'Clothing when last seen',
    circumstances: 'Circumstances', reporterContact: 'Private reporter contact',
    requestTitle: 'Short request title', deliveryAddress: 'Delivery address or landmark',
    itemsNeeded: 'Items needed', item: 'Item', quantity: 'Quantity', unit: 'Unit',
    deliveryInstructions: 'Context or delivery instructions', postSupply: 'Post supply request',
  },
  es: {
    map: 'Mapa', overview: 'Resumen', incidents: 'Emergencias', supplies: 'Suministros',
    teams: 'Equipos', activity: 'Actividad', signIn: 'Iniciar sesión', openOperation: 'Crear operación',
    liveResponse: 'Diseñado para respuesta en vivo', headline: 'Todos los equipos. Una visión clara.',
    hero: 'Coordina emergencias, triaje y equipos disponibles desde un espacio compartido y sencillo.',
    start: 'Comenzar a coordinar', noAccount: 'Sin cuenta obligatoria', privateLinks: 'Enlaces privados',
    operationName: 'Nombre de la operación', codename: 'Código corto', primaryArea: 'Zona principal',
    context: 'Contexto breve', yourName: 'Tu nombre', adminEmail: 'Correo del administrador',
    create: 'Abrir operación de respuesta', recent: 'Tus operaciones recientes',
    emergency: 'Emergencia', missingPerson: 'Persona desaparecida', requestSupplies: 'Solicitar suministros',
    supplyNeeds: 'Necesidades', needsResponse: 'Necesidades y respuesta', publicMap: 'Mapa público de ayuda',
    feature: 'Solicitar función', featureTitle: 'Solicitar una nueva función',
    featureHelp: 'Cuéntanos qué facilitaría la coordinación en terreno.',
    email: 'Correo de contacto', details: 'Detalles de la función', send: 'Enviar solicitud',
    sent: 'Tu solicitud fue enviada. Gracias.', cancel: 'Cancelar',
    builtBy: 'Creado por', donate: 'Por favor, dona para mejorar el sitio y el rendimiento del servidor',
    returnOperation: 'Volver a una operación',
    passwordless: 'Acceso sin contraseña', emailLink: 'Enviarme un enlace de acceso',
    language: 'Idioma', whatHappened: '¿Qué puedes ver?', exactLocation: 'Dirección o punto de referencia',
    peopleAffected: 'Personas afectadas', peopleTrapped: 'Personas atrapadas', hazards: 'Peligros visibles',
    usefulDetails: 'Otros detalles útiles', sendReport: 'Enviar reporte sin verificar',
    reportMissing: 'Reportar una persona desaparecida', personName: 'Nombre de la persona', age: 'Edad aproximada',
    lastSeenLocation: 'Dirección o lugar donde fue vista', lastSeenTime: '¿Cuándo fue vista por última vez?',
    physicalDescription: 'Descripción física', clothing: 'Ropa que llevaba',
    circumstances: 'Circunstancias', reporterContact: 'Contacto privado del informante',
    requestTitle: 'Título breve', deliveryAddress: 'Dirección o punto de entrega',
    itemsNeeded: 'Artículos necesarios', item: 'Artículo', quantity: 'Cantidad', unit: 'Unidad',
    deliveryInstructions: 'Contexto o instrucciones de entrega', postSupply: 'Publicar solicitud',
  },
  fr: {
    map: 'Carte', overview: 'Aperçu', incidents: 'Urgences', supplies: 'Fournitures',
    teams: 'Équipes', activity: 'Activité', signIn: 'Se connecter', openOperation: 'Créer une opération',
    liveResponse: 'Conçu pour la réponse en direct', headline: 'Toutes les équipes. Une vision claire.',
    hero: 'Coordonnez les urgences, le triage et les intervenants disponibles dans un espace partagé et simple.',
    start: 'Commencer', noAccount: 'Aucun compte requis', privateLinks: 'Liens privés',
    operationName: "Nom de l’opération", codename: 'Nom court', primaryArea: 'Zone principale',
    context: 'Contexte bref', yourName: 'Votre nom', adminEmail: "E-mail de l’administrateur",
    create: 'Ouvrir l’opération', recent: 'Vos opérations récentes',
    emergency: 'Urgence', missingPerson: 'Personne disparue', requestSupplies: 'Demander des fournitures',
    supplyNeeds: 'Besoins', needsResponse: 'Besoins et réponse', publicMap: "Carte publique d’aide",
    feature: 'Proposer une fonction', featureTitle: 'Proposer une nouvelle fonction',
    featureHelp: 'Dites-nous ce qui faciliterait la coordination sur le terrain.',
    email: 'E-mail de contact', details: 'Détails', send: 'Envoyer',
    sent: 'Votre demande a été envoyée. Merci.', cancel: 'Annuler',
    builtBy: 'Créé par', donate: 'Faites un don pour améliorer le site et les performances du serveur',
    returnOperation: 'Revenir à une opération',
    passwordless: 'Accès sans mot de passe', emailLink: 'Envoyer un lien de connexion',
    language: 'Langue', whatHappened: 'Que voyez-vous ?', exactLocation: 'Adresse ou point de repère',
    peopleAffected: 'Personnes touchées', peopleTrapped: 'Personnes piégées', hazards: 'Dangers visibles',
    usefulDetails: 'Autres détails utiles', sendReport: 'Envoyer le signalement non vérifié',
    reportMissing: 'Signaler une personne disparue', personName: 'Nom de la personne', age: 'Âge approximatif',
    lastSeenLocation: 'Dernier lieu connu', lastSeenTime: 'Quand a-t-elle été vue ?',
    physicalDescription: 'Description physique', clothing: 'Vêtements portés',
    circumstances: 'Circonstances', reporterContact: 'Contact privé du déclarant',
    requestTitle: 'Titre court', deliveryAddress: 'Adresse ou point de livraison',
    itemsNeeded: 'Articles nécessaires', item: 'Article', quantity: 'Quantité', unit: 'Unité',
    deliveryInstructions: 'Contexte ou instructions', postSupply: 'Publier la demande',
  },
  it: {
    map: 'Mappa', overview: 'Panoramica', incidents: 'Emergenze', supplies: 'Forniture',
    teams: 'Squadre', activity: 'Attività', signIn: 'Accedi', openOperation: 'Crea operazione',
    liveResponse: 'Creato per la risposta in tempo reale', headline: 'Tutte le squadre. Una visione chiara.',
    hero: 'Coordina emergenze, triage e soccorritori disponibili in uno spazio condiviso e semplice.',
    start: 'Inizia a coordinare', noAccount: 'Nessun account richiesto', privateLinks: 'Link privati',
    operationName: "Nome dell’operazione", codename: 'Nome breve', primaryArea: 'Area principale',
    context: 'Breve contesto', yourName: 'Il tuo nome', adminEmail: "Email dell’amministratore",
    create: 'Apri operazione', recent: 'Operazioni recenti',
    emergency: 'Emergenza', missingPerson: 'Persona scomparsa', requestSupplies: 'Richiedi forniture',
    supplyNeeds: 'Richieste', needsResponse: 'Bisogni e risposta', publicMap: 'Mappa pubblica di aiuto',
    feature: 'Richiedi funzione', featureTitle: 'Richiedi una nuova funzione',
    featureHelp: 'Dicci cosa renderebbe più facile il coordinamento sul campo.',
    email: 'Email di contatto', details: 'Dettagli', send: 'Invia richiesta',
    sent: 'Richiesta inviata. Grazie.', cancel: 'Annulla',
    builtBy: 'Creato da', donate: 'Fai una donazione per migliorare il sito e le prestazioni del server',
    returnOperation: 'Torna a un’operazione',
    passwordless: 'Accesso senza password', emailLink: 'Invia link di accesso',
    language: 'Lingua', whatHappened: 'Cosa vedi?', exactLocation: 'Indirizzo o punto di riferimento',
    peopleAffected: 'Persone coinvolte', peopleTrapped: 'Persone intrappolate', hazards: 'Pericoli visibili',
    usefulDetails: 'Altri dettagli utili', sendReport: 'Invia segnalazione non verificata',
    reportMissing: 'Segnala una persona scomparsa', personName: 'Nome della persona', age: 'Età approssimativa',
    lastSeenLocation: 'Ultimo luogo conosciuto', lastSeenTime: "Quando è stata vista l'ultima volta?",
    physicalDescription: 'Descrizione fisica', clothing: 'Abbigliamento',
    circumstances: 'Circostanze', reporterContact: 'Contatto privato del segnalante',
    requestTitle: 'Titolo breve', deliveryAddress: 'Indirizzo o punto di consegna',
    itemsNeeded: 'Articoli necessari', item: 'Articolo', quantity: 'Quantità', unit: 'Unità',
    deliveryInstructions: 'Contesto o istruzioni', postSupply: 'Pubblica richiesta',
  },
  zh: {
    map: '地图', overview: '概览', incidents: '紧急事件', supplies: '物资',
    teams: '救援队', activity: '动态', signIn: '登录', openOperation: '创建行动',
    liveResponse: '为实时救援而设计', headline: '所有团队，一张清晰全图。',
    hero: '在一个简单的共享空间中协调紧急事件、分诊需求和可用救援人员。',
    start: '开始协调', noAccount: '无需账户', privateLinks: '私密访问链接',
    operationName: '行动名称', codename: '短代号', primaryArea: '主要区域',
    context: '简要情况', yourName: '您的姓名', adminEmail: '管理员邮箱',
    create: '创建救援行动', recent: '最近的行动',
    emergency: '紧急事件', missingPerson: '失踪人员', requestSupplies: '请求物资',
    supplyNeeds: '物资需求', needsResponse: '需求与响应', publicMap: '公共救援地图',
    feature: '请求新功能', featureTitle: '请求新功能',
    featureHelp: '告诉我们什么功能能让现场协调更容易。',
    email: '联系邮箱', details: '功能详情', send: '发送请求',
    sent: '请求已发送，谢谢。', cancel: '取消',
    builtBy: '开发者', donate: '请捐助以改进网站和服务器性能',
    returnOperation: '返回行动',
    passwordless: '免密码访问', emailLink: '发送登录链接',
    language: '语言', whatHappened: '您看到了什么？', exactLocation: '地址或附近地标',
    peopleAffected: '受影响人数', peopleTrapped: '被困人数', hazards: '可见危险',
    usefulDetails: '其他有用信息', sendReport: '发送待核实报告',
    reportMissing: '报告失踪人员', personName: '人员姓名', age: '大概年龄',
    lastSeenLocation: '最后出现地点', lastSeenTime: '最后出现时间',
    physicalDescription: '外貌描述', clothing: '最后所穿衣物',
    circumstances: '相关情况', reporterContact: '报告人私人联系方式',
    requestTitle: '简短标题', deliveryAddress: '配送地址或地标',
    itemsNeeded: '所需物品', item: '物品', quantity: '数量', unit: '单位',
    deliveryInstructions: '背景或配送说明', postSupply: '发布物资请求',
  },
  ru: {
    map: 'Карта', overview: 'Обзор', incidents: 'Происшествия', supplies: 'Снабжение',
    teams: 'Команды', activity: 'События', signIn: 'Войти', openOperation: 'Создать операцию',
    liveResponse: 'Для реагирования в реальном времени', headline: 'Все команды. Единая картина.',
    hero: 'Координируйте происшествия, сортировку и доступных спасателей в общем простом пространстве.',
    start: 'Начать координацию', noAccount: 'Аккаунт не нужен', privateLinks: 'Приватные ссылки',
    operationName: 'Название операции', codename: 'Короткое имя', primaryArea: 'Основная зона',
    context: 'Краткое описание', yourName: 'Ваше имя', adminEmail: 'Email администратора',
    create: 'Открыть операцию', recent: 'Недавние операции',
    emergency: 'Происшествие', missingPerson: 'Пропавший человек', requestSupplies: 'Запросить помощь',
    supplyNeeds: 'Потребности', needsResponse: 'Потребности и помощь', publicMap: 'Публичная карта помощи',
    feature: 'Предложить функцию', featureTitle: 'Предложить новую функцию',
    featureHelp: 'Расскажите, что упростит координацию на месте.',
    email: 'Контактный email', details: 'Описание функции', send: 'Отправить',
    sent: 'Запрос отправлен. Спасибо.', cancel: 'Отмена',
    builtBy: 'Автор', donate: 'Пожалуйста, поддержите улучшение сайта и производительности сервера',
    returnOperation: 'Вернуться к операции',
    passwordless: 'Вход без пароля', emailLink: 'Отправить ссылку для входа',
    language: 'Язык', whatHappened: 'Что вы видите?', exactLocation: 'Адрес или ориентир',
    peopleAffected: 'Пострадавшие', peopleTrapped: 'Люди в ловушке', hazards: 'Видимые опасности',
    usefulDetails: 'Другие полезные сведения', sendReport: 'Отправить непроверенное сообщение',
    reportMissing: 'Сообщить о пропавшем', personName: 'Имя человека', age: 'Примерный возраст',
    lastSeenLocation: 'Последнее известное место', lastSeenTime: 'Когда его видели?',
    physicalDescription: 'Описание внешности', clothing: 'Одежда',
    circumstances: 'Обстоятельства', reporterContact: 'Приватный контакт заявителя',
    requestTitle: 'Краткий заголовок', deliveryAddress: 'Адрес или пункт доставки',
    itemsNeeded: 'Необходимые предметы', item: 'Предмет', quantity: 'Количество', unit: 'Единица',
    deliveryInstructions: 'Контекст или инструкции', postSupply: 'Опубликовать запрос',
  },
  he: {
    map: 'מפה', overview: 'סקירה', incidents: 'אירועים', supplies: 'אספקה',
    teams: 'צוותים', activity: 'פעילות', signIn: 'כניסה', openOperation: 'יצירת מבצע',
    liveResponse: 'נבנה לתגובה בזמן אמת', headline: 'כל הצוותים. תמונה ברורה אחת.',
    hero: 'תיאום אירועים, מיון צרכים וכוחות זמינים בסביבת עבודה משותפת ופשוטה.',
    start: 'התחלת תיאום', noAccount: 'אין צורך בחשבון', privateLinks: 'קישורי גישה פרטיים',
    operationName: 'שם המבצע', codename: 'שם קוד קצר', primaryArea: 'אזור עיקרי',
    context: 'תיאור קצר', yourName: 'השם שלך', adminEmail: 'דוא״ל מנהל',
    create: 'פתיחת מבצע תגובה', recent: 'מבצעים אחרונים',
    emergency: 'אירוע חירום', missingPerson: 'נעדר/ת', requestSupplies: 'בקשת אספקה',
    supplyNeeds: 'צרכי אספקה', needsResponse: 'צרכים ומענה', publicMap: 'מפת סיוע ציבורית',
    feature: 'בקשת תכונה', featureTitle: 'בקשת תכונה חדשה',
    featureHelp: 'ספרו לנו מה יקל על התיאום בשטח.',
    email: 'דוא״ל ליצירת קשר', details: 'פרטי התכונה', send: 'שליחת בקשה',
    sent: 'הבקשה נשלחה. תודה.', cancel: 'ביטול',
    builtBy: 'נבנה על ידי', donate: 'אנא תרמו לשיפור האתר וביצועי השרת',
    returnOperation: 'חזרה למבצע',
    passwordless: 'גישה ללא סיסמה', emailLink: 'שליחת קישור כניסה',
    language: 'שפה', whatHappened: 'מה ניתן לראות?', exactLocation: 'כתובת או נקודת ציון',
    peopleAffected: 'מספר נפגעים', peopleTrapped: 'מספר לכודים', hazards: 'סכנות נראות',
    usefulDetails: 'פרטים שימושיים נוספים', sendReport: 'שליחת דיווח לא מאומת',
    reportMissing: 'דיווח על נעדר/ת', personName: 'שם האדם', age: 'גיל משוער',
    lastSeenLocation: 'המקום האחרון שבו נראה/תה', lastSeenTime: 'מתי נראה/תה לאחרונה?',
    physicalDescription: 'תיאור חיצוני', clothing: 'לבוש בעת ההיעלמות',
    circumstances: 'נסיבות', reporterContact: 'פרטי מדווח פרטיים',
    requestTitle: 'כותרת קצרה', deliveryAddress: 'כתובת או נקודת מסירה',
    itemsNeeded: 'פריטים נדרשים', item: 'פריט', quantity: 'כמות', unit: 'יחידה',
    deliveryInstructions: 'הקשר או הוראות מסירה', postSupply: 'פרסום בקשת אספקה',
  },
}

function detectedLocale() {
  const saved = localStorage.getItem('reliefgrid:locale')
  if (messages[saved]) return saved
  const candidates = navigator.languages || [navigator.language || 'en']
  for (const candidate of candidates) {
    const code = candidate.toLowerCase().split('-')[0].replace('iw', 'he')
    if (messages[code]) return code
  }
  return 'en'
}

export const locale = ref(detectedLocale())

const reverseLiterals = {}
for (const [english, translations] of Object.entries(literalTranslations)) {
  reverseLiterals[english] = english
  for (const translated of Object.values(translations)) reverseLiterals[translated] = english
}

function translatedLiteral(value, target = locale.value) {
  if (typeof value !== 'string' || target === 'en' && literalTranslations[value]) return value
  const leading = value.match(/^\s*/)?.[0] || ''
  const trailing = value.match(/\s*$/)?.[0] || ''
  const text = value.trim()
  if (!text) return value

  let english = literalTranslations[text] ? text : reverseLiterals[text]
  let suffix = ''
  if (!english) {
    const core = text.replace(/[.!?…:]+$/, '')
    suffix = text.slice(core.length)
    english = literalTranslations[core] ? core : reverseLiterals[core]
  }
  if (english) {
    const result = target === 'en' ? english : literalTranslations[english]?.[target]
    return result ? `${leading}${result}${suffix}${trailing}` : value
  }

  const part = (source) => target === 'en'
    ? source
    : literalTranslations[source]?.[target] || source
  const dynamic = [
    [/^Updated (.+)$/, (match) => `${part('Updated')} ${match[1]}`],
    [/^(\d+) emergencies · (\d+) supply needs$/, (match) => `${match[1]} ${part('emergencies')} · ${match[2]} ${part('supply needs')}`],
    [/^(\d+) responders total$/, (match) => `${match[1]} ${part('responders total')}`],
    [/^(.+) of (.+) (.+) promised$/, (match) => `${match[1]} ${part('of')} ${match[2]} ${translatedLiteral(match[3], target)} ${part('promised')}`],
    [/^(.+) (.+) left$/, (match) => `${match[1]} ${translatedLiteral(match[2], target)} ${part('left')}`],
    [/^(\d+) (delivery|deliveries) committed$/, (match) => `${match[1]} ${part(match[2])} ${part('committed')}`],
    [/^Last seen: (.+)$/, (match) => `${part('Last seen')}: ${match[1]}`],
    [/^Last seen (.+)$/, (match) => `${part('Last seen')} ${match[1] === 'time unknown' ? part('time unknown') : match[1]}`],
    [/^(\d+) trapped$/, (match) => `${match[1]} ${part('trapped')}`],
    [/^(\d+) affected$/, (match) => `${match[1]} ${part('affected')}`],
    [/^(.+) still needed$/, (match) => `${match[1]} ${part('still needed')}`],
    [/^Deliver to (.+)$/, (match) => `${part('Deliver to')} ${match[1]}`],
    [/^To (.+)$/, (match) => `${part('To')} ${match[1]}`],
    [/^Last position (.+)$/, (match) => `${part('Last position')} ${match[1]}`],
    [/^(.+) · ETA (.+)$/, (match) => `${translatedLiteral(match[1], target)} · ${part('ETA')} ${match[2] === 'not provided' ? part('not provided') : match[2]}`],
    [/^(\d+) responders across (\d+) teams\.?$/, (match) => `${match[1]} ${part('responders across')} ${match[2]} ${part('teams')}.`],
    [/^(\d+) open requests, updated live\.?$/, (match) => `${match[1]} ${part('open requests, updated live')}.`],
    [/^Expires (.+)$/, (match) => `${part('Expires')} ${match[1]}`],
    [/^You’ve been invited as (.+)\.$/, (match) => `${part('You’ve been invited as')} ${translatedLiteral(match[1], target)}.`],
    [/^Send this one-time link to (.+)\.$/, (match) => `${part('Send this one-time link to')} ${match[1] === 'the responder' ? part('the responder') : match[1]}.`],
    [/^Missing \((\d+)\)$/, (match) => `${translatedLiteral('Missing', target)} (${match[1]})`],
  ]
  for (const [pattern, format] of dynamic) {
    const match = text.match(pattern)
    if (match) return `${leading}${format(match)}${trailing}`
  }
  return value
}

function localizeElement(root) {
  if (!root) return
  if (root.nodeType === Node.TEXT_NODE) {
    const translated = translatedLiteral(root.nodeValue)
    if (translated !== root.nodeValue) root.nodeValue = translated
    return
  }
  if (root.nodeType !== Node.ELEMENT_NODE) return
  for (const attribute of ['placeholder', 'aria-label', 'title']) {
    if (root.hasAttribute(attribute)) {
      const value = root.getAttribute(attribute)
      const translated = translatedLiteral(value)
      if (translated !== value) root.setAttribute(attribute, translated)
    }
  }
  for (const child of root.childNodes) localizeElement(child)
}

let observer
function localizePage() {
  const app = document.getElementById('app')
  if (!app) return
  localizeElement(app)
  if (!observer) {
    observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'characterData') localizeElement(mutation.target)
        for (const node of mutation.addedNodes) localizeElement(node)
      }
    })
    observer.observe(app, { childList: true, characterData: true, subtree: true })
  }
}

watch(locale, async (value) => {
  localStorage.setItem('reliefgrid:locale', value)
  document.documentElement.lang = value
  document.documentElement.dir = value === 'he' ? 'rtl' : 'ltr'
  await nextTick()
  localizePage()
}, { immediate: true })

export function useI18n() {
  const t = (key) => messages[locale.value]?.[key] || messages.en[key] || key
  const tl = (value) => translatedLiteral(value)
  const setLocale = (value) => {
    if (messages[value]) locale.value = value
  }
  return { locale, languages, t, tl, setLocale }
}
