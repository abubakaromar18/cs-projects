<script>
  // One column of the palette: shows the color, its codes, WCAG contrast
  // against black/white text, and per-swatch controls.
  import {
    bestTextColor,
    contrastRatio,
    hexToHsl,
    hexToRgb,
    normalizeHex,
    wcagRating,
  } from '../lib/color.js';

  let {
    swatch,
    index,
    count,
    canRemove,
    onlock,
    onremove,
    onchange,
    onmove,
    oncopy,
  } = $props();

  const text = $derived(bestTextColor(swatch.hex));
  const rgb = $derived(hexToRgb(swatch.hex));
  const hsl = $derived(hexToHsl(swatch.hex));
  const onWhite = $derived(contrastRatio(swatch.hex, '#ffffff'));
  const onBlack = $derived(contrastRatio(swatch.hex, '#000000'));

  // Local draft so the user can type partial hex codes without the
  // palette rejecting them on every keystroke.
  let draft = $state('');
  let editing = $state(false);

  function commit() {
    const norm = normalizeHex(draft);
    if (norm) onchange(index, norm);
    editing = false;
  }
</script>

<section
  class="swatch"
  style:background={swatch.hex}
  style:color={text}
  aria-label={`Color ${index + 1}: ${swatch.hex}${swatch.locked ? ', locked' : ''}`}
>
  <div class="tools">
    <button
      class="icon"
      title={swatch.locked ? 'Unlock' : 'Lock'}
      aria-pressed={swatch.locked}
      onclick={() => onlock(index)}
    >{swatch.locked ? '🔒' : '🔓'}</button>
    <button class="icon" title="Move left" disabled={index === 0} onclick={() => onmove(index, index - 1)}>←</button>
    <button class="icon" title="Move right" disabled={index === count - 1} onclick={() => onmove(index, index + 1)}>→</button>
    <button class="icon" title="Remove" disabled={!canRemove} onclick={() => onremove(index)}>✕</button>
  </div>

  <div class="info">
    {#if editing}
      <!-- svelte-ignore a11y_autofocus -->
      <input
        class="hex-input"
        bind:value={draft}
        autofocus
        maxlength="7"
        onblur={commit}
        onkeydown={(e) => {
          if (e.key === 'Enter') commit();
          if (e.key === 'Escape') editing = false;
          e.stopPropagation();
        }}
      />
    {:else}
      <button
        class="hex"
        title="Click to copy, double-click to edit"
        onclick={() => oncopy(swatch.hex)}
        ondblclick={() => { draft = swatch.hex; editing = true; }}
      >{swatch.hex.toUpperCase()}</button>
    {/if}

    <label class="picker" title="Pick a color">
      <input type="color" value={swatch.hex} oninput={(e) => onchange(index, e.currentTarget.value)} />
      <span>pick</span>
    </label>

    <dl>
      <dt>RGB</dt><dd>{rgb.r}, {rgb.g}, {rgb.b}</dd>
      <dt>HSL</dt><dd>{Math.round(hsl.h)}°, {Math.round(hsl.s)}%, {Math.round(hsl.l)}%</dd>
    </dl>

    <ul class="contrast">
      <li><span class="chip white">Aa</span> {onWhite.toFixed(2)} <b>{wcagRating(onWhite)}</b></li>
      <li><span class="chip black">Aa</span> {onBlack.toFixed(2)} <b>{wcagRating(onBlack)}</b></li>
    </ul>
  </div>
</section>

<style>
  .swatch {
    flex: 1 1 0;
    min-width: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 1rem 0.75rem;
    transition: background-color 0.25s ease;
  }
  .tools { display: flex; gap: 0.25rem; justify-content: center; flex-wrap: wrap; }
  .icon {
    background: transparent;
    border: 1px solid currentColor;
    color: inherit;
    padding: 0.2rem 0.45rem;
    opacity: 0.75;
  }
  .icon:hover:not(:disabled) { opacity: 1; }
  .info { text-align: center; display: grid; gap: 0.5rem; justify-items: center; }
  .hex {
    background: transparent;
    border: none;
    color: inherit;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    font-family: ui-monospace, monospace;
  }
  .hex-input {
    width: 7.5em;
    text-align: center;
    font-family: ui-monospace, monospace;
    font-size: 1.1rem;
    color: #000;
  }
  .picker { position: relative; font-size: 0.8rem; opacity: 0.8; cursor: pointer; }
  .picker input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
  dl { margin: 0; display: grid; grid-template-columns: auto auto; gap: 0 0.4rem; font-size: 0.8rem; }
  dt { opacity: 0.7; }
  dd { margin: 0; font-family: ui-monospace, monospace; }
  .contrast { list-style: none; margin: 0; padding: 0; font-size: 0.78rem; display: grid; gap: 0.2rem; }
  .chip { display: inline-block; padding: 0 0.3rem; border-radius: 4px; font-weight: 700; }
  .chip.white { background: #fff; color: #000; }
  .chip.black { background: #000; color: #fff; }
  @media (max-width: 700px) {
    .swatch { flex-direction: row; align-items: center; padding: 0.6rem 0.75rem; }
    .tools { flex-direction: column; }
    .info { grid-template-columns: auto auto; text-align: left; justify-items: start; }
  }
</style>
