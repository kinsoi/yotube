export type Locale = 'en' | 'fr' | 'ru'
export type Color = 'orange' | 'yellow' | 'blue' | 'green' | 'pink' | 'purple' | 'red' | 'teal'
export type SyncStatus = 'ok' | 'partial' | 'error' | 'running'
export type TrackStatus = 'pending' | 'uploaded' | 'unavailable' | 'error'
export type Phase = 'fetching' | 'uploading' | 'icons' | 'saving' | 'done' | 'error'

export interface TrackInfo {
  video_id: string
  title: string
  artist: string
  duration: number | null
  thumbnail_url: string | null
  available: boolean
}

export interface PlaylistPreview {
  playlist_id: string
  title: string
  thumbnail_url: string | null
  tracks: TrackInfo[]
}

export interface Track {
  id: number
  video_id: string
  title: string
  artist: string
  duration: number | null
  thumbnail_url: string | null
  position: number
  icon_id: string | null
  icon_url: string | null
  icon_manual: boolean
  status: TrackStatus
  error: string | null
}

export interface PlaylistSummary {
  id: number
  title: string
  source_type: 'youtube' | 'manual'
  source_url: string | null
  yoto_card_id: string | null
  shuffle: boolean
  auto_sync: boolean
  color: Color
  cover_url: string | null
  last_sync_at: string | null
  last_sync_status: SyncStatus | null
  last_sync_error: string | null
  track_count: number
  syncing: boolean
  icon_urls: string[]
}

export interface PlaylistDetail extends PlaylistSummary {
  tracks: Track[]
}

export interface TrackIn {
  video_id: string
  title: string
  artist?: string
  duration?: number | null
  thumbnail_url?: string | null
}

export interface PlaylistCreate {
  title: string
  source_type: 'youtube' | 'manual'
  source_url?: string
  tracks?: TrackIn[]
  shuffle: boolean
  auto_sync: boolean
  color: Color
}

export interface PlaylistUpdate {
  title?: string
  shuffle?: boolean
  auto_sync?: boolean
  color?: Color
}

export interface Icon {
  media_id: string
  title: string
  url: string
}

export interface AuthStatus {
  configured: boolean
  connected: boolean
}

export interface AppSettings {
  language: Locale | null
  sync_cron: string
  timezone: string
  icon_ai_enabled: boolean
  yoto_configured: boolean
  yoto_connected: boolean
}

export interface ProgressEvent {
  type: 'progress'
  playlist_id: number
  phase: Phase
  current: number
  total: number
  track_title: string | null
  message: string | null
}

export type ServerEvent =
  ProgressEvent | { type: 'playlist_updated'; playlist_id: number } | { type: 'auth_required' }
