// Listening to a song in the browser before it is added: one song plays at a time.

export type PreviewStatus = 'idle' | 'loading' | 'playing' | 'error'

export const player = $state<{ videoId: string | null; status: PreviewStatus }>({
  videoId: null,
  status: 'idle',
})

let audio: HTMLAudioElement | null = null

export function previewUrl(videoId: string): string {
  return `/api/preview/${encodeURIComponent(videoId)}`
}

export async function togglePreview(videoId: string): Promise<void> {
  const replay = player.videoId === videoId && player.status === 'error'
  if (player.videoId === videoId && !replay) {
    stopPreview()
    return
  }
  stopPreview()

  const current = new Audio(previewUrl(videoId))
  audio = current
  player.videoId = videoId
  player.status = 'loading'

  const on = (type: string, update: () => void) =>
    current.addEventListener(type, () => {
      if (audio === current) update()
    })
  on('playing', () => (player.status = 'playing'))
  on('waiting', () => (player.status = 'loading'))
  on('ended', stopPreview)
  on('error', () => fail(current))

  try {
    await current.play()
  } catch (e) {
    // Another song started meanwhile (AbortError): nothing to report.
    if (audio === current && !(e instanceof DOMException && e.name === 'AbortError')) {
      fail(current)
    }
  }
}

export function stopPreview(): void {
  release()
  player.videoId = null
  player.status = 'idle'
}

function fail(current: HTMLAudioElement): void {
  if (audio !== current) return
  const videoId = player.videoId
  release()
  player.videoId = videoId
  player.status = 'error'
}

function release(): void {
  if (!audio) return
  audio.pause()
  // Drop the source so the browser closes the stream instead of buffering on.
  audio.removeAttribute('src')
  audio.load()
  audio = null
}
