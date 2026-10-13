<script lang="ts">
  import { COLORS } from '../lib/format'
  import { t, tn } from '../lib/i18n.svelte'
  import type { PlaylistSummary, ProgressEvent } from '../lib/types'
  import Glyph from './Glyph.svelte'
  import PixelIcon from './PixelIcon.svelte'
  import StatusBadge from './StatusBadge.svelte'
  import SyncProgress from './SyncProgress.svelte'

  let { playlist, progress }: { playlist: PlaylistSummary; progress?: ProgressEvent } = $props()

  const status = $derived(playlist.syncing || progress ? 'running' : playlist.last_sync_status)
</script>

<a class="yoto-card" href="#/playlists/{playlist.id}" style:--card={COLORS[playlist.color]}>
  <div class="cover">
    {#if playlist.cover_url}
      <img src={playlist.cover_url} alt="" loading="lazy" />
    {:else}
      <span class="note" aria-hidden="true"><Glyph name="music" size={64} /></span>
    {/if}
    {#if playlist.icon_urls.length}
      <div class="icons">
        {#each playlist.icon_urls as url (url)}
          <PixelIcon src={url} size={28} />
        {/each}
      </div>
    {/if}
  </div>
  <div class="body">
    <h2>{playlist.title}</h2>
    <p class="muted count">{tn('library.tracks', playlist.track_count)}</p>
    <div class="row badges">
      <StatusBadge {status} />
      {#if playlist.shuffle}<span
          class="chip"
          title={t('badge.shuffle')}
          aria-label={t('badge.shuffle')}><Glyph name="shuffle" size={14} /></span
        >{/if}
      {#if playlist.auto_sync}<span
          class="chip"
          title={t('badge.auto')}
          aria-label={t('badge.auto')}><Glyph name="moon" size={14} /></span
        >{/if}
    </div>
    {#if progress}
      <SyncProgress {progress} compact />
    {/if}
  </div>
</a>

<style>
  .yoto-card {
    display: grid;
    grid-template-rows: auto 1fr;
    text-decoration: none;
    background: var(--surface);
    border: 3px solid var(--card);
    border-radius: var(--radius-lg);
    box-shadow: 0 6px 0 var(--card);
    overflow: hidden;
    min-width: 0;
    transition: transform 0.15s ease;
  }
  .yoto-card:hover {
    transform: translateY(-4px) rotate(-0.5deg);
  }
  .cover {
    position: relative;
    aspect-ratio: 1;
    background: var(--card);
    display: grid;
    place-items: center;
  }
  .note {
    display: grid;
    color: #fff;
    opacity: 0.45;
  }
  .cover img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .icons {
    position: absolute;
    bottom: 10px;
    left: 10px;
    display: flex;
    gap: 6px;
  }
  .body {
    display: grid;
    align-content: start;
    gap: 8px;
    padding: 14px 16px 16px;
  }
  h2 {
    overflow-wrap: anywhere;
    font-size: 1.1rem;
    line-height: 1.2;
  }
  .count {
    margin: 0;
  }
  .badges {
    gap: 6px;
  }
</style>
