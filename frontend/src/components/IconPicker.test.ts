import { render, screen } from '@testing-library/svelte'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { setLocale } from '../lib/i18n.svelte'
import IconPicker from './IconPicker.svelte'

beforeEach(() => {
  setLocale('en')
  // jsdom has no modal dialogs.
  HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
    this.open = true
  }
  HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
    this.open = false
  }
})
afterEach(() => vi.unstubAllGlobals())

function stubIcons(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })),
  )
}

const lion = { media_id: 'm1', title: 'Lion', url: 'https://i/lion.png' }

it('offers the whole catalogue when nothing matches the song', async () => {
  stubIcons({ icons: [lion], matched: false })
  render(IconPicker, { query: 'Georgian Disco', onpick: vi.fn(), onclose: vi.fn() })

  expect(
    await screen.findByText('Nothing matches “Georgian Disco”. Pick one from the whole catalogue:'),
  ).toBeInTheDocument()
  expect(screen.getByTitle('Lion')).toBeInTheDocument()
})

it('lists matching icons without a notice', async () => {
  stubIcons({ icons: [lion], matched: true })
  render(IconPicker, { query: 'lion', onpick: vi.fn(), onclose: vi.fn() })

  expect(await screen.findByTitle('Lion')).toBeInTheDocument()
  expect(screen.queryByText(/Nothing matches/)).not.toBeInTheDocument()
})
