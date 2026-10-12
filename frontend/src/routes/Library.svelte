<script lang="ts">
  import PlaylistCard from '../components/PlaylistCard.svelte'
  import { api } from '../lib/api'
  import { errorMessage } from '../lib/errors'
  import { live } from '../lib/events.svelte'
  import { t } from '../lib/i18n.svelte'
  import type { PlaylistSummary } from '../lib/types'

  let playlists = $state<PlaylistSummary[]>([])
  let loading = $state(true)
  let error = $state<string | null>(null)

  async function load() {
    try {
      playlists = await api.listPlaylists()
      error = null
    } catch (e) {
      error = errorMessage(e)
    } finally {
      loading = false
    }
  }

  $effect(() => {
    void live.version
    load()
  })
</script>

<section>
  <div class="page-head">
    <h1>{t('library.title')}</h1>
    <a class="btn btn-primary" href="#/new">＋ {t('library.new')}</a>
  </div>

  {#if loading}
    <p class="muted">{t('common.loading')}</p>
  {:else if error}
    <p class="error-box">{error}</p>
  {:else if playlists.length === 0}
    <div class="panel empty">
      <div class="art" aria-hidden="true">🎵</div>
      <h2>{t('library.empty_title')}</h2>
      <p class="muted">{t('library.empty_text')}</p>
      <a class="btn btn-primary" href="#/new">＋ {t('library.new')}</a>
    </div>
  {:else}
    <div class="grid">
      {#each playlists as playlist (playlist.id)}
        <PlaylistCard {playlist} progress={live.progress[playlist.id]} />
      {/each}
    </div>
  {/if}
</section>

<style>
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(160px, 100%), 1fr));
    gap: 24px;
  }
  @media (max-width: 560px) {
    .grid {
      gap: 14px;
    }
  }
  .empty {
    display: grid;
    justify-items: center;
    text-align: center;
    gap: 12px;
    padding: 48px 24px;
  }
  .art {
    font-size: 3rem;
  }
</style>
