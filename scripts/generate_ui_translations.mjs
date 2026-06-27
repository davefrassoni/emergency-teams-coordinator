import { readdir, readFile, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const sourceRoot = fileURLToPath(new URL('../frontend/src/', import.meta.url))
const output = new URL('../frontend/src/literalTranslations.generated.js', import.meta.url)
const languages = ['es', 'fr', 'it', 'zh', 'ru', 'he']
const overrides = {
  'Back to home': { es: 'Volver al inicio', fr: "Retour à l’accueil", it: 'Torna alla home', zh: '返回首页', ru: 'На главную', he: 'חזרה לדף הבית' },
  'boxes': { es: 'cajas', fr: 'boîtes', it: 'scatole', zh: '箱', ru: 'коробки', he: 'קופסאות' },
  'Deployed': { es: 'Desplegado', fr: 'Déployée', it: 'Schierata', zh: '已部署', ru: 'Развернута', he: 'פרוס' },
  'Expectant / deceased': { es: 'Expectante / fallecido', fr: 'Pronostic réservé / décédé', it: 'In attesa / deceduto', zh: '待救治 / 已死亡', ru: 'Ожидающий помощи / умерший', he: 'ממתין לטיפול / נפטר' },
  'Live': { es: 'En vivo', fr: 'En direct', it: 'In tempo reale', zh: '实时', ru: 'В реальном времени', he: 'בזמן אמת' },
  'Live · fallback': { es: 'En vivo · respaldo', fr: 'En direct · mode de secours', it: 'In tempo reale · modalità alternativa', zh: '实时 · 备用连接', ru: 'В реальном времени · резервный режим', he: 'בזמן אמת · מצב גיבוי' },
  'Live affected zone': { es: 'Zona afectada en vivo', fr: 'Zone touchée en direct', it: 'Zona colpita in tempo reale', zh: '受灾区域实时图', ru: 'Зона поражения в реальном времени', he: 'אזור פגוע בזמן אמת' },
  'Open': { es: 'Abierto', fr: 'Ouvert', it: 'Aperto', zh: '开放', ru: 'Открыто', he: 'פתוח' },
  'Signing you in…': { es: 'Iniciando sesión…', fr: 'Connexion en cours…', it: 'Accesso in corso…', zh: '正在登录…', ru: 'Выполняется вход…', he: 'מתבצעת כניסה…' },
  'still needed': { es: 'aún necesarios', fr: 'encore nécessaires', it: 'ancora necessari', zh: '仍然需要', ru: 'ещё требуется', he: 'עדיין נדרש' },
}

const extras = [
  'Live', 'Live · fallback', 'Connecting', 'System', 'Unknown', 'Immediate', 'Urgent',
  'Lower urgency', 'Expectant / deceased', 'Reported', 'Verified', 'Response active',
  'Resolved', 'Available', 'Deployed', 'Unavailable', 'Resting', 'Search & rescue',
  'Medical', 'Fire & hazmat', 'Structural engineering', 'Logistics', 'Security', 'Other',
  'Open', 'Partially covered', 'Covered', 'Closed', 'Preparing', 'In transit', 'Arrived',
  'Cancelled', 'units', 'liters', 'boxes', 'packs', 'pallets', 'just now',
  'Something went wrong.', 'Delivery tracking updated.',
  'Report received. A coordinator must verify it before dispatch.',
  'Missing-person report received. Authorities can verify it and assign a search team.',
  'Supply request published. Nearby contributors can now offer items.',
  'Your contribution is reserved. Save the tracking link.',
  'This invitation could not be found.', 'This sign-in link has expired or was already used.',
  'Public reporting is disabled for this operation.',
  'Updated', 'emergencies', 'responders', 'responders total', 'teams', 'trapped', 'affected',
  'approx.', 'time unknown', 'delivery', 'deliveries', 'committed', 'left', 'of', 'promised',
  'To', 'ETA', 'not provided', 'Expires', 'the responder', 'ago', 'Essential supplies needed',
  'Response underway', 'Awaiting verification', 'All', 'Missing', 'Location placed',
  'Tap the map at the exact location',
]

async function vueFiles(directory) {
  const files = []
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) files.push(...await vueFiles(path))
    else if (entry.name.endsWith('.vue')) files.push(path)
  }
  return files
}

function clean(value) {
  return value
    .replace(/&amp;/g, '&')
    .replace(/&[a-z]+;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^[*·:,.!?/–—-]+\s*/, '')
    .replace(/\s*[·:,.!?/–—-]+$/, '')
}

