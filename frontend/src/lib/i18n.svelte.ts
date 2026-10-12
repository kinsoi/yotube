import en from './locales/en.json'
import fr from './locales/fr.json'
import ru from './locales/ru.json'
import type { Locale } from './types'

type Dict = { [key: string]: string | Dict }
type Params = Record<string, string | number>

export const LOCALES: Record<Locale, Dict> = { en, fr, ru }
export const LOCALE_NAMES: Record<Locale, string> = { en: 'English', fr: 'Français', ru: 'Русский' }

const STORAGE_KEY = 'yotube.locale'

function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && value in LOCALES
}

function storedLocale(): Locale | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return isLocale(value) ? value : null
  } catch {
    return null
  }
}

function detectLocale(): Locale {
  const stored = storedLocale()
  if (stored) return stored
  const browser = typeof navigator === 'undefined' ? 'en' : navigator.language.slice(0, 2)
  return isLocale(browser) ? browser : 'en'
}

export const i18n = $state({ locale: detectLocale() })

export function hasStoredLocale(): boolean {
  return storedLocale() !== null
}

export function setLocale(locale: Locale): void {
  i18n.locale = locale
  document.documentElement.lang = locale
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    // Private browsing: the choice simply isn't remembered.
  }
}

function lookup(dict: Dict, key: string): string | undefined {
  let current: string | Dict | undefined = dict
  for (const part of key.split('.')) {
    if (typeof current !== 'object' || current === null) return undefined
    current = current[part]
  }
  return typeof current === 'string' ? current : undefined
}

export function translate(locale: Locale, key: string, params: Params = {}): string {
  const template = lookup(LOCALES[locale], key) ?? lookup(LOCALES.en, key) ?? key
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match,
  )
}

export function tnFor(locale: Locale, key: string, count: number, params: Params = {}): string {
  const category = new Intl.PluralRules(locale).select(count)
  const pluralKey = lookup(LOCALES[locale], `${key}.${category}`) ? category : 'other'
  return translate(locale, `${key}.${pluralKey}`, { count, ...params })
}

/** Translate `key` in the current locale (reactive inside components). */
export function t(key: string, params?: Params): string {
  return translate(i18n.locale, key, params)
}

/** Translate a plural key (`key.one|few|many|other`) for `count`. */
export function tn(key: string, count: number, params?: Params): string {
  return tnFor(i18n.locale, key, count, params)
}

export function flattenKeys(dict: Dict, prefix = ''): string[] {
  return Object.entries(dict).flatMap(([key, value]) =>
    typeof value === 'string' ? [`${prefix}${key}`] : flattenKeys(value, `${prefix}${key}.`),
  )
}
