<script lang="ts">
  import { COLORS, COLOR_NAMES } from '../lib/format'
  import { t } from '../lib/i18n.svelte'
  import type { Color } from '../lib/types'

  let {
    value = $bindable('orange'),
    onchange,
  }: { value: Color; onchange?: (value: Color) => void } = $props()
</script>

<fieldset class="colors">
  <legend class="visually-hidden">{t('options.color')}</legend>
  {#each COLOR_NAMES as color (color)}
    <label class="swatch" style:--swatch={COLORS[color]} title={t(`colors.${color}`)}>
      <input
        type="radio"
        name="color"
        value={color}
        bind:group={value}
        onchange={() => onchange?.(color)}
      />
      <span class="visually-hidden">{t(`colors.${color}`)}</span>
    </label>
  {/each}
</fieldset>

<style>
  .colors {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    border: 0;
    padding: 0;
    margin: 0;
  }
  .swatch {
    width: 36px;
    height: 36px;
    border-radius: 12px;
    background: var(--swatch);
    box-shadow: inset 0 -4px 0 rgb(0 0 0 / 18%);
    cursor: pointer;
    position: relative;
  }
  .swatch input {
    position: absolute;
    opacity: 0;
  }
  .swatch:has(input:checked) {
    outline: 3px solid var(--text);
    outline-offset: 3px;
  }
  .swatch:has(input:focus-visible) {
    outline: 3px solid var(--primary);
    outline-offset: 3px;
  }
</style>
