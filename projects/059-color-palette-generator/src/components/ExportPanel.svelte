<script>
  // Shows the palette in the chosen export format with copy / download.
  import { EXPORTERS } from '../lib/exporters.js';

  let { hexes, oncopy } = $props();
  let format = $state('css');

  const output = $derived(EXPORTERS[format].fn(hexes));

  function download() {
    const { ext, mime } = EXPORTERS[format];
    const blob = new Blob([output], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = Object.assign(document.createElement('a'), { href: url, download: `palette.${ext}` });
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="export">
  <div class="tabs" role="tablist">
    {#each Object.entries(EXPORTERS) as [key, ex] (key)}
      <button role="tab" aria-selected={format === key} class:active={format === key} onclick={() => (format = key)}>
        {ex.label}
      </button>
    {/each}
  </div>
  <pre><code>{output}</code></pre>
  <div class="actions">
    <button onclick={() => oncopy(output)}>Copy</button>
    <button onclick={download}>Download .{EXPORTERS[format].ext}</button>
  </div>
</div>

<style>
  .tabs { display: flex; gap: 0.3rem; flex-wrap: wrap; }
  .tabs .active { border-color: var(--accent); color: var(--accent); font-weight: 600; }
  pre {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.8rem;
    overflow-x: auto;
    font-size: 0.8rem;
    max-height: 16rem;
  }
  .actions { display: flex; gap: 0.5rem; }
</style>
