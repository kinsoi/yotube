<script lang="ts">
  import Glyph from './Glyph.svelte'
  import { onDestroy } from 'svelte'
  import { t } from '../lib/i18n.svelte'
  import { player, stopPreview, togglePreview } from '../lib/preview.svelte'

  let { videoId, title }: { videoId: string; title: string } = $props()

  const status = $derived(player.videoId === videoId ? player.status : 'idle')
  const label = $derived(
    status === 'error'
      ? t('preview.error')
      : status === 'idle'
        ? t('preview.play', { title })
        : t('preview.stop', { title }),
  )

  onDestroy(() => {
    if (player.videoId === videoId) stopPreview()
  })
</script>

<button
  class="btn btn-icon preview status-{status}"
  type="button"
  aria-label={label}
  title={label}
  aria-pressed={status === 'loading' || status === 'playing'}
  onclick={() => togglePreview(videoId)}
>
  {#if status === 'loading'}
    <span class="spinner" aria-hidden="true"></span>
  {:else if status === 'playing'}
    <Glyph name="stop" size={18} />
  {:else if status === 'error'}
    <Glyph name="alert" size={20} />
  {:else}
    <Glyph name="play" size={18} />
  {/if}
</button>

<style>
  .preview {
    flex: none;
    border-radius: 50%;
  }
  .status-playing,
  .status-loading {
    background: var(--primary);
    color: var(--on-primary);
  }
  .status-error {
    color: var(--danger);
  }
  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation-duration: 2.4s;
    }
  }
</style>
