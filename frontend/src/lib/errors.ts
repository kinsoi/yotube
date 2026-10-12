import { ApiError } from './api'
import { t } from './i18n.svelte'

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const key = `errors.${error.code}`
    const message = t(key)
    if (message !== key) return message
  }
  return t('errors.generic')
}
