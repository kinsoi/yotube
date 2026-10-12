import { ApiError } from './api'
import { t } from './i18n.svelte'

/** Localized text for a failed sync; the raw engine message is only shown for unknown codes. */
export function syncErrorMessage(code: string | null, raw: string | null): string {
  const key = `sync_errors.${code}`
  const known = code && code !== 'unknown' && t(key) !== key
  return known ? t(key) : t('sync_errors.unknown', { message: raw ?? '' })
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const key = `errors.${error.code}`
    const message = t(key)
    if (message !== key) return message
  }
  return t('errors.generic')
}
