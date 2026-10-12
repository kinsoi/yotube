<script lang="ts">
  import { onMount } from 'svelte'
  import { api } from '../lib/api'
  import { errorMessage } from '../lib/errors'
  import { t } from '../lib/i18n.svelte'
  import type { Icon } from '../lib/types'
  import PixelIcon from './PixelIcon.svelte'

  let {
    query: initialQuery,
    onpick,
    onclose,
  }: { query: string; onpick: (icon: Icon) => void; onclose: () => void } = $props()

  let query = $state('')
  let icons = $state<Icon[]>([])
  let loading = $state(true)
  let error = $state<string | null>(null)
  let dialog: HTMLDialogElement
  let timer: ReturnType<typeof setTimeout> | undefined

  async function load(text: string) {
    loading = true
    error = null
    try {
      const found = await api.searchIcons(text)
      if (text === query) icons = found // ignore stale responses
    } catch (e) {
      if (text === query) error = errorMessage(e)
    } finally {
      if (text === query) loading = false
    }
  }

  function onInput() {
    clearTimeout(timer)
    timer = setTimeout(() => load(query), 250)
  }

  onMount(() => {
    query = initialQuery
    dialog.showModal()
    load(query)
    return () => clearTimeout(timer)
  })
</script>

<dialog bind:this={dialog} {onclose} class="panel" aria-labelledby="icon-picker-title">
  <div class="row head">
    <h2 id="icon-picker-title">{t('icons.title')}</h2>
    <button class="btn btn-icon" onclick={() => dialog.close()} aria-label={t('common.close')}
      >✕</button
    >
  </div>
  <input
    class="input"
    type="search"
    placeholder={t('icons.search_placeholder')}
    bind:value={query}
    oninput={onInput}
  />
  {#if error}<p class="error-box">{error}</p>{/if}
  {#if loading}
    <p class="muted">{t('icons.loading')}</p>
  {:else if icons.length === 0}
    <p class="muted">{t('icons.none')}</p>
  {:else}
    <div class="grid">
      {#each icons as icon (icon.media_id)}
        <button
          class="icon-btn"
          title={icon.title}
          onclick={() => {
            onpick(icon)
            dialog.close()
          }}
        >
          <PixelIcon src={icon.url} size={48} alt={icon.title} />
        </button>
      {/each}
    </div>
  {/if}
</dialog>

<style>
  dialog[open] {
    width: min(560px, calc(100vw - 32px));
    max-height: min(640px, calc(100vh - 64px));
    display: grid;
    gap: 16px;
    color: var(--text);
  }
  dialog::backdrop {
    background: rgb(43 33 24 / 45%);
  }
  .head {
    justify-content: space-between;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
    gap: 8px;
    overflow-y: auto;
  }
  .icon-btn {
    display: grid;
    place-items: center;
    padding: 6px;
    border: 2px solid transparent;
    border-radius: var(--radius-sm);
    background: var(--surface-2);
    cursor: pointer;
  }
  .icon-btn:hover,
  .icon-btn:focus-visible {
    border-color: var(--primary);
  }
</style>
