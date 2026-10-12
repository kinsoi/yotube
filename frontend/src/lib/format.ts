import type { Color } from './types'

export const COLORS: Record<Color, string> = {
  orange: '#F26B3A',
  yellow: '#F5B82E',
  blue: '#3B82F6',
  green: '#22A06B',
  pink: '#EC4899',
  purple: '#8B5CF6',
  red: '#E5484D',
  teal: '#14B8A6',
}

export const COLOR_NAMES = Object.keys(COLORS) as Color[]

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return ''
  const total = Math.round(seconds)
  const minutes = Math.floor(total / 60)
  return `${minutes}:${String(total % 60).padStart(2, '0')}`
}

/** Backend datetimes are naive UTC ISO strings. */
export function formatDate(iso: string | null, locale: string): string {
  if (!iso) return ''
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`)
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
