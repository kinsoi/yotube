<script lang="ts" module>
  // Rounded line icons on a 24px grid; shapes adapted from Lucide (ISC licence).
  const circle = (cx: number, cy: number, r: number) =>
    `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`

  const LINE = {
    plus: ['M5 12h14', 'M12 5v14'],
    x: ['M18 6 6 18', 'm6 6 12 12'],
    check: ['M20 6 9 17l-5-5'],
    'check-circle': [circle(12, 12, 10), 'm9 12 2 2 4-4'],
    'arrow-up': ['m5 12 7-7 7 7', 'M12 19V5'],
    'arrow-down': ['M12 5v14', 'm19 12-7 7-7-7'],
    external: [
      'M15 3h6v6',
      'M10 14 21 3',
      'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6',
    ],
    sync: [
      'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8',
      'M21 3v5h-5',
      'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16',
      'M8 16H3v5',
    ],
    shuffle: [
      'm18 14 4 4-4 4',
      'm18 2 4 4-4 4',
      'M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22',
      'M2 6h1.9c1.5 0 2.9.9 3.6 2.2',
      'M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8',
    ],
    moon: ['M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z'],
    sun: [
      circle(12, 12, 4),
      'M12 2v2',
      'M12 20v2',
      'm4.93 4.93 1.41 1.41',
      'm17.66 17.66 1.41 1.41',
      'M2 12h2',
      'M20 12h2',
      'm6.34 17.66-1.41 1.41',
      'm19.07 4.93-1.41 1.41',
    ],
    monitor: [
      'M4 3h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z',
      'M8 21h8',
      'M12 17v4',
    ],
    card: ['M4 5h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z', 'M2 10h20'],
    trash: [
      'M3 6h18',
      'M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6',
      'M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2',
    ],
    sparkles: [
      'M9.94 15.5a2 2 0 0 0-1.44-1.44l-6.13-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5l1.58-6.13a.5.5 0 0 1 .96 0l1.58 6.13a2 2 0 0 0 1.44 1.44l6.13 1.58a.5.5 0 0 1 0 .96l-6.13 1.58a2 2 0 0 0-1.44 1.44l-1.58 6.13a.5.5 0 0 1-.96 0z',
      'M20 3v4',
      'M22 5h-4',
    ],
    link: [
      'M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71',
      'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71',
    ],
    search: [circle(11, 11, 8), 'm21 21-4.3-4.3'],
    music: ['M9 18V5l12-2v13', circle(6, 18, 3), circle(18, 16, 3)],
    alert: [circle(12, 12, 10), 'M12 8v4', 'M12 16h.01'],
  } satisfies Record<string, string[]>

  const FILLED = {
    play: ['M7 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L8.5 3.64A1 1 0 0 0 7 4.5Z'],
    stop: ['M8 6h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z'],
  } satisfies Record<string, string[]>

  export type GlyphName = keyof typeof LINE | keyof typeof FILLED
</script>

<script lang="ts">
  let { name, size = 20 }: { name: GlyphName; size?: number } = $props()

  const filled = $derived(name in FILLED)
  const paths: string[] = $derived(
    name in FILLED ? FILLED[name as keyof typeof FILLED] : LINE[name as keyof typeof LINE],
  )
</script>

<svg
  class="glyph"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill={filled ? 'currentColor' : 'none'}
  stroke={filled ? 'none' : 'currentColor'}
  stroke-width="2.25"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  focusable="false"
>
  {#each paths as d (d)}<path {d} />{/each}
</svg>

<style>
  .glyph {
    flex: none;
    display: inline-block;
    vertical-align: -0.2em;
  }
</style>
