import { beforeEach, expect, it } from 'vitest'
import { loadTheme, setTheme, theme } from './theme.svelte'

beforeEach(() => {
  localStorage.clear()
  setTheme('auto')
})

it('applies a forced theme on the document and remembers it', () => {
  setTheme('dark')
  expect(theme.current).toBe('dark')
  expect(document.documentElement.dataset.theme).toBe('dark')

  document.documentElement.removeAttribute('data-theme')
  loadTheme()
  expect(theme.current).toBe('dark')
  expect(document.documentElement.dataset.theme).toBe('dark')
})

it('follows the system in auto mode', () => {
  setTheme('light')
  setTheme('auto')
  expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
  loadTheme()
  expect(theme.current).toBe('auto')
})

it('ignores an unknown stored value', () => {
  localStorage.setItem('yotube.theme', 'purple')
  loadTheme()
  expect(theme.current).toBe('auto')
})
