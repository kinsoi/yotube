<script lang="ts">
  let { src, size = 32, alt = '' }: { src: string | null; size?: number; alt?: string } = $props()
</script>

{#if src}
  <img class="pixel" {src} {alt} width={size} height={size} loading="lazy" />
{:else}
  <span class="pixel placeholder" style:width="{size}px" style:height="{size}px" aria-hidden="true"
  ></span>
{/if}

<style>
  .pixel {
    image-rendering: pixelated;
    border-radius: 6px;
    background: #111;
    padding: 2px;
    flex: none;
  }

  .placeholder {
    display: inline-block;
    background: repeating-conic-gradient(#2b2118 0 25%, #3a2e24 0 50%) 0 0 / 8px 8px;
  }
</style>
