type Params = Record<string, string>

export type Route =
  | { name: 'library'; params: Params }
  | { name: 'new'; params: Params }
  | { name: 'playlist'; id: number; params: Params }
  | { name: 'settings'; params: Params }

export function parseHash(hash: string): Route {
  const [path, query = ''] = hash.replace(/^#/, '').split('?')
  // Parsed once into a plain object; not reactive state.
  // eslint-disable-next-line svelte/prefer-svelte-reactivity
  const params = Object.fromEntries(new URLSearchParams(query))
  if (path === '/new') return { name: 'new', params }
  if (path === '/settings') return { name: 'settings', params }
  const match = /^\/playlists\/(\d+)$/.exec(path)
  if (match) return { name: 'playlist', id: Number(match[1]), params }
  return { name: 'library', params }
}

export const router = $state<{ route: Route }>({ route: parseHash(window.location.hash) })

export function startRouter(): void {
  window.addEventListener('hashchange', () => {
    router.route = parseHash(window.location.hash)
    window.scrollTo(0, 0)
  })
}

export function navigate(path: string): void {
  window.location.hash = path
}
