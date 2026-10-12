<script lang="ts">
  import { t } from '../lib/i18n.svelte'
  import type { SyncStatus } from '../lib/types'

  let { status }: { status: SyncStatus | null } = $props()
</script>

<span class="chip badge {status ?? 'never'}">{t(`status.${status ?? 'never'}`)}</span>

<style>
  .badge.ok {
    background: rgb(34 160 107 / 16%);
    color: var(--success);
  }
  .badge.partial {
    background: rgb(224 161 15 / 18%);
    color: var(--warning);
  }
  .badge.error {
    background: rgb(229 72 77 / 14%);
    color: var(--danger);
  }
  .badge.running {
    background: rgb(242 107 58 / 16%);
    color: var(--primary);
  }
</style>
