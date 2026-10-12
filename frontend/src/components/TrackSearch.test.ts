import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, expect, it, vi } from 'vitest'
import { setLocale } from '../lib/i18n.svelte'
import TrackSearch from './TrackSearch.svelte'

afterEach(() => vi.unstubAllGlobals())

it('searches and adds a track', async () => {
  setLocale('en')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            video_id: 'v1',
            title: 'Lion song',
            artist: 'Anne',
            duration: 90,
            thumbnail_url: null,
            available: true,
          },
        ]),
        { status: 200 },
      ),
    ),
  )
  const onadd = vi.fn()
  render(TrackSearch, { selected: new Set<string>(), onadd })

  await fireEvent.input(screen.getByPlaceholderText('Search a song or an artist'), {
    target: { value: 'lion' },
  })
  await fireEvent.submit(screen.getByRole('search'))

  const add = await screen.findByRole('button', { name: 'Add' })
  await fireEvent.click(add)
  expect(onadd).toHaveBeenCalledWith(expect.objectContaining({ video_id: 'v1' }))
})
