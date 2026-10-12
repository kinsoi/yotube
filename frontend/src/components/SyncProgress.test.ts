import { render, screen } from '@testing-library/svelte'
import { expect, it } from 'vitest'
import SyncProgress from './SyncProgress.svelte'

it('renders a determinate bar while uploading', () => {
  render(SyncProgress, {
    progress: {
      type: 'progress',
      playlist_id: 1,
      phase: 'uploading',
      current: 1,
      total: 4,
      track_title: 'Song',
      message: null,
    },
  })
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '25')
})

it('renders an indeterminate bar while fetching', () => {
  render(SyncProgress, {
    progress: {
      type: 'progress',
      playlist_id: 1,
      phase: 'fetching',
      current: 0,
      total: 0,
      track_title: null,
      message: null,
    },
  })
  expect(screen.getByRole('progressbar')).not.toHaveAttribute('aria-valuenow')
})
