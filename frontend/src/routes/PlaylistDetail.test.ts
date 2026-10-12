import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, expect, it, vi } from 'vitest'
import { setLocale } from '../lib/i18n.svelte'
import type { PlaylistDetail as Detail, Track } from '../lib/types'
import PlaylistDetail from './PlaylistDetail.svelte'

afterEach(() => vi.unstubAllGlobals())

function track(id: number): Track {
  return {
    id,
    video_id: `v${id}`,
    title: `Song ${id}`,
    artist: 'A',
    duration: 60,
    thumbnail_url: null,
    position: id - 1,
    icon_id: null,
    icon_url: null,
    icon_manual: false,
    status: 'uploaded',
    error: null,
  }
}

const playlist: Detail = {
  id: 1,
  title: 'Bedtime',
  source_type: 'manual',
  source_url: null,
  yoto_card_id: 'card1',
  shuffle: false,
  auto_sync: false,
  color: 'blue',
  cover_url: null,
  last_sync_at: null,
  last_sync_status: 'ok',
  last_sync_error: null,
  last_sync_error_code: null,
  track_count: 2,
  syncing: false,
  icon_urls: [],
  tracks: [track(1), track(2)],
}

function stubApi() {
  const fetchMock = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(
    async () => new Response(JSON.stringify(playlist), { status: 200 }),
  )
  vi.stubGlobal('fetch', fetchMock)
  const calls = () => fetchMock.mock.calls.map(([url, init]) => `${init?.method ?? 'GET'} ${url}`)
  return calls
}

async function editTrackList() {
  render(PlaylistDetail, { id: 1 })
  const removeButtons = await screen.findAllByRole('button', { name: 'Remove song' })
  await fireEvent.click(removeButtons[1])
  expect(screen.getByText('You have unsaved changes to the song list.')).toBeInTheDocument()
}

it('saves pending song edits when "Sync now" is clicked instead of dropping them', async () => {
  setLocale('en')
  const calls = stubApi()
  await editTrackList()

  await fireEvent.click(screen.getByRole('button', { name: /Sync now/ }))

  await vi.waitFor(() => expect(calls()).toContain('PUT /api/playlists/1/tracks'))
  expect(calls()).not.toContain('POST /api/playlists/1/sync')
})

it('warns before leaving the page with unsaved song edits', async () => {
  setLocale('en')
  stubApi()
  await editTrackList()

  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)

  expect(event.defaultPrevented).toBe(true)
})
