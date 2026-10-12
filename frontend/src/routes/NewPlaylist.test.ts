import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, expect, it, vi } from 'vitest'
import { setLocale } from '../lib/i18n.svelte'
import NewPlaylist from './NewPlaylist.svelte'

afterEach(() => vi.unstubAllGlobals())

const preview = {
  title: 'Lullabies',
  thumbnail_url: null,
  tracks: [
    {
      video_id: 'v1',
      title: 'Song one',
      artist: 'A',
      duration: 60,
      thumbnail_url: null,
      available: true,
    },
  ],
}

it('drops the preview when the URL changes and keeps a typed name', async () => {
  setLocale('en')
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(JSON.stringify(preview), { status: 200 })),
  )
  render(NewPlaylist)

  const url = screen.getByPlaceholderText(/https/i)
  await fireEvent.input(url, { target: { value: 'https://music.youtube.com/playlist?list=A' } })
  await fireEvent.click(screen.getByRole('button', { name: 'Preview' }))
  expect(await screen.findByText('Song one', { exact: false })).toBeInTheDocument()

  await fireEvent.input(url, { target: { value: 'https://music.youtube.com/playlist?list=B' } })
  expect(screen.queryByText('Song one', { exact: false })).not.toBeInTheDocument()
})
