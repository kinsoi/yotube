<script lang="ts">
  import { t } from '../lib/i18n.svelte'
</script>

<div class="banner" role="alert">
  <span>{t('banner.text')}</span>
  <a class="btn btn-primary" href="/api/auth/login">{t('banner.action')}</a>
</div>

<style>
  .banner {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    justify-content: center;
    padding: 12px 16px;
    background: var(--surface-2);
    border-bottom: 2px solid var(--border);
    font-weight: 800;
  }
</style>
