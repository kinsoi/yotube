<script lang="ts">
  let {
    checked = $bindable(false),
    label,
    help,
    disabled = false,
    onchange,
  }: {
    checked: boolean
    label: string
    help?: string
    disabled?: boolean
    onchange?: (value: boolean) => void
  } = $props()
</script>

<label class="toggle" class:disabled>
  <input
    type="checkbox"
    role="switch"
    bind:checked
    {disabled}
    onchange={() => onchange?.(checked)}
  />
  <span class="track" aria-hidden="true"><span class="knob"></span></span>
  <span class="text">
    <span class="label">{label}</span>
    {#if help}<span class="help muted">{help}</span>{/if}
  </span>
</label>

<style>
  .toggle {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    cursor: pointer;
  }
  .disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  input {
    position: absolute;
    opacity: 0;
  }
  .track {
    flex: none;
    width: 52px;
    height: 32px;
    border-radius: 999px;
    background: var(--border);
    position: relative;
    transition: background 0.2s;
  }
  .knob {
    position: absolute;
    top: 4px;
    left: 4px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 2px 0 rgb(0 0 0 / 15%);
    transition: transform 0.2s;
  }
  input:checked + .track {
    background: var(--primary);
  }
  input:checked + .track .knob {
    transform: translateX(20px);
  }
  input:focus-visible + .track {
    outline: 3px solid var(--primary);
    outline-offset: 2px;
  }
  .text {
    display: grid;
    gap: 2px;
  }
  .label {
    font-weight: 800;
  }
  .help {
    font-size: 0.85rem;
  }
</style>
