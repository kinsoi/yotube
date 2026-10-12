import { describe, expect, it } from 'vitest'
import { parseHash } from './router.svelte'

describe('parseHash', () => {
  it('maps hashes to routes', () => {
    expect(parseHash('')).toEqual({ name: 'library', params: {} })
    expect(parseHash('#/')).toEqual({ name: 'library', params: {} })
    expect(parseHash('#/new')).toEqual({ name: 'new', params: {} })
    expect(parseHash('#/playlists/12')).toEqual({ name: 'playlist', id: 12, params: {} })
    expect(parseHash('#/settings?auth=ok')).toEqual({ name: 'settings', params: { auth: 'ok' } })
  })

  it('falls back to the library for unknown paths', () => {
    expect(parseHash('#/playlists/abc')).toEqual({ name: 'library', params: {} })
    expect(parseHash('#/nope')).toEqual({ name: 'library', params: {} })
  })
})
