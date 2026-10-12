import { fireEvent, render } from '@testing-library/svelte'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Thumbnail from './Thumbnail.svelte'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

it('retries a thumbnail that failed to load (image hosts rate-limit bursts)', async () => {
  const { container } = render(Thumbnail, { src: 'https://i.ytimg.com/a.jpg', size: 48 })
  const first = container.querySelector('img')!

  await fireEvent.error(first)
  await vi.runAllTimersAsync()

  const retried = container.querySelector('img')
  expect(retried).not.toBeNull()
  expect(retried).not.toBe(first)
  expect(retried!.getAttribute('src')).toBe('https://i.ytimg.com/a.jpg')
})

it('shows a music note once every retry failed', async () => {
  const { container } = render(Thumbnail, { src: 'https://i.ytimg.com/a.jpg', size: 48 })

  for (let attempt = 0; attempt < 10 && container.querySelector('img'); attempt++) {
    await fireEvent.error(container.querySelector('img')!)
    await vi.runAllTimersAsync()
  }

  expect(container.querySelector('img')).toBeNull()
  expect(container.textContent).toContain('♪')
})

it('shows a music note when there is no image', () => {
  const { container } = render(Thumbnail, { src: null, size: 48 })
  expect(container.querySelector('img')).toBeNull()
  expect(container.textContent).toContain('♪')
})
