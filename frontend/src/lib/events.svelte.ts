import type { ProgressEvent, ServerEvent } from './types'

export const live = $state({
  progress: {} as Record<number, ProgressEvent>,
  /** Incremented whenever server data may have changed; pages refetch on change. */
  version: 0,
  authRequired: false,
})

export function handleEvent(event: ServerEvent): void {
  switch (event.type) {
    case 'progress':
      if (event.phase === 'done' || event.phase === 'error') {
        delete live.progress[event.playlist_id]
      } else {
        live.progress[event.playlist_id] = event
      }
      break
    case 'playlist_updated':
      live.version += 1
      break
    case 'auth_required':
      live.authRequired = true
      break
  }
}

export function connectEvents(): () => void {
  const source = new EventSource('/api/events')
  source.onmessage = (message) => handleEvent(JSON.parse(message.data) as ServerEvent)
  source.onopen = () => {
    live.version += 1 // refetch after a reconnection
  }
  return () => source.close()
}
