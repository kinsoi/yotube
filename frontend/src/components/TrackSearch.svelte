<script lang="ts">
  import { api } from '../lib/api'
  import { errorMessage } from '../lib/errors'
  import { formatDuration } from '../lib/format'
  import { t } from '../lib/i18n.svelte'
  import type { TrackInfo } from '../lib/types'
  import PreviewButton from './PreviewButton.svelte'
  import Thumbnail from './Thumbnail.svelte'

  let { selected, onadd }: { selected: Set<string>; onadd: (track: TrackInfo) => void } = $props()

  let query = $state('')
  let results = $state<TrackInfo[] | null>(null)
  let loading = $state(false)
  let error = $state<string | null>(null)

  async function search(event: SubmitEvent) {
    event.preventDefault()
    if (!query.trim()) return
    loading = true
    error = null
    try {
      results = await api.search(query.trim())
    } catch (e) {
      error = errorMessage(e)
    } finally {
      loading = false
    }
  }
</script>

<div class="stack">
  <form role="search" class="row search" onsubmit={search}>
    <input class="input" type="search" placeholder={t('search.placeholder')} bind:value={query} />
    <button class="btn btn-primary" disabled={loading}>{t('search.button')}</button>
  </form>

  {#if error}<p class="error-box">{error}</p>{/if}
  {#if loading}<p class="muted">{t('common.loading')}</p>{/if}

  {#if results && !loading}
    {#if results.length === 0}
      <p class="muted">{t('search.no_results')}</p>
    {:else}
      <ul class="results">
        {#each results as track (track.video_id)}
          <li>
            <Thumbnail src={track.thumbnail_url} size={48} />
            <PreviewButton videoId={track.video_id} title={track.title} />
            <span class="meta">
              <strong>{track.title}</strong>
              <span class="muted">{track.artist} · {formatDuration(track.duration)}</span>
            </span>
            {#if selected.has(track.video_id)}
              <span class="chip">✓ {t('search.added')}</span>
            {:else}
              <button class="btn" type="button" onclick={() => onadd(track)}
                >{t('search.add')}</button
              >
            {/if}
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .search {
    flex-wrap: nowrap;
  }
  .results {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 8px;
  }
  li {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px;
    border-radius: var(--radius);
    background: var(--surface-2);
  }
  .meta {
    display: grid;
    flex: 1;
    min-width: 0;
  }
  .meta > * {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
