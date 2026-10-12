import { describe, expect, it } from 'vitest'
import en from './locales/en.json'
import fr from './locales/fr.json'
import ru from './locales/ru.json'
import { flattenKeys, translate } from './i18n.svelte'

describe('locale files', () => {
  it('share exactly the same keys', () => {
    const keys = flattenKeys(en).sort()
    expect(flattenKeys(fr).sort()).toEqual(keys)
    expect(flattenKeys(ru).sort()).toEqual(keys)
  })

  it('use the same placeholders in every language', () => {
    const placeholders = (text: string) => (text.match(/\{\w+\}/g) ?? []).sort()
    for (const key of flattenKeys(en)) {
      const reference = placeholders(translate('en', key))
      expect(placeholders(translate('fr', key)), key).toEqual(reference)
      expect(placeholders(translate('ru', key)), key).toEqual(reference)
    }
  })
})

describe('translate', () => {
  it('interpolates parameters', () => {
    expect(translate('fr', 'detail.last_sync', { date: 'hier' })).toBe('Dernière synchro : hier')
  })

  it('falls back to the key when it is unknown', () => {
    expect(translate('ru', 'does.not.exist')).toBe('does.not.exist')
  })

  it('picks Russian plural forms', async () => {
    const { tnFor } = await import('./i18n.svelte')
    expect(tnFor('ru', 'library.tracks', 1)).toBe('1 трек')
    expect(tnFor('ru', 'library.tracks', 3)).toBe('3 трека')
    expect(tnFor('ru', 'library.tracks', 5)).toBe('5 треков')
    expect(tnFor('en', 'library.tracks', 1)).toBe('1 track')
    expect(tnFor('fr', 'library.tracks', 0)).toBe('0 piste')
  })
})
