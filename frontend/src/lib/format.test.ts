import { describe, expect, it } from 'vitest'
import { COLOR_NAMES, formatDate, formatDuration } from './format'

describe('formatDuration', () => {
  it('formats minutes and seconds', () => {
    expect(formatDuration(125)).toBe('2:05')
    expect(formatDuration(59.6)).toBe('1:00')
    expect(formatDuration(null)).toBe('')
  })
})

describe('formatDate', () => {
  it('treats naive timestamps as UTC', () => {
    expect(formatDate('2026-10-12T03:00:00', 'en-GB')).toBe(
      formatDate('2026-10-12T03:00:00Z', 'en-GB'),
    )
    expect(formatDate(null, 'en')).toBe('')
  })
})

it('exposes the eight playlist colours', () => {
  expect(COLOR_NAMES).toHaveLength(8)
})
