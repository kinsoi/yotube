import { beforeEach, expect, it, vi } from 'vitest'
import { player, stopPreview, togglePreview } from './preview.svelte'

class FakeAudio extends EventTarget {
  static instances: FakeAudio[] = []
  src: string
  paused = true
  constructor(src: string) {
    super()
    this.src = src
    FakeAudio.instances.push(this)
  }
  play = vi.fn(async () => {
    this.paused = false
  })
  pause = vi.fn(() => {
    this.paused = true
  })
  removeAttribute = vi.fn()
  load = vi.fn()
}

beforeEach(() => {
  stopPreview()
  FakeAudio.instances = []
  vi.stubGlobal('Audio', FakeAudio)
})

it('plays one song at a time from the preview endpoint', async () => {
  await togglePreview('v1')
  expect(FakeAudio.instances[0].src).toBe('/api/preview/v1')
  expect(player.videoId).toBe('v1')
  expect(player.status).toBe('loading')

  FakeAudio.instances[0].dispatchEvent(new Event('playing'))
  expect(player.status).toBe('playing')

  await togglePreview('v2')
  expect(FakeAudio.instances[0].pause).toHaveBeenCalled()
  expect(player.videoId).toBe('v2')
})

it('stops when the playing song is toggled again', async () => {
  await togglePreview('v1')
  await togglePreview('v1')
  expect(FakeAudio.instances[0].pause).toHaveBeenCalled()
  expect(player.videoId).toBeNull()
  expect(player.status).toBe('idle')
})

it('reports an error when the song cannot be played', async () => {
  await togglePreview('v1')
  FakeAudio.instances[0].dispatchEvent(new Event('error'))
  expect(player.videoId).toBe('v1')
  expect(player.status).toBe('error')
})

it('goes back to idle when the song ends', async () => {
  await togglePreview('v1')
  FakeAudio.instances[0].dispatchEvent(new Event('ended'))
  expect(player.videoId).toBeNull()
  expect(player.status).toBe('idle')
})

it('ignores events of a song that was replaced', async () => {
  await togglePreview('v1')
  await togglePreview('v2')
  FakeAudio.instances[0].dispatchEvent(new Event('error'))
  expect(player.videoId).toBe('v2')
  expect(player.status).toBe('loading')
})
