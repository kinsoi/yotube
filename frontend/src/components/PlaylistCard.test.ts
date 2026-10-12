import { render, screen } from '@testing-library/svelte'
import { beforeEach, expect, it } from 'vitest'
import { setLocale } from '../lib/i18n.svelte'
import type { PlaylistSummary } from '../lib/types'
import PlaylistCard from './PlaylistCard.svelte'

const playlist: PlaylistSummary = {
  id: 7,
  title: 'Bedtime songs',
  source_type: 'youtube',
  source_url: 'https://music.youtube.com/playlist?list=PL1',
  yoto_card_id: 'card-1',
  shuffle: true,
  auto_sync: true,
  color: 'blue',
  cover_url: null,
  last_sync_at: '2026-10-12T03:00:00',
  last_sync_status: 'ok',
  last_sync_error: null,
  last_sync_error_code: null,
  track_count: 3,
  syncing: false,
  icon_urls: ['https://i/1.png'],
}

beforeEach(() => setLocale('en'))

it('shows title, track count, status and links to the detail page', () => {
  render(PlaylistCard, { playlist })
  expect(screen.getByRole('heading', { name: 'Bedtime songs' })).toBeInTheDocument()
  expect(screen.getByText('3 tracks')).toBeInTheDocument()
  expect(screen.getByText('Synced')).toBeInTheDocument()
  expect(screen.getByRole('link')).toHaveAttribute('href', '#/playlists/7')
})

it('shows live progress while syncing', () => {
  render(PlaylistCard, {
    playlist: { ...playlist, syncing: true },
    progress: {
      type: 'progress',
      playlist_id: 7,
      phase: 'uploading',
      current: 1,
      total: 3,
      track_title: 'Lullaby',
      message: null,
    },
  })
  expect(screen.getByText('Syncing…')).toBeInTheDocument()
  expect(screen.getByText('Sending 1/3: Lullaby')).toBeInTheDocument()
})

it('is translated', () => {
  setLocale('ru')
  render(PlaylistCard, { playlist: { ...playlist, track_count: 5 } })
  expect(screen.getByText('5 треков')).toBeInTheDocument()
})
