<script lang="ts">
  import ColorPicker from '../components/ColorPicker.svelte'
  import IconPicker from '../components/IconPicker.svelte'
  import PixelIcon from '../components/PixelIcon.svelte'
  import StatusBadge from '../components/StatusBadge.svelte'
  import SyncProgress from '../components/SyncProgress.svelte'
  import Toggle from '../components/Toggle.svelte'
  import TrackSearch from '../components/TrackSearch.svelte'
  import { api } from '../lib/api'
  import { errorMessage, syncErrorMessage } from '../lib/errors'
  import { live } from '../lib/events.svelte'
  import { COLORS, formatDate, formatDuration } from '../lib/format'
  import { i18n, t } from '../lib/i18n.svelte'
  import { navigate } from '../lib/router.svelte'
  import type {
    Icon,
    PlaylistDetail,
    PlaylistUpdate,
    Track,
    TrackIn,
    TrackStatus,
  } from '../lib/types'

  let { id }: { id: number } = $props()

  let playlist = $state<PlaylistDetail | null>(null)
  let error = $state<string | null>(null)
  type DraftRow = TrackIn & {
    icon_url?: string | null
    status?: TrackStatus
    error?: string | null
  }
  let draft = $state<DraftRow[] | null>(null) // unsaved edits of a hand-picked playlist
  let adding = $state(false)
  let iconTrack = $state<Track | null>(null)
  let confirmDelete = $state(false)
  let deleteOnYoto = $state(false)
  let title = $state('')
  let lastServerTitle = ''
  let deleting = $state(false)
  let dragIndex: number | null = null

  const progress = $derived(live.progress[id])
  const manual = $derived(playlist?.source_type === 'manual')
  const status = $derived(
    playlist?.syncing || progress ? 'running' : (playlist?.last_sync_status ?? null),
  )
  const draftIds = $derived(new Set((draft ?? []).map((t) => t.video_id)))

  async function load() {
    try {
      playlist = await api.getPlaylist(id)
      // Keep a half-typed rename: only follow the server while the input is untouched.
      if (title === lastServerTitle) title = playlist.title
      lastServerTitle = playlist.title
      error = null
    } catch (e) {
      error = errorMessage(e)
    }
  }

  $effect(() => {
    void live.version
    load()
  })

  async function run(action: () => Promise<unknown>): Promise<boolean> {
    error = null
    try {
      await action()
      await load()
      return true
    } catch (e) {
      error = errorMessage(e)
      return false
    }
  }

  async function update(body: PlaylistUpdate) {
    if (await run(() => api.updatePlaylist(id, body))) return
    // The controls would otherwise keep showing the value the server refused.
    const message = error
    await load()
    error = message
  }

  function asTrackIn(track: TrackIn): TrackIn {
    const { video_id, title, artist, duration, thumbnail_url } = track
    return { video_id, title, artist, duration, thumbnail_url }
  }

  // Draft rows keep the display data of saved tracks so reordering does not hide icons/status.
  function asDraftRow(track: Track): DraftRow {
    return {
      ...asTrackIn(track),
      icon_url: track.icon_url,
      status: track.status,
      error: track.error,
    }
  }

  function editTracks(change: (tracks: DraftRow[]) => DraftRow[]) {
    draft = change(draft ?? playlist!.tracks.map(asDraftRow))
  }

  function moveTrack(from: number, to: number) {
    editTracks((tracks) => {
      const next = [...tracks]
      const [item] = next.splice(from, 1)
      next.splice(to, 0, item)
      return next
    })
  }

  async function saveTracks() {
    if (!draft) return
    const tracks = draft.map(asTrackIn)
    if (await run(() => api.replaceTracks(id, tracks))) {
      draft = null
      adding = false
    }
  }

  async function pickIcon(icon: Icon) {
    const track = iconTrack
    if (track) await run(() => api.setTrackIcon(id, track.id, icon))
  }

  async function remove() {
    if (deleting) return
    deleting = true
    try {
      await api.deletePlaylist(id, deleteOnYoto)
      navigate('/')
    } catch (e) {
      error = errorMessage(e)
      confirmDelete = false
      deleting = false
    }
  }

  const rows: (Track | DraftRow)[] = $derived(draft ?? playlist?.tracks ?? [])
</script>

