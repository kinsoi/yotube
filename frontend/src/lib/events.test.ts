import { beforeEach, describe, expect, it } from 'vitest'
import { handleEvent, live } from './events.svelte'

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

  it('flags an expired Yoto session', () => {
    handleEvent({ type: 'auth_required' })
    expect(live.authRequired).toBe(true)
  })
})
