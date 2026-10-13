import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { setLocale } from '../lib/i18n.svelte'
import { player, stopPreview } from '../lib/preview.svelte'
import PreviewButton from './PreviewButton.svelte'

class FakeAudio extends EventTarget {
  constructor(public src: string) {
    super()
  }
  play = vi.fn(async () => {})
  pause = vi.fn()
  removeAttribute = vi.fn()
  load = vi.fn()
}

beforeEach(() => {
  setLocale('en')
  stopPreview()
  vi.stubGlobal('Audio', FakeAudio)
})
afterEach(() => vi.unstubAllGlobals())

it('starts and stops listening to a song', async () => {
  render(PreviewButton, { videoId: 'v1', title: 'Lion song' })

  await fireEvent.click(screen.getByRole('button', { name: 'Listen to Lion song' }))
  expect(player.videoId).toBe('v1')

  await fireEvent.click(screen.getByRole('button', { name: 'Stop Lion song' }))
  expect(player.videoId).toBeNull()
})

it('stops the song when the button goes away', async () => {
  const { unmount } = render(PreviewButton, { videoId: 'v1', title: 'Lion song' })
  await fireEvent.click(screen.getByRole('button', { name: 'Listen to Lion song' }))

  unmount()

  expect(player.videoId).toBeNull()
})
