<script lang="ts">
  import Glyph from './Glyph.svelte'
  import { onDestroy } from 'svelte'

  let { src, size }: { src: string | null; size: number } = $props()

  // YouTube image hosts answer 429 when a page loads many thumbnails at once: retry a
  // few times with a growing, jittered delay, then fall back to a music note.
  const RETRY_DELAYS_MS = [1500, 4000, 9000]

  let attempt = $state(0)
  let failed = $state(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  $effect(() => {
    void src
    attempt = 0
    failed = false
    clearTimeout(timer)
  })

  function retry() {
    if (attempt >= RETRY_DELAYS_MS.length) {
      failed = true
      return
    }
    const delay = RETRY_DELAYS_MS[attempt] + Math.random() * 1000
    timer = setTimeout(() => (attempt += 1), delay)
  }

  onDestroy(() => clearTimeout(timer))
</script>

<span class="thumb" style:--size="{size}px">
  {#if src && !failed}
    {#key attempt}
      <img {src} alt="" width={size} height={size} referrerpolicy="no-referrer" onerror={retry} />
    {/key}
  {:else}
    <span class="note" aria-hidden="true"
      ><Glyph name="music" size={Math.round(size * 0.45)} /></span
    >
  {/if}
</span>

<style>
  .thumb {
    display: grid;
    place-items: center;
    flex: none;
    width: var(--size);
    height: var(--size);
    border-radius: 10px;
    overflow: hidden;
    background: var(--border);
  }
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .note {
    display: grid;
    opacity: 0.5;
  }
</style>
