import { beforeEach, describe, expect, it, vi } from 'vitest'
import { connectEvents, handleEvent, live } from './events.svelte'

const progress = {
  type: 'progress' as const,
  playlist_id: 4,
  phase: 'uploading' as const,
  current: 1,
  total: 3,
  track_title: 'Song',
  message: null,
}

beforeEach(() => {
  live.progress = {}
  live.version = 0
  live.authRequired = false
})

describe('handleEvent', () => {
  it('tracks progress per playlist and clears it when done', () => {
    handleEvent(progress)
    expect(live.progress[4]?.current).toBe(1)
    handleEvent({ ...progress, phase: 'done' })
    expect(live.progress[4]).toBeUndefined()
  })

  it('bumps the version on playlist updates', () => {
    handleEvent({ type: 'playlist_updated', playlist_id: 4 })
    expect(live.version).toBe(1)
  })

  it('drops stale progress on playlist updates, keeping other playlists', () => {
    handleEvent(progress)
    handleEvent({ ...progress, playlist_id: 5 })
    handleEvent({ type: 'playlist_updated', playlist_id: 4 })
    expect(live.progress[4]).toBeUndefined()
    expect(live.progress[5]).toBeDefined()
  })

  it('flags an expired Yoto session', () => {
    handleEvent({ type: 'auth_required' })
    expect(live.authRequired).toBe(true)
  })
})

describe('connectEvents', () => {
  it('clears progress and refetches when the stream (re)opens', () => {
    class FakeSource {
      static last: FakeSource
      onopen: (() => void) | null = null
      onmessage: unknown = null
      close = vi.fn()
      constructor() {
        FakeSource.last = this
      }
    }
    vi.stubGlobal('EventSource', FakeSource)
    handleEvent(progress)
    const close = connectEvents()
    FakeSource.last.onopen?.()
    expect(live.progress).toEqual({})
    expect(live.version).toBe(1)
    close()
    vi.unstubAllGlobals()
  })
})
