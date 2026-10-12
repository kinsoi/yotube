<script lang="ts">
  import { onMount } from 'svelte'
  import LanguageSwitcher from './components/LanguageSwitcher.svelte'
  import ReconnectBanner from './components/ReconnectBanner.svelte'
  import { api } from './lib/api'
  import { connectEvents, live } from './lib/events.svelte'
  import { hasStoredLocale, setLocale, t } from './lib/i18n.svelte'
  import { router } from './lib/router.svelte'
  import Library from './routes/Library.svelte'
  import NewPlaylist from './routes/NewPlaylist.svelte'
  import PlaylistDetail from './routes/PlaylistDetail.svelte'
  import Settings from './routes/Settings.svelte'

  onMount(() => {
    api
      .getSettings()
      .then((settings) => {
        live.authRequired = settings.yoto_configured && !settings.yoto_connected
        if (settings.language && !hasStoredLocale()) setLocale(settings.language)
      })
      .catch(() => {
        // The pages show their own errors.
      })
    return connectEvents()
  })
</script>

<header class="topbar">
  <a class="brand" href="#/">
    <span class="logo" aria-hidden="true">♪</span>
    Yotube
  </a>
  <nav>
    <a href="#/" class:active={router.route.name === 'library'}>{t('nav.library')}</a>
    <a href="#/settings" class:active={router.route.name === 'settings'}>{t('nav.settings')}</a>
  </nav>
  <LanguageSwitcher />
</header>

{#if live.authRequired && router.route.name !== 'settings'}
  <ReconnectBanner />
{/if}

<main class="container">
  {#if router.route.name === 'library'}
    <Library />
  {:else if router.route.name === 'new'}
    <NewPlaylist />
  {:else if router.route.name === 'playlist'}
    {#key router.route.id}
      <PlaylistDetail id={router.route.id} />
    {/key}
  {:else}
    <Settings params={router.route.params} />
  {/if}
</main>

<style>
  .topbar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px 16px;
    padding: 10px 16px;
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    backdrop-filter: blur(10px);
    border-bottom: 2px solid var(--border);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 1.4rem;
    font-weight: 900;
    text-decoration: none;
  }
  .logo {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 12px;
    background: var(--primary);
    color: #fff;
    box-shadow: 0 3px 0 var(--primary-strong);
  }
  nav {
    display: flex;
    gap: 4px;
    margin-left: auto;
    min-width: 0;
  }
  nav a {
    padding: 8px 14px;
    border-radius: 999px;
    text-decoration: none;
    font-weight: 800;
  }
  nav a.active {
    background: var(--surface-2);
  }
  @media (max-width: 560px) {
    .brand {
      font-size: 1.1rem;
    }
    nav a {
      padding: 8px 10px;
    }
    .topbar {
      gap: 6px 10px;
    }
  }
</style>