{#if playlist}
  <section class="stack" style:--card={COLORS[playlist.color]}>
    <header class="hero panel">
      <div class="cover">
        {#if playlist.cover_url}<img src={playlist.cover_url} alt="" />{:else}<span
            class="note"
            aria-hidden="true">♪</span
          >{/if}
      </div>
      <div class="stack info">
        <div class="row">
          <StatusBadge {status} />
          <span class="chip">{manual ? t('detail.source_manual') : t('detail.source_youtube')}</span
          >
        </div>
        <h1>{playlist.title}</h1>
        <p class="muted">
          {playlist.last_sync_at
            ? t('detail.last_sync', { date: formatDate(playlist.last_sync_at, i18n.locale) })
            : t('detail.never_synced')}
        </p>
        {#if progress}<SyncProgress {progress} />{/if}
        {#if playlist.last_sync_status === 'error' && !progress}
          <p class="error-box" title={playlist.last_sync_error ?? undefined}>
            {syncErrorMessage(playlist.last_sync_error_code, playlist.last_sync_error)}
          </p>
        {/if}
        <div class="row">
          <button
            class="btn btn-primary"
            disabled={Boolean(progress) || playlist.syncing}
            onclick={() => run(() => api.syncPlaylist(id))}>⟳ {t('detail.sync_now')}</button
          >
          {#if playlist.shuffle && playlist.yoto_card_id}
            <button
              class="btn"
              disabled={Boolean(progress) || playlist.syncing}
              onclick={() => run(() => api.reshufflePlaylist(id))}
              >🔀 {t('detail.reshuffle')}</button
            >
          {/if}
          {#if playlist.source_url}
            <a class="btn" href={playlist.source_url} target="_blank" rel="noreferrer"
              >{t('detail.open_source')} ↗</a
            >
          {/if}
        </div>
      </div>
    </header>

    {#if error}<p class="error-box">{error}</p>{/if}

    <div class="layout">
      <div class="panel stack">
        <div class="row between">
          <h2>{t('detail.tracks_title')} ({rows.length})</h2>
          {#if manual}
            <button class="btn" onclick={() => (adding = !adding)}>
              {adding ? t('detail.done_adding') : `＋ ${t('detail.add_songs')}`}
            </button>
          {/if}
        </div>

        {#if rows.length > 100}<p class="notice">{t('detail.over_limit')}</p>{/if}

        {#if adding}
          <TrackSearch
            selected={draftIds.size ? draftIds : new Set(playlist.tracks.map((t) => t.video_id))}
            onadd={(track) => editTracks((tracks) => [...tracks, asTrackIn(track)])}
          />
        {/if}

        {#if draft}
          <div class="notice row between">
            <span>{t('detail.order_changed')}</span>
            <span class="row">
              <button class="btn" onclick={() => (draft = null)}>{t('common.cancel')}</button>
              <button class="btn btn-primary" onclick={saveTracks}>{t('detail.save_order')}</button>
            </span>
          </div>
        {/if}

        <ol class="tracks">
          {#each rows as track, index (`${track.video_id}-${index}`)}
            {@const saved = 'id' in track ? track : null}
            {@const iconUrl = track.icon_url ?? null}
            {@const trackStatus = track.status ?? null}
            <li
              draggable={manual}
              ondragstart={(event) => {
                dragIndex = index
                event.dataTransfer?.setData('text/plain', String(index))
              }}
              ondragover={(event) => manual && event.preventDefault()}
              ondrop={(event) => {
                event.preventDefault()
                if (dragIndex !== null && dragIndex !== index) moveTrack(dragIndex, index)
                dragIndex = null
              }}
            >
              <span class="num">{index + 1}</span>
              {#if saved}
                <button
                  class="icon-btn"
                  title={t('detail.change_icon')}
                  aria-label={t('detail.change_icon')}
                  onclick={() => (iconTrack = saved)}
                >
                  <PixelIcon src={iconUrl} size={32} />
                </button>
              {:else}
                <PixelIcon src={iconUrl} size={32} />
              {/if}
              <span class="meta">
                <strong>{track.title}</strong>
                <span class="muted"
                  >{track.artist ?? ''} · {formatDuration(track.duration ?? null)}</span
                >
              </span>
              {#if trackStatus && trackStatus !== 'uploaded'}
                <span class="chip status-{trackStatus}" title={track.error ?? ''}
                  >{t(`track.${trackStatus}`)}</span
                >
              {/if}
              {#if manual}
                <span class="row tools">
                  <button
                    class="btn btn-icon"
                    aria-label={t('new.move_up')}
                    disabled={index === 0}
                    onclick={() => moveTrack(index, index - 1)}>↑</button
                  >
                  <button
                    class="btn btn-icon"
                    aria-label={t('new.move_down')}
                    disabled={index === rows.length - 1}
                    onclick={() => moveTrack(index, index + 1)}>↓</button
                  >
                  <button
                    class="btn btn-icon btn-danger"
                    aria-label={t('detail.remove_track')}
                    disabled={rows.length === 1}
                    onclick={() => editTracks((tracks) => tracks.filter((_, i) => i !== index))}
                    >✕</button
                  >
                </span>
              {/if}
            </li>
          {/each}
        </ol>
      </div>

      <aside class="stack">
        <div class="panel stack">
          <h2>{t('detail.settings_title')}</h2>
          <form
            class="rename"
            onsubmit={(event) => {
              event.preventDefault()
              if (title.trim() && title.trim() !== playlist?.title) update({ title: title.trim() })
            }}
          >
            <label class="field">
              {t('detail.rename')}
              <input class="input" maxlength="200" bind:value={title} />
            </label>
            <button class="btn">{t('common.save')}</button>
          </form>
          <Toggle
            checked={playlist.shuffle}
            label={t('options.shuffle')}
            help={t('options.shuffle_help')}
            onchange={(value) => update({ shuffle: value })}
          />
          {#if !manual}
            <Toggle
              checked={playlist.auto_sync}
              label={t('options.auto_sync')}
              help={t('options.auto_sync_help')}
              onchange={(value) => update({ auto_sync: value })}
            />
          {/if}
          <div class="field">
            {t('options.color')}
            <ColorPicker value={playlist.color} onchange={(value) => update({ color: value })} />
          </div>
        </div>

        <div class="panel stack card-help">
          <h2>💳 {t('detail.card_title')}</h2>
          <p class="muted">{t('detail.card_steps')}</p>
        </div>

        <div class="panel stack">
          {#if confirmDelete}
            <h2>{t('detail.delete_title', { title: playlist.title })}</h2>
            <p class="muted">{t('detail.delete_text')}</p>
            {#if playlist.yoto_card_id}
              <Toggle bind:checked={deleteOnYoto} label={t('detail.delete_on_yoto')} />
            {/if}
            <div class="row">
              <button class="btn" onclick={() => (confirmDelete = false)}
                >{t('common.cancel')}</button
              >
              <button class="btn btn-danger" disabled={deleting} onclick={remove}
                >{t('common.delete')}</button
              >
            </div>
          {:else}
            <button class="btn btn-danger" onclick={() => (confirmDelete = true)}
              >🗑 {t('detail.delete')}</button
            >
          {/if}
        </div>
      </aside>
    </div>
  </section>

  {#if iconTrack}
    <IconPicker query={iconTrack.title} onpick={pickIcon} onclose={() => (iconTrack = null)} />
  {/if}
{:else if error}
  <p class="error-box">{error}</p>
{:else}
  <p class="muted">{t('common.loading')}</p>
{/if}

<style>
  .hero {
    display: grid;
    grid-template-columns: 160px minmax(0, 1fr);
    gap: 24px;
    border-color: var(--card);
    box-shadow: 0 6px 0 var(--card);
  }
  @media (max-width: 640px) {
    .hero {
      grid-template-columns: minmax(0, 1fr);
    }
    .cover {
      max-width: 220px;
    }
  }
  .cover {
    aspect-ratio: 1;
    border-radius: var(--radius);
    background: var(--card);
    overflow: hidden;
    display: grid;
    place-items: center;
  }
  .note {
    font-size: 4.5rem;
    line-height: 1;
    color: #fff;
    opacity: 0.4;
  }
  .cover img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .info {
    gap: 12px;
    align-content: start;
  }
  .layout {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
    gap: 24px;
    align-items: start;
  }
  @media (max-width: 900px) {
    .layout {
      grid-template-columns: minmax(0, 1fr);
    }
  }
  .between {
    justify-content: space-between;
  }
  .tracks {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .tracks li {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 10px;
    border-radius: var(--radius);
    background: var(--surface-2);
  }
  .tracks li[draggable='true'] {
    cursor: grab;
  }
  .num {
    width: 2ch;
    text-align: right;
    color: var(--muted);
    font-weight: 900;
  }
  .icon-btn {
    padding: 0;
    border: 0;
    background: none;
    cursor: pointer;
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
  .status-error,
  .status-unavailable {
    color: var(--danger);
  }
  .tools {
    gap: 4px;
    flex-wrap: nowrap;
  }
  @media (max-width: 560px) {
    .tracks li {
      flex-wrap: wrap;
    }
    .meta {
      flex-basis: 120px;
    }
    .tools {
      margin-left: auto;
    }
  }
  .tools .btn-icon {
    width: 36px;
    min-height: 36px;
  }
  .rename {
    display: grid;
    gap: 12px;
    justify-items: start;
  }
  .rename .field {
    justify-self: stretch;
  }
</style>
