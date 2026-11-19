<script>
  // Root component: owns the palette state (wrapped in an undo/redo
  // history), syncs it to the URL hash, and wires up keyboard shortcuts.
  import Swatch from './components/Swatch.svelte';
  import ContrastGrid from './components/ContrastGrid.svelte';
  import ExportPanel from './components/ExportPanel.svelte';
  import {
    HARMONIES,
    MAX_SIZE,
    MIN_SIZE,
    addSwatch,
    decodePalette,
    encodePalette,
    generatePalette,
    initialPalette,
    moveSwatch,
    removeSwatch,
    setColor,
    toggleLock,
  } from './lib/palette.js';
  import { mulberry32, randomSeed } from './lib/random.js';
  import * as H from './lib/history.js';

  // One RNG for the session. Seeded randomly, but any seed reproduces.
  const rng = mulberry32(randomSeed());

  let mode = $state('analogous');
  let history = $state.raw(
    H.createHistory(decodePalette(location.hash.slice(1)) ?? initialPalette(5, 'analogous', rng)),
  );
  let toast = $state('');
  let toastTimer;

  const palette = $derived(history.present);
  const hexes = $derived(palette.map((s) => s.hex));

  /** Every palette edit goes through here so it lands in history. */
  function commit(next) {
    if (next !== palette) history = H.push(history, next);
  }

  const regenerate = () => commit(generatePalette(palette, mode, rng));
  const undo = () => (history = H.undo(history));
  const redo = () => (history = H.redo(history));

  function notify(msg) {
    toast = msg;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ''), 1600);
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      notify(text.length < 10 ? `Copied ${text}` : 'Copied to clipboard');
    } catch {
      notify('Clipboard unavailable');
    }
  }

  // Keep the URL shareable: the hash always reflects the current palette.
  $effect(() => {
    const encoded = encodePalette(palette);
    if (location.hash.slice(1) !== encoded) replaceHash(encoded);
  });
  function replaceHash(encoded) {
    window.history.replaceState(null, '', `#${encoded}`);
  }

  function onKey(e) {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
    const mod = e.ctrlKey || e.metaKey;
    if (e.code === 'Space') { e.preventDefault(); regenerate(); }
    else if (mod && e.key.toLowerCase() === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
    else if (mod && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z'))) {
      e.preventDefault(); redo();
    }
    else if (/^[1-9]$/.test(e.key) && !mod) {
      const i = Number(e.key) - 1;
      if (i < palette.length) commit(toggleLock(palette, i));
    }
  }
</script>

<svelte:window onkeydown={onKey} />

<header>
  <h1>Palette<span>gen</span></h1>
  <div class="controls">
    <label>
      Harmony
      <select bind:value={mode}>
        {#each Object.entries(HARMONIES) as [key, h] (key)}
          <option value={key}>{h.label}</option>
        {/each}
      </select>
    </label>
    <button class="primary" onclick={regenerate}>Generate <kbd>Space</kbd></button>
    <button onclick={undo} disabled={!H.canUndo(history)} title="Ctrl/⌘+Z">Undo</button>
    <button onclick={redo} disabled={!H.canRedo(history)} title="Ctrl/⌘+Shift+Z">Redo</button>
    <button onclick={() => commit(addSwatch(palette, mode, rng))} disabled={palette.length >= MAX_SIZE}>+ Add</button>
    <button onclick={() => copy(location.href)}>Share link</button>
  </div>
</header>

<main>
  <div class="palette">
    {#each palette as swatch, i (i)}
      <Swatch
        {swatch}
        index={i}
        count={palette.length}
        canRemove={palette.length > MIN_SIZE}
        onlock={(idx) => commit(toggleLock(palette, idx))}
        onremove={(idx) => commit(removeSwatch(palette, idx))}
        onchange={(idx, hex) => commit(setColor(palette, idx, hex))}
        onmove={(from, to) => commit(moveSwatch(palette, from, to))}
        oncopy={copy}
      />
    {/each}
  </div>

  <p class="hint">
    <kbd>Space</kbd> generate · <kbd>1</kbd>–<kbd>9</kbd> lock/unlock · click a hex to copy, double-click to edit.
    Locked colors are kept and used as the base for the harmony.
  </p>

  <div class="panels">
    <section class="panel">
      <h2>Accessibility</h2>
      <ContrastGrid {hexes} onfix={(idx, hex) => commit(setColor(palette, idx, hex))} />
    </section>
    <section class="panel">
      <h2>Export</h2>
      <ExportPanel {hexes} oncopy={copy} />
    </section>
  </div>
</main>

{#if toast}
  <div class="toast" role="status">{toast}</div>
{/if}

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
    padding: 0.8rem 1.25rem;
    border-bottom: 1px solid var(--border);
    background: var(--panel);
  }
  h1 { margin: 0; font-size: 1.3rem; letter-spacing: -0.02em; }
  h1 span { color: var(--accent); }
  .controls { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
  label { display: flex; gap: 0.4rem; align-items: center; font-size: 0.9rem; }
  select { padding: 0.4rem; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); }
  kbd {
    font-family: ui-monospace, monospace;
    font-size: 0.75em;
    border: 1px solid currentColor;
    border-radius: 4px;
    padding: 0 0.3em;
    opacity: 0.8;
  }
  .palette { display: flex; height: 60vh; min-height: 22rem; }
  .hint { color: var(--muted); font-size: 0.85rem; text-align: center; margin: 0.75rem 1rem; }
  .panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: 1rem; padding: 0 1.25rem 2rem; }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; min-width: 0; }
  h2 { margin: 0 0 0.75rem; font-size: 1rem; }
  .toast {
    position: fixed;
    bottom: 1.25rem;
    left: 50%;
    transform: translateX(-50%);
    background: var(--fg);
    color: var(--bg);
    padding: 0.5rem 1rem;
    border-radius: 999px;
    font-size: 0.9rem;
  }
  @media (max-width: 700px) {
    .palette { flex-direction: column; height: auto; }
    .panels { grid-template-columns: 1fr; padding: 0 0.75rem 1.5rem; }
  }
</style>
