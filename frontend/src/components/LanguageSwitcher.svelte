<script lang="ts">
  import { api } from '../lib/api'
  import { i18n, LOCALE_NAMES, setLocale, t } from '../lib/i18n.svelte'
  import type { Locale } from '../lib/types'

  function change(event: Event) {
    const locale = (event.currentTarget as HTMLSelectElement).value as Locale
    setLocale(locale)
    api.updateSettings({ language: locale }).catch(() => {
      // The local choice still applies; the server default is just not updated.
    })
  }
</script>

<label class="switcher">
  <span class="visually-hidden">{t('settings.language')}</span>
  <select class="input" value={i18n.locale} onchange={change}>
    {#each Object.entries(LOCALE_NAMES) as [code, name] (code)}
      <option value={code}>{name}</option>
    {/each}
  </select>
</label>

<style>
  select {
    min-height: 40px;
    width: auto;
    padding: 0 12px;
  }
</style>
