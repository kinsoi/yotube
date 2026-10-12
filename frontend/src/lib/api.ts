import type {
  AppSettings,
  AuthStatus,
  Icon,
  PlaylistCreate,
  PlaylistDetail,
  PlaylistPreview,
  PlaylistSummary,
  PlaylistUpdate,
  Track,
  TrackIn,
  TrackInfo,
} from './types'

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      method,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'network', 'Network error')
  }
  if (!response.ok) {
    let data: { detail?: unknown; code?: string } = {}
    try {
      data = await response.json()
    } catch {
      // Not JSON (e.g. a proxy error page).
    }
    const message = typeof data.detail === 'string' ? data.detail : response.statusText
    throw new ApiError(response.status, data.code ?? 'generic', message)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

const q = encodeURIComponent

export const api = {
  authStatus: () => request<AuthStatus>('GET', '/api/auth/status'),
  logout: () => request<void>('POST', '/api/auth/logout'),
  search: (query: string) => request<TrackInfo[]>('GET', `/api/search?q=${q(query)}`),
  previewPlaylist: (url: string) =>
    request<PlaylistPreview>('GET', `/api/youtube/playlist?url=${q(url)}`),
  listPlaylists: () => request<PlaylistSummary[]>('GET', '/api/playlists'),
  getPlaylist: (id: number) => request<PlaylistDetail>('GET', `/api/playlists/${id}`),
  createPlaylist: (body: PlaylistCreate) => request<PlaylistDetail>('POST', '/api/playlists', body),
  updatePlaylist: (id: number, body: PlaylistUpdate) =>
    request<PlaylistDetail>('PATCH', `/api/playlists/${id}`, body),
  deletePlaylist: (id: number, deleteOnYoto: boolean) =>
    request<void>('DELETE', `/api/playlists/${id}?delete_on_yoto=${deleteOnYoto}`),
  replaceTracks: (id: number, tracks: TrackIn[]) =>
    request<PlaylistDetail>('PUT', `/api/playlists/${id}/tracks`, tracks),
  setTrackIcon: (id: number, trackId: number, icon: Icon) =>
    request<Track>('PATCH', `/api/playlists/${id}/tracks/${trackId}`, {
      icon_id: icon.media_id,
      icon_url: icon.url,
    }),
  syncPlaylist: (id: number) => request<{ status: string }>('POST', `/api/playlists/${id}/sync`),
  reshufflePlaylist: (id: number) =>
    request<{ status: string }>('POST', `/api/playlists/${id}/reshuffle`),
  searchIcons: (query: string) => request<Icon[]>('GET', `/api/icons?q=${q(query)}`),
  getSettings: () => request<AppSettings>('GET', '/api/settings'),
  updateSettings: (body: Pick<AppSettings, 'language'>) =>
    request<AppSettings>('PATCH', '/api/settings', body),
}
