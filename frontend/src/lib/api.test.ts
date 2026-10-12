import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './api'
import { errorMessage } from './errors'
import { setLocale } from './i18n.svelte'

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('sends JSON and parses the response', async () => {
    const fetchMock = mockFetch(201, { id: 3 })
    const created = await api.createPlaylist({
      title: 'Kids',
      source_type: 'youtube',
      source_url: 'https://music.youtube.com/playlist?list=PL1',
      shuffle: false,
      auto_sync: true,
      color: 'orange',
    })
    expect(created).toEqual({ id: 3 })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/playlists')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toMatchObject({ title: 'Kids' })
  })

  it('encodes query parameters', async () => {
    const fetchMock = mockFetch(200, [])
    await api.search('lion & tiger')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/search?q=lion%20%26%20tiger')
  })

  it('returns undefined for 204', async () => {
    mockFetch(204, null)
    await expect(api.deletePlaylist(1, true)).resolves.toBeUndefined()
  })

  it('turns error bodies into ApiError', async () => {
    mockFetch(400, { detail: 'nope', code: 'invalid_playlist_url' })
    await expect(api.previewPlaylist('x')).rejects.toMatchObject({
      status: 400,
      code: 'invalid_playlist_url',
    })
  })

  it('reports network failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api.listPlaylists()).rejects.toMatchObject({ code: 'network' })
  })
})

describe('errorMessage', () => {
  it('translates known codes and falls back to a generic message', () => {
    setLocale('en')
    expect(errorMessage(new ApiError(409, 'sync_running', ''))).toBe(
      'A sync is already running. Try again in a moment.',
    )
    expect(errorMessage(new ApiError(500, 'weird_code', ''))).toBe('Something went wrong.')
    expect(errorMessage(new Error('boom'))).toBe('Something went wrong.')
  })
})
