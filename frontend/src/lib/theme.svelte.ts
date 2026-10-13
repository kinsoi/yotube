// Colour theme: follow the system, or force light/dark. A per-browser choice.

export type Theme = 'auto' | 'light' | 'dark'

export const THEMES: Theme[] = ['auto', 'light', 'dark']

const STORAGE_KEY = 'yotube.theme'

export const theme = $state<{ current: Theme }>({ current: 'auto' })

function isTheme(value: unknown): value is Theme {
  return THEMES.includes(value as Theme)
}

function apply(value: Theme): void {
  const root = document.documentElement
  if (value === 'auto') root.removeAttribute('data-theme')
  else root.dataset.theme = value
}

export function loadTheme(): void {
  let stored: string | null = null
  try {
    stored = localStorage.getItem(STORAGE_KEY)
  } catch {
    // Storage blocked: stay on the system theme.
  }
  theme.current = isTheme(stored) ? stored : 'auto'
  apply(theme.current)
}

export function setTheme(value: Theme): void {
  theme.current = value
  apply(value)
  try {
    if (value === 'auto') localStorage.removeItem(STORAGE_KEY)
    else localStorage.setItem(STORAGE_KEY, value)
  } catch {
    // Private browsing: the choice simply isn't remembered.
  }
}