function isPhrase(value) {
  return value.length > 1
    && /[A-Za-z]{2}/.test(value)
    && !/[{}<>`]/.test(value)
    && !/^(https?:|[a-z]+\/|#[a-z])/i.test(value)
    && !/^[A-Z_]{2,}$/.test(value)
    && !/^(ReliefGrid|Dave Frassoni|RG)$/.test(value)
}

async function phrases() {
  const found = new Set(extras)
  for (const file of await vueFiles(sourceRoot)) {
    const source = await readFile(file, 'utf8')
    const template = source
      .replace(/<script[\s\S]*?<\/script>/g, '')
      .replace(/<style[\s\S]*?<\/style>/g, '')

    for (const match of template.matchAll(/>([^<>]+)</g)) {
      for (const part of match[1].split(/{{[\s\S]*?}}/)) {
        const value = clean(part)
        if (isPhrase(value)) found.add(value)
      }
    }
    for (const expression of template.matchAll(/{{([\s\S]*?)}}/g)) {
      for (const match of expression[1].matchAll(/['"]([^'"]+)['"]/g)) {
        const value = clean(match[1])
        if (isPhrase(value)) found.add(value)
      }
    }
    for (const match of template.matchAll(/\b(?:placeholder|aria-label|title|eyebrow|label)="([^"]+)"/g)) {
      const value = clean(match[1])
      if (isPhrase(value)) found.add(value)
    }
    for (const match of source.matchAll(/\blabel:\s*['"]([^'"]+)['"]/g)) {
      const value = clean(match[1])
      if (isPhrase(value)) found.add(value)
    }
    for (const match of source.matchAll(/(?:notify\(|(?:fatalError|confirmation|formError)\.value\s*=\s*)['"]([^'"]+)['"]/g)) {
      const value = clean(match[1])
      if (isPhrase(value)) found.add(value)
    }
  }
  return [...found].sort((a, b) => a.localeCompare(b))
}

async function translateChunk(entries, language) {
  const query = entries.map(([index, phrase]) => `[[[${index}]]] ${phrase}`).join('\n')
  const url = new URL('https://translate.googleapis.com/translate_a/single')
  url.search = new URLSearchParams({ client: 'gtx', sl: 'en', tl: language, dt: 't', q: query })
  const response = await fetch(url, { signal: AbortSignal.timeout(30000) })
  if (!response.ok) throw new Error(`Translation request failed: ${response.status}`)
  const payload = await response.json()
  const text = payload[0].map((segment) => segment[0]).join('')
  const translated = new Map()
  const pattern = /\[\[\[(\d+)]]]\s*([\s\S]*?)(?=\n\[\[\[|$)/g
  for (const match of text.matchAll(pattern)) translated.set(Number(match[1]), match[2].trim())
  return translated
}

async function translationsFor(source, language) {
  const result = Array(source.length)
  let chunk = []
  let size = 0
  for (const [index, phrase] of source.entries()) {
    if (size + phrase.length > 3500 && chunk.length) {
      const values = await translateChunk(chunk, language)
      for (const [itemIndex] of chunk) result[itemIndex] = values.get(itemIndex)
      chunk = []
      size = 0
    }
    chunk.push([index, phrase])
    size += phrase.length
  }
  if (chunk.length) {
    const values = await translateChunk(chunk, language)
    for (const [itemIndex] of chunk) result[itemIndex] = values.get(itemIndex)
  }
  for (const [index, phrase] of source.entries()) {
    if (!result[index]) {
      const values = await translateChunk([[index, phrase]], language)
      result[index] = values.get(index) || phrase
      if (!values.get(index)) console.warn(`Keeping ${language} token unchanged: ${phrase}`)
    }
  }
  if (result.some((value) => !value)) throw new Error(`Incomplete ${language} translation`)
  return result
}

const source = await phrases()
const translated = {}
for (const language of languages) {
  console.log(`Translating ${source.length} phrases to ${language}…`)
  translated[language] = await translationsFor(source, language)
}

const rows = source.map((phrase, index) => {
  const values = Object.fromEntries(languages.map((language) => [
    language,
    overrides[phrase]?.[language] || translated[language][index],
  ]))
  return `  ${JSON.stringify(phrase)}: ${JSON.stringify(values)},`
})

await writeFile(
  output,
  `// Generated by scripts/generate_ui_translations.mjs. Do not edit by hand.\n`
    + `export const literalTranslations = {\n${rows.join('\n')}\n}\n`,
  'utf8',
)
console.log(`Wrote ${source.length} translated UI phrases.`)
