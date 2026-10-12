import { beforeEach, expect, it } from 'vitest'
import { syncErrorMessage } from './errors'
import { setLocale } from './i18n.svelte'

beforeEach(() => setLocale('en'))

it('shows the localized text for a known code', () => {
  expect(syncErrorMessage('source_empty', 'The YouTube Music playlist is empty or private')).toBe(
    'The YouTube Music playlist is empty, private or unavailable.',
  )
})

it('falls back to the raw message for unknown or missing codes', () => {
  expect(syncErrorMessage('unknown', 'boom')).toBe('The last sync failed: boom')
  expect(syncErrorMessage('brand_new', 'boom')).toBe('The last sync failed: boom')
  expect(syncErrorMessage(null, 'boom')).toBe('The last sync failed: boom')
})
