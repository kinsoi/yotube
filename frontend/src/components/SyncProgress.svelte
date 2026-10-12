<script lang="ts">
  import { t } from '../lib/i18n.svelte'
  import type { ProgressEvent } from '../lib/types'

  let { progress, compact = false }: { progress: ProgressEvent; compact?: boolean } = $props()

  const percent = $derived(
    progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : null,
  )
  const label = $derived(
    t(`progress.${progress.phase}`, {
      current: progress.current,
      total: progress.total,
      title: progress.track_title ?? '',
    }),
  )
</script>

<div class="progress" class:compact>
  <div
    class="bar"
    role="progressbar"
    aria-label={label}
    aria-valuemin={percent === null ? undefined : 0}
    aria-valuemax={percent === null ? undefined : 100}
    aria-valuenow={percent ?? undefined}
  >
    <div
      class="fill"
      class:indeterminate={percent === null}
      style:width={percent === null ? '35%' : `${percent}%`}
    ></div>
  </div>
  <p class="label">{label}</p>
</div>

<style>
  .progress {
    display: grid;
    gap: 6px;
  }
  .bar {
    height: 12px;
    border-radius: 999px;
    background: var(--surface-2);
    overflow: hidden;
  }
  .compact .bar {
    height: 8px;
  }
  .fill {
    height: 100%;
    border-radius: inherit;
    background: repeating-linear-gradient(
      -45deg,
      var(--primary) 0 10px,
      var(--primary-strong) 10px 20px
    );
    transition: width 0.4s ease;
  }
  .indeterminate {
    animation: slide 1.2s ease-in-out infinite;
  }
  .label {
    margin: 0;
    font-size: 0.85rem;
    color: var(--muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  @keyframes slide {
    from {
      transform: translateX(-100%);
    }
    to {
      transform: translateX(300%);
    }
  }
</style>
