<script lang="ts">
  import { api } from '../lib/api'
  import { errorMessage } from '../lib/errors'
  import { live } from '../lib/events.svelte'
  import { i18n, LOCALE_NAMES, setLocale, t } from '../lib/i18n.svelte'
  import type { AppSettings, Locale } from '../lib/types'

  let { params }: { params: Record<string, string> } = $props()

  let settings = $state<AppSettings | null>(null)
  let error = $state<string | null>(null)

  async function load() {
    try {
      settings = await api.getSettings()
      live.authRequired = settings.yoto_configured && !settings.yoto_connected
    } catch (e) {
      error = errorMessage(e)
    }
  }

  async function disconnect() {
    await api.logout().catch((e) => (error = errorMessage(e)))
    await load()
  }

  async function changeLanguage(locale: Locale) {
    setLocale(locale)
    settings = await api.updateSettings({ language: locale }).catch(() => settings)
  }

  $effect(() => {
    load()
  })
</script>

<section class="stack narrow">
  <div class="page-head"><h1>{t('settings.title')}</h1></div>

  {#if params.auth === 'ok'}<p class="notice">✅ {t('settings.auth_ok')}</p>{/if}
  {#if params.auth === 'error'}<p class="error-box">{t('settings.auth_error')}</p>{/if}
  {#if error}<p class="error-box">{error}</p>{/if}

  {#if settings}
    <div class="panel stack">
      <h2>{t('settings.yoto_title')}</h2>
      {#if !settings.yoto_configured}
        <p class="error-box">{t('settings.not_configured')}</p>
      {:else if settings.yoto_connected}
        <p class="row"><span class="dot ok"></span>{t('settings.connected')}</p>
        <div><button class="btn" onclick={disconnect}>{t('settings.disconnect')}</button></div>
      {:else}
        <p class="row"><span class="dot"></span>{t('settings.disconnected')}</p>
        <div><a class="btn btn-primary" href="/api/auth/login">{t('settings.connect')}</a></div>
        <p class="muted small">{t('settings.lan_note')}</p>
      {/if}
    </div>

    <div class="panel stack">
      <h2>{t('settings.language')}</h2>
      <div class="row">
        {#each Object.entries(LOCALE_NAMES) as [code, name] (code)}
          <button
            class="btn"
            class:btn-primary={i18n.locale === code}
            onclick={() => changeLanguage(code as Locale)}>{name}</button
          >
        {/each}
      </div>
    </div>

    <div class="panel stack">
      <h2>🌙 {t('settings.schedule_title')}</h2>
      <p class="muted">
        {t('settings.schedule_text', { cron: settings.sync_cron, timezone: settings.timezone })}
      </p>
    </div>

    <div class="panel stack">
      <h2>✨ {t('settings.icon_ai_title')}</h2>
      <p class="muted">
        {settings.icon_ai_enabled ? t('settings.icon_ai_on') : t('settings.icon_ai_off')}
      </p>
    </div>
  {:else if !error}
    <p class="muted">{t('common.loading')}</p>
  {/if}
</section>

<style>
  .narrow {
    max-width: 720px;
  }
  .dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--muted);
  }
  .dot.ok {
    background: var(--success);
  }
  .small {
    font-size: 0.85rem;
  }
</style>
