<script lang="ts">
  import ColorPicker from '../components/ColorPicker.svelte'
  import Toggle from '../components/Toggle.svelte'
  import TrackSearch from '../components/TrackSearch.svelte'
  import { api } from '../lib/api'
  import { errorMessage } from '../lib/errors'
  import { formatDuration } from '../lib/format'
  import { t, tn } from '../lib/i18n.svelte'
  import { navigate } from '../lib/router.svelte'
  import type { Color, PlaylistPreview, TrackInfo } from '../lib/types'

  let tab = $state<'import' | 'compose'>('import')
  let title = $state('')
  let shuffle = $state(false)
  let autoSync = $state(true)
  let color = $state<Color>('orange')
  let busy = $state(false)
  let error = $state<string | null>(null)

  let url = $state('')
  let preview = $state<PlaylistPreview | null>(null)

  let basket = $state<TrackInfo[]>([])
  const selected = $derived(new Set(basket.map((track) => track.video_id)))

  const canCreate = $derived(
    !busy && title.trim().length > 0 && (tab === 'import' ? preview !== null : basket.length > 0),
  )

  async function loadPreview(event: SubmitEvent) {
    event.preventDefault()
    busy = true
    error = null
    preview = null
    try {
      preview = await api.previewPlaylist(url.trim())
      title = preview.title
    } catch (e) {
      error = errorMessage(e)
    } finally {
      busy = false
    }
  }

  function move(index: number, delta: number) {
    const target = index + delta
    if (target < 0 || target >= basket.length) return
    const next = [...basket]
    ;[next[index], next[target]] = [next[target], next[index]]
    basket = next
  }

  async function create() {
    busy = true
    error = null
    try {
      const playlist =
        tab === 'import'
          ? await api.createPlaylist({
              title: title.trim(),
              source_type: 'youtube',
              source_url: url.trim(),
              shuffle,
              auto_sync: autoSync,
              color,
            })
          : await api.createPlaylist({
              title: title.trim(),
              source_type: 'manual',
              tracks: basket.map(({ video_id, title, artist, duration, thumbnail_url }) => ({
                video_id,
                title,
                artist,
                duration,
                thumbnail_url,
              })),
              shuffle,
              auto_sync: false,
              color,
            })
      navigate(`/playlists/${playlist.id}`)
    } catch (e) {
      error = errorMessage(e)
      busy = false
    }
  }
</script>

<section class="stack">
  <div class="page-head"><h1>{t('new.title')}</h1></div>

  <div class="tabs" role="tablist">
    <button role="tab" aria-selected={tab === 'import'} onclick={() => (tab = 'import')}>
      🔗 {t('new.tab_import')}
    </button>
    <button role="tab" aria-selected={tab === 'compose'} onclick={() => (tab = 'compose')}>
      🔍 {t('new.tab_compose')}
    </button>
  </div>

  {#if error}<p class="error-box">{error}</p>{/if}

  {#if tab === 'import'}
    <div class="panel stack">
      <form class="stack" onsubmit={loadPreview}>
        <label class="field">
          {t('new.url_label')}
          <input
            class="input"
            type="url"
            required
            placeholder={t('new.url_placeholder')}
            bind:value={url}
          />
        </label>
        <div><button class="btn" disabled={busy || !url.trim()}>{t('new.preview')}</button></div>
      </form>

      {#if preview}
        <div class="preview row">
          {#if preview.thumbnail_url}
            <img src={preview.thumbnail_url} alt="" width="96" height="96" />
          {/if}
          <div>
            <h2>{preview.title}</h2>
            <p class="muted">{tn('new.preview_tracks', preview.tracks.length)}</p>
          </div>
        </div>
        <ol class="tracks muted">
          {#each preview.tracks.slice(0, 8) as track, index (`${track.video_id}-${index}`)}
            <li>{track.title} <span>· {formatDuration(track.duration)}</span></li>
          {/each}
          {#if preview.tracks.length > 8}<li>…</li>{/if}
        </ol>
      {/if}
    </div>
  {:else}
    <div class="compose">
      <div class="panel">
        <TrackSearch {selected} onadd={(track) => (basket = [...basket, track])} />
      </div>
      <div class="panel stack">
        <h2>{t('new.basket_title')} ({basket.length})</h2>
        {#if basket.length === 0}
          <p class="muted">{t('new.basket_empty')}</p>
        {:else}
          <ol class="basket">
            {#each basket as track, index (track.video_id)}
              <li>
                <span class="name">{track.title}</span>
                <button
                  class="btn btn-icon"
                  aria-label={t('new.move_up')}
                  onclick={() => move(index, -1)}>↑</button
                >
                <button
                  class="btn btn-icon"
                  aria-label={t('new.move_down')}
                  onclick={() => move(index, 1)}>↓</button
                >
                <button
                  class="btn btn-icon btn-danger"
                  aria-label={t('new.remove')}
                  onclick={() => (basket = basket.filter((_, i) => i !== index))}>✕</button
                >
              </li>
            {/each}
          </ol>
        {/if}
      </div>
    </div>
  {/if}

  <div class="panel stack">
    <h2>{t('new.options')}</h2>
    <label class="field">
      {t('new.name_label')}
      <input class="input" maxlength="200" bind:value={title} />
    </label>
    <Toggle bind:checked={shuffle} label={t('options.shuffle')} help={t('options.shuffle_help')} />
    {#if tab === 'import'}
      <Toggle
        bind:checked={autoSync}
        label={t('options.auto_sync')}
        help={t('options.auto_sync_help')}
      />
    {/if}
    <div class="field">
      {t('options.color')}
      <ColorPicker bind:value={color} />
    </div>
    <div>
      <button class="btn btn-primary" disabled={!canCreate} onclick={create}>
        {busy ? t('new.creating') : t('new.create')}
      </button>
    </div>
  </div>
</section>

<style>
  .tabs {
    display: flex;
    gap: 8px;
    padding: 6px;
    border-radius: 999px;
    background: var(--surface-2);
    width: fit-content;
    max-width: 100%;
  }
  .tabs button {
    border: 0;
    border-radius: 999px;
    padding: 10px 18px;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-weight: 800;
    cursor: pointer;
  }
  .tabs button[aria-selected='true'] {
    background: var(--surface);
    box-shadow: var(--shadow-press);
  }
  .preview img {
    border-radius: var(--radius);
    object-fit: cover;
  }
  .tracks {
    margin: 0;
    padding-left: 20px;
    display: grid;
    gap: 4px;
  }
  .compose {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 24px;
    align-items: start;
  }
  .basket {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 8px;
  }
  .basket li {
    display: flex;
    gap: 6px;
    align-items: center;
  }
  .name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
